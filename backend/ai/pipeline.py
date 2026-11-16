"""
SpaceGuard AI — Analysis Pipeline Orchestrator
Runs the full AI pipeline: anomaly → health → predictions → space weather → Granite → alert.

What this module does
---------------------
`run_analysis_pipeline()` is the single entry point called after every
telemetry record is saved. It chains all the AI services in order, persists
the results (anomaly fields on the telemetry record, a new AIAnalysis row,
alerts when severity warrants) and returns the combined analysis dict to the
API layer. All services are lazily-created shared singletons so expensive ML
models are loaded only once per process.
"""
import logging
from datetime import datetime, timezone

from ai.anomaly_detector import AnomalyDetector
from ai.risk_engine import RiskEngine
from ai.predictor import TrendPredictor
from ai.granite_service import GraniteService
from ai.space_weather_service import SpaceWeatherService

logger = logging.getLogger(__name__)

# Module-level singletons are initialized lazily so that importing this module
# never loads ML models or reads credentials at startup (important for tests,
# migrations and cold starts).

_detector = None
_risk_engine = None
_predictor = None
_granite = None
_weather = None


def get_detector() -> AnomalyDetector:
    """Lazily initialized AnomalyDetector singleton."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


def get_risk_engine() -> RiskEngine:
    """Lazily initialized RiskEngine singleton."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine


def get_predictor() -> TrendPredictor:
    """Lazily initialized TrendPredictor singleton."""
    global _predictor
    if _predictor is None:
        _predictor = TrendPredictor()
    return _predictor


def get_granite() -> GraniteService:
    """Lazily initialized GraniteService singleton (shared across all callers)."""
    global _granite
    if _granite is None:
        _granite = GraniteService()
    return _granite


def get_weather_service() -> SpaceWeatherService:
    """Lazily initialized SpaceWeatherService singleton."""
    global _weather
    if _weather is None:
        _weather = SpaceWeatherService()
    return _weather


def _to_native(obj):
    """
    Recursively convert numpy/datetime types to native Python for JSON serialization.

    ML libraries return numpy scalars (np.integer, np.floating, np.bool_)
    and sklearn outputs can carry them inside result dicts. Those types are
    not JSON-serializable by Django/DRF, so every value that will be stored
    in a JSONField or returned by the API is passed through here first.
    """
    import numpy as np
    if obj is None:
        return None
    # bool must be checked first: in Python, bool is a subclass of int
    if isinstance(obj, bool):
        return obj
    # Recurse into containers so nested numpy values are converted too
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    # numpy scalar types → their plain-Python equivalents
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    # datetime objects → ISO-8601 strings (JSON has no native date type)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


def run_analysis_pipeline(telemetry_record) -> dict:
    """
    Full AI pipeline for one telemetry record.
    Returns a complete analysis dict that is saved to AIAnalysis and returned to the API.

    Order of operations: anomaly detection → persist anomaly fields → health
    score → trend predictions → space weather → severity escalation → Granite
    explanation → alerts → AIAnalysis record. Every result is converted via
    `_to_native` so the returned dict is safely JSON-serializable.
    """
    mission = telemetry_record.mission

    # 1. Anomaly detection
    anomaly_result = _to_native(get_detector().analyze(telemetry_record))

    # 2. Save anomaly fields back to the telemetry record
    telemetry_record.anomaly_score = anomaly_result['anomaly_score']
    telemetry_record.is_anomaly = anomaly_result['is_anomaly']
    telemetry_record.save(update_fields=['anomaly_score', 'is_anomaly'])

    # 3. Health score computation (use last 10 records for trend penalty)
    #    Ordered newest → oldest; the risk engine only uses these for the
    #    "is the situation getting worse?" trend deduction
    recent = list(mission.telemetry_records.order_by('-timestamp')[:10])
    health_result = _to_native(
        get_risk_engine().compute_health(telemetry_record, anomaly_result, recent_records=recent)
    )

    # 4. Trend predictions
    predictions = _to_native(get_predictor().predict_all(mission))

    # 5. Space weather risk for the telemetry timestamp
    record_date = telemetry_record.timestamp.date() if telemetry_record.timestamp else None
    space_weather = _to_native(get_weather_service().get_risk_for_date(record_date))

    # Escalate anomaly severity if space weather is HIGH/EXTREME and sensor radiation is elevated.
    # Why: solar storms can push radiation above safe levels without tripping
    # the ML model (which learned "normal" mostly from quiet-space data). If
    # space weather is HIGH/EXTREME, radiation exceeds 30 mSv and the ML still
    # said NORMAL, upgrade the severity to LOW and blame the RADIATION
    # subsystem so operators do not miss the correlation.
    if (
        space_weather.get('risk_level') in ('HIGH', 'EXTREME')
        and telemetry_record.radiation > 30
        and anomaly_result['severity'] == 'NORMAL'
    ):
        # Only the result dict is mutated — the model's own verdict is untouched
        anomaly_result['severity'] = 'LOW'
        anomaly_result['suspicious_parameters'] = anomaly_result.get('suspicious_parameters', []) + ['radiation']
        anomaly_result['affected_subsystem'] = 'RADIATION'
        # Marker the frontend/explanation uses to explain why severity was raised
        anomaly_result['space_weather_escalated'] = True

    # 6. Build telemetry context dict (only real measured values)
    #    Injected verbatim into the Granite prompt so the LLM can only quote
    #    genuine sensor readings — never hallucinate any
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
    #    Skipping the LLM call for healthy records saves latency and API cost
    if anomaly_result['severity'] != 'NORMAL':
        explanation = get_granite().explain_anomaly(
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
    #    (Django models are imported inside the function so importing this
    #    module never touches the ORM — keeps tests and migrations safe)
    from alerts.services import AlertService
    if anomaly_result['severity'] in ('MODERATE', 'HIGH', 'CRITICAL'):
        AlertService.create_if_needed(mission, anomaly_result, telemetry_record, explanation)
    if space_weather.get('risk_level') == 'EXTREME':
        AlertService.create_weather_alert_if_needed(mission, space_weather, telemetry_record)

    # 9. Save full analysis to AIAnalysis model
    #    input_context = everything the AI saw (for reproducibility/auditing)
    #    result        = everything the AI produced (what the API returns)
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
