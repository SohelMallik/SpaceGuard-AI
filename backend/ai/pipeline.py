"""
SpaceGuard AI — Analysis Pipeline Orchestrator
Runs the full AI pipeline: anomaly → health → predictions → Granite explanation → alert.
"""
import logging
from ai.anomaly_detector import AnomalyDetector
from ai.risk_engine import RiskEngine
from ai.predictor import TrendPredictor
from ai.granite_service import GraniteService

logger = logging.getLogger(__name__)

_detector = AnomalyDetector()
_risk_engine = RiskEngine()
_predictor = TrendPredictor()
_granite = GraniteService()


def run_analysis_pipeline(telemetry_record) -> dict:
    """
    Full AI pipeline for one telemetry record.
    Returns a complete analysis dict that is saved to AIAnalysis and returned to the API.
    """
    mission = telemetry_record.mission

    def _to_native(obj):
        """Recursively convert numpy types to native Python for JSON serialization."""
        import numpy as np
        if isinstance(obj, dict):
            return {k: _to_native(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_native(v) for v in obj]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    # 1. Anomaly detection
    anomaly_result = _to_native(_detector.analyze(telemetry_record))

    # 2. Save anomaly fields back to the telemetry record
    telemetry_record.anomaly_score = anomaly_result['anomaly_score']
    telemetry_record.is_anomaly = anomaly_result['is_anomaly']
    telemetry_record.save(update_fields=['anomaly_score', 'is_anomaly'])

    # 3. Health score computation (use last 10 records for trend penalty)
    recent = list(mission.telemetry_records.order_by('-timestamp')[:10])
    health_result = _risk_engine.compute_health(telemetry_record, anomaly_result, recent_records=recent)

    # 4. Trend predictions
    predictions = _predictor.predict_all(mission)

    # 5. Build telemetry context dict (only real measured values)
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

    # 6. IBM Granite explanation (only for non-NORMAL severity)
    explanation = {}
    if anomaly_result['severity'] != 'NORMAL':
        explanation = _granite.explain_anomaly(
            telemetry_data, anomaly_result, health_result, predictions
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

    # 7. Create alert if severity warrants it
    if anomaly_result['severity'] in ('MODERATE', 'HIGH', 'CRITICAL'):
        from alerts.services import AlertService
        AlertService.create_if_needed(mission, anomaly_result, telemetry_record, explanation)

    # 8. Save full analysis to AIAnalysis model
    from anomaly.models import AIAnalysis, AnalysisType
    input_context = {
        'telemetry': telemetry_data,
        'anomaly': anomaly_result,
        'health': health_result,
        'predictions': predictions,
    }
    result_data = {
        'health': health_result,
        'anomaly': anomaly_result,
        'explanation': explanation,
        'predictions': predictions,
    }
    raw_text = explanation.get('raw_response', '')

    AIAnalysis.objects.create(
        mission=mission,
        telemetry=telemetry_record,
        analysis_type=AnalysisType.EXPLANATION,
        input_context=input_context,
        result=result_data,
        raw_response=raw_text,
    )

    return {
        'telemetry_id': telemetry_record.id,
        'anomaly': anomaly_result,
        'health': health_result,
        'predictions': predictions,
        'explanation': explanation,
    }
