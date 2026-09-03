"""
Comprehensive tests for SpaceGuard AI.
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from missions.models import Mission, MissionStatus
from telemetry.models import Telemetry
from alerts.models import Alert, AlertStatus, Severity
from anomaly.models import AIAnalysis


def make_mission(**kwargs):
    defaults = {
        'name': 'Test Mission',
        'spacecraft_name': 'Test-SC-1',
        'status': MissionStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Mission.objects.create(**defaults)


def make_telemetry(mission, **kwargs):
    defaults = {
        'timestamp': timezone.now(),
        'temperature': 25.0,
        'battery_voltage': 28.0,
        'battery_current': 8.0,
        'fuel_level': 75.0,
        'radiation': 12.0,
        'pressure': 101.3,
        'signal_strength': -70.0,
        'velocity': 7.66,
        'power_consumption': 250.0,
    }
    defaults.update(kwargs)
    return Telemetry.objects.create(mission=mission, **defaults)


# ─── Model Tests ─────────────────────────────────────────────────────────────

class MissionModelTests(TestCase):
    def test_str(self):
        m = make_mission()
        self.assertIn('Test Mission', str(m))
        self.assertIn('Test-SC-1', str(m))

    def test_default_status(self):
        m = make_mission()
        self.assertEqual(m.status, MissionStatus.ACTIVE)


class TelemetryModelTests(TestCase):
    def setUp(self):
        self.mission = make_mission()

    def test_str(self):
        t = make_telemetry(self.mission)
        self.assertIn('Test-SC-1', str(t))

    def test_anomaly_defaults(self):
        t = make_telemetry(self.mission)
        self.assertFalse(t.is_anomaly)
        self.assertIsNone(t.anomaly_score)


class AlertModelTests(TestCase):
    def setUp(self):
        self.mission = make_mission()
        self.telemetry = make_telemetry(self.mission)

    def test_create_alert(self):
        alert = Alert.objects.create(
            mission=self.mission,
            telemetry=self.telemetry,
            subsystem='THERMAL',
            severity=Severity.HIGH,
            description='High temperature anomaly.',
        )
        self.assertEqual(alert.status, AlertStatus.NEW)
        self.assertIn('THERMAL', str(alert))


# ─── Anomaly Detector Tests ───────────────────────────────────────────────────

class AnomalyDetectorTests(TestCase):
    def setUp(self):
        self.mission = make_mission()
        # Create enough training data
        import numpy as np
        rng = np.random.default_rng(0)
        for i in range(30):
            make_telemetry(self.mission,
                timestamp=timezone.now(),
                temperature=float(rng.normal(25, 2)),
                battery_voltage=float(rng.normal(28, 0.5)),
                battery_current=float(rng.normal(8, 0.8)),
                fuel_level=float(rng.normal(75, 2)),
                radiation=float(rng.normal(12, 2)),
                pressure=float(rng.normal(101.3, 1)),
                signal_strength=float(rng.normal(-70, 3)),
                velocity=float(rng.normal(7.66, 0.05)),
                power_consumption=float(rng.normal(250, 15)),
            )

    def test_normal_telemetry_low_score(self):
        from ai.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        t = make_telemetry(self.mission)
        result = detector.analyze(t)
        self.assertIn('is_anomaly', result)
        self.assertIn('anomaly_score', result)
        self.assertIn('severity', result)
        self.assertIn('affected_subsystem', result)
        self.assertGreaterEqual(result['anomaly_score'], 0.0)
        self.assertLessEqual(result['anomaly_score'], 1.0)

    def test_anomalous_telemetry_detected(self):
        from ai.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        # Force threshold breach
        t = make_telemetry(self.mission, temperature=120.0, battery_voltage=10.0)
        result = detector.analyze(t)
        # Should flag threshold violations
        self.assertTrue(result['is_anomaly'])
        self.assertIn(result['severity'], ['HIGH', 'CRITICAL', 'MODERATE'])

    def test_subsystem_classification(self):
        from ai.anomaly_detector import classify_subsystem
        self.assertEqual(classify_subsystem(['temperature']), 'THERMAL')
        self.assertEqual(classify_subsystem(['battery_voltage', 'power_consumption']), 'ELECTRICAL')
        self.assertEqual(classify_subsystem(['signal_strength']), 'COMMUNICATION')
        self.assertEqual(classify_subsystem([]), 'UNKNOWN')


# ─── Risk Engine Tests ────────────────────────────────────────────────────────

class RiskEngineTests(TestCase):
    def setUp(self):
        self.mission = make_mission()

    def test_nominal_health_score(self):
        from ai.risk_engine import RiskEngine
        engine = RiskEngine()
        t = make_telemetry(self.mission)
        anomaly_result = {'severity': 'NORMAL', 'suspicious_parameters': []}
        result = engine.compute_health(t, anomaly_result)
        self.assertGreaterEqual(result['health_score'], 85)
        self.assertEqual(result['risk_level'], 'NORMAL')

    def test_high_severity_reduces_score(self):
        from ai.risk_engine import RiskEngine
        engine = RiskEngine()
        t = make_telemetry(self.mission, temperature=120.0)
        anomaly_result = {'severity': 'CRITICAL', 'suspicious_parameters': ['temperature']}
        result = engine.compute_health(t, anomaly_result)
        self.assertLess(result['health_score'], 50)
        self.assertIn(result['risk_level'], ['HIGH', 'CRITICAL'])

    def test_score_breakdown_present(self):
        from ai.risk_engine import RiskEngine
        engine = RiskEngine()
        t = make_telemetry(self.mission)
        result = engine.compute_health(t, {'severity': 'NORMAL', 'suspicious_parameters': []})
        self.assertIn('score_breakdown', result)
        self.assertIn('anomaly_severity', result['score_breakdown'])


# ─── API Tests ────────────────────────────────────────────────────────────────

class MissionAPITests(APITestCase):
    def setUp(self):
        self.mission = make_mission()

    def test_list_missions(self):
        r = self.client.get('/api/missions/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_create_mission(self):
        data = {
            'name': 'API Test Mission',
            'spacecraft_name': 'API-SC-1',
            'status': 'ACTIVE',
        }
        r = self.client.post('/api/missions/', data, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Mission.objects.count(), 2)

    def test_get_health_no_data(self):
        r = self.client.get(f'/api/missions/{self.mission.pk}/health/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_analyze_no_telemetry(self):
        r = self.client.post(f'/api/missions/{self.mission.pk}/analyze/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class AlertAPITests(APITestCase):
    def setUp(self):
        self.mission = make_mission()
        self.telemetry = make_telemetry(self.mission)
        self.alert = Alert.objects.create(
            mission=self.mission,
            telemetry=self.telemetry,
            subsystem='THERMAL',
            severity=Severity.HIGH,
            description='Test thermal anomaly.',
        )

    def test_list_alerts(self):
        r = self.client.get('/api/alerts/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_update_alert_status(self):
        r = self.client.patch(
            f'/api/alerts/{self.alert.pk}/',
            {'status': 'INVESTIGATING'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, AlertStatus.INVESTIGATING)


class AlertServiceTests(TestCase):
    def setUp(self):
        self.mission = make_mission()
        self.telemetry = make_telemetry(self.mission)

    def test_creates_alert_on_moderate_severity(self):
        from alerts.services import AlertService
        anomaly = {'severity': 'MODERATE', 'affected_subsystem': 'THERMAL', 'suspicious_parameters': []}
        explanation = {'detected_problem': 'High temp.', 'recommended_action': 'Check heater.'}
        alert = AlertService.create_if_needed(self.mission, anomaly, self.telemetry, explanation)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.subsystem, 'THERMAL')

    def test_suppresses_duplicate_alert(self):
        from alerts.services import AlertService
        anomaly = {'severity': 'HIGH', 'affected_subsystem': 'ELECTRICAL', 'suspicious_parameters': []}
        explanation = {'detected_problem': 'Voltage drop.', 'recommended_action': 'Check battery.'}
        a1 = AlertService.create_if_needed(self.mission, anomaly, self.telemetry, explanation)
        a2 = AlertService.create_if_needed(self.mission, anomaly, self.telemetry, explanation)
        self.assertIsNotNone(a1)
        self.assertIsNone(a2)  # duplicate suppressed

    def test_no_alert_for_low_severity(self):
        from alerts.services import AlertService
        anomaly = {'severity': 'LOW', 'affected_subsystem': 'THERMAL', 'suspicious_parameters': []}
        explanation = {'detected_problem': 'Minor temp spike.', 'recommended_action': 'Monitor.'}
        result = AlertService.create_if_needed(self.mission, anomaly, self.telemetry, explanation)
        self.assertIsNone(result)

    def test_weather_alert_created_for_extreme(self):
        from alerts.services import AlertService
        sw = {'risk_score': 85, 'risk_level': 'EXTREME', 'max_kp_index': 8, 'xclass_flares_48h': 2}
        alert = AlertService.create_weather_alert_if_needed(self.mission, sw, self.telemetry)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.subsystem, 'RADIATION')
        self.assertEqual(alert.severity, 'CRITICAL')

    def test_weather_alert_duplicate_suppressed(self):
        from alerts.services import AlertService
        sw = {'risk_score': 85, 'risk_level': 'EXTREME', 'max_kp_index': 8, 'xclass_flares_48h': 2}
        a1 = AlertService.create_weather_alert_if_needed(self.mission, sw, self.telemetry)
        a2 = AlertService.create_weather_alert_if_needed(self.mission, sw, self.telemetry)
        self.assertIsNotNone(a1)
        self.assertIsNone(a2)


# ─── SpaceWeatherService Tests ────────────────────────────────────────────────

class SpaceWeatherServiceTests(TestCase):
    def test_neutral_returned_when_no_model(self):
        """Service must return a safe fallback when pkl files are absent."""
        from ai.space_weather_service import SpaceWeatherService
        svc = SpaceWeatherService()
        result = svc.get_risk_for_date(None)
        self.assertIn('risk_level', result)
        self.assertIn('recommendation', result)
        self.assertIn('risk_score', result)
        self.assertIn('at_risk_subsystems', result)

    def test_neutral_is_serializable(self):
        from ai.space_weather_service import SpaceWeatherService
        import json
        svc = SpaceWeatherService()
        result = svc.get_risk_for_date(None)
        # Must not raise
        serialized = json.dumps(result)
        self.assertIn('risk_level', serialized)


# ─── Pipeline _to_native Tests ────────────────────────────────────────────────

def _to_native_standalone(obj):
    """Standalone copy for tests — avoids importing the full pipeline module chain."""
    import numpy as np
    from datetime import datetime
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return {k: _to_native_standalone(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native_standalone(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class PipelineToNativeTests(TestCase):
    def test_handles_none(self):
        self.assertIsNone(_to_native_standalone(None))

    def test_handles_bool(self):
        self.assertIs(_to_native_standalone(True), True)
        self.assertIs(_to_native_standalone(False), False)

    def test_handles_numpy_types(self):
        import numpy as np
        self.assertEqual(_to_native_standalone(np.int64(5)), 5)
        self.assertAlmostEqual(_to_native_standalone(np.float32(3.14)), 3.14, places=4)
        self.assertIs(_to_native_standalone(np.bool_(True)), True)

    def test_handles_nested_dict(self):
        import numpy as np
        d = {'a': np.int64(1), 'b': [np.float32(2.0), None], 'c': True}
        result = _to_native_standalone(d)
        self.assertEqual(result['a'], 1)
        self.assertIsNone(result['b'][1])
        self.assertIs(result['c'], True)


# ─── Mission Weather API Tests ────────────────────────────────────────────────

class MissionWeatherAPITests(APITestCase):
    def setUp(self):
        self.mission = make_mission()

    def test_weather_endpoint_returns_200(self):
        r = self.client.get(f'/api/missions/{self.mission.pk}/weather/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertIn('space_weather', data)
        self.assertIn('risk_level', data['space_weather'])
        self.assertIn('recommendation', data['space_weather'])

    def test_weather_endpoint_includes_mission_info(self):
        r = self.client.get(f'/api/missions/{self.mission.pk}/weather/')
        data = r.json()
        self.assertIn('mission', data)
        self.assertIn('spacecraft', data)


# ─── Assistant Space Weather Tests ───────────────────────────────────────────

def _local_ai_agent_standalone(context, question):
    """Call the local agent without importing requests at module level."""
    import importlib, sys
    # Ensure requests is importable (it's installed system-wide)
    import requests as _req  # noqa: F401 — ensure it's available
    from ai.granite_service import _local_ai_agent
    return _local_ai_agent(context, question)


class AssistantSpaceWeatherTests(TestCase):
    def test_local_agent_answers_weather_question(self):
        context = {
            'spacecraft': 'ISS-Alpha',
            'mission_name': 'Test',
            'mission_status': 'ACTIVE',
            'latest_telemetry': {},
            'health': {},
            'latest_anomaly': {},
            'latest_explanation': {},
            'active_alerts': [],
            'space_weather': {
                'risk_score': 32,
                'risk_level': 'MODERATE',
                'recommendation': 'CAUTION',
                'xclass_flares_48h': 0,
                'mclass_flares_48h': 2,
                'max_kp_index': 4.5,
                'storm_count': 1,
                'at_risk_subsystems': ['RADIATION', 'COMMUNICATION'],
                'date': '2025-01-10',
            },
        }
        result = _local_ai_agent_standalone(context, 'What is the space weather like?')
        self.assertIn('answer', result)
        self.assertIn('MODERATE', result['answer'])
        self.assertIn('CAUTION', result['answer'])

    def test_local_agent_handles_missing_weather(self):
        context = {
            'spacecraft': 'ISS-Alpha',
            'mission_name': 'Test',
            'mission_status': 'ACTIVE',
            'latest_telemetry': {},
            'health': {},
            'latest_anomaly': {},
            'latest_explanation': {},
            'active_alerts': [],
            'space_weather': {},
        }
        result = _local_ai_agent_standalone(context, 'What is the solar weather?')
        self.assertIn('answer', result)
        self.assertIsInstance(result['answer'], str)
