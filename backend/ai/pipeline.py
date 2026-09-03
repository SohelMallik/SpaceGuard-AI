"""
SpaceGuard AI — Analysis Pipeline Orchestrator
Runs the full AI pipeline: anomaly → health → predictions → space weather → Granite → alert.
"""
import logging
from datetime import datetime, timezone

from ai.anomaly_detector import AnomalyDetector
from ai.risk_engine import RiskEngine
from ai.predictor import TrendPredictor
from ai.granite_service import GraniteService
from ai.space_weather_service import SpaceWeatherService

logger = logging.getLogger(__name__)

_detector = AnomalyDetector()
_risk_engine = RiskEngine()
_predictor = TrendPredictor()
_granite = GraniteService()
_weather = SpaceWeatherService()


def _to_native(obj):
    """Recursively convert numpy/datetime types to native Python for JSON serialization."""
    import numpy as np
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


def run_analysis_pipeline(telemetry_record) -> dict:
    """
    Full AI pipeline for one telemetry record.
    Returns a complete analysis dict that is saved to AIAnalysis and returned to the API.
    """
    mission = telemetry_record.mission

    # 1. Anomaly detection
    anomaly_result = _to_native(_detector.analyze(telemetry_record))

    # 2. Save anomaly fields back to the telemetry record
    telemetry_record.anomaly_score = anomaly_result['anomaly_score']
    telemetry_record.is_anomaly = anomaly_result['is_anomaly']
    telemetry_record.save(update_fields=['anomaly_score', 'is_anomaly'])

    # 3. Health score computation (use last 10 records for trend penalty)
    recent = list(mission.telemetry_records.order_by('-timestamp')[:10])
    health_result = _to_native(
        _risk_engine.compute_health(telemetry_record, anomaly_result, recent_records=recent)
    )

    # 4. Trend predictions
    predictions = _to_native(_predictor.predict_all(mission))

    # 5. Space weather risk for the telemetry timestamp
    record_date = telemetry_record.timestamp.date() if telemetry_record.timestamp else None
    space_weather = _to_native(_weather.get_risk_for_date(record_date))

    # Escalate anomaly severity if space weather is HIGH/EXTREME and sensor radiation is elevated
    if (
        space_weather.get('risk_level') in ('HIGH', 'EXTREME')
        and telemetry_record.radiation > 30
        and anomaly_result['severity'] == 'NORMAL'
    ):
        anomaly_result['severity'] = 'LOW'
        anomaly_result['suspicious_parameters'] = anomaly_result.get('suspicious_parameters', []) + ['radiation']
        anomaly_result['affected_subsystem'] = 'RADIATION'
        anomaly_result['space_weather_escalated'] = True

    # 6. Build telemetry context dict (only real measured values)
    telemetry_data = {
        'timestamp': str(telemetry_record.timestamp),
        'spacecraft': mission.spacecraft_name,
        'mission': mission.name,
        'temperature': telemetry_record.temperature,
        'battery_voltage': telemetry_record.battery_voltage,
        'battery_current': telemetry_record.battery_current,
        'fuel_level': telemetry_record.fuel_level,
        'radiation': telemetry_record.radiation,
        'pressure': telemetry_record.pressure,
        'signal_strength': telemetry_record.signal_strength,
        'velocity': telemetry_record.velocity,
        'power_consumption': telemetry_record.power_consumption,
    }

    # 7. IBM Granite explanation (only for non-NORMAL severity)
    if anomaly_result['severity'] != 'NORMAL':
        explanation = _granite.explain_anomaly(
            telemetry_data, anomaly_result, health_result, predictions, space_weather
        )
    else:
        explanation = {
            'detected_problem': 'No anomaly detected. All systems nominal.',
            'affected_subsystem': 'NONE',
            'severity': 'NORMAL',
            'evidence': 'All sensor readings are within normal operating ranges.',
            'possible_cause': 'N/A',
            'recommended_action': 'Continue nominal operations.',
            'generated_by': 'Rule-Based (Normal Condition)',
        }

    # 8. Create alert if severity warrants it; also create weather alert if EXTREME
    from alerts.services import AlertService
    if anomaly_result['severity'] in ('MODERATE', 'HIGH', 'CRITICAL'):
        AlertService.create_if_needed(mission, anomaly_result, telemetry_record, explanation)
    if space_weather.get('risk_level') == 'EXTREME':
        AlertService.create_weather_alert_if_needed(mission, space_weather, telemetry_record)

    # 9. Save full analysis to AIAnalysis model
    from anomaly.models import AIAnalysis, AnalysisType
    input_context = {
        'telemetry': telemetry_data,
        'anomaly': anomaly_result,
        'health': health_result,
        'predictions': predictions,
        'space_weather': space_weather,
    }
    result_data = {
        'health': health_result,
        'anomaly': anomaly_result,
        'explanation': explanation,
        'predictions': predictions,
        'space_weather': space_weather,
    }

    AIAnalysis.objects.create(
        mission=mission,
        telemetry=telemetry_record,
        analysis_type=AnalysisType.EXPLANATION,
        input_context=input_context,
        result=result_data,
        raw_response=explanation.get('raw_response', ''),
    )

    return {
        'telemetry_id': telemetry_record.id,
        'anomaly': anomaly_result,
        'health': health_result,
        'predictions': predictions,
        'explanation': explanation,
        'space_weather': space_weather,
    }
