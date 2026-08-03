"""
SpaceGuard AI — Anomaly Detection Service
Uses Isolation Forest (scikit-learn) to detect multi-parameter anomalies.
"""
import os
import logging
import numpy as np
import joblib
from django.conf import settings

logger = logging.getLogger(__name__)

# Feature columns used for ML detection
FEATURE_COLUMNS = [
    'temperature', 'battery_voltage', 'battery_current',
    'fuel_level', 'radiation', 'pressure',
    'signal_strength', 'velocity', 'power_consumption',
]

# Normal operating ranges (used for threshold-based rules and subsystem mapping)
THRESHOLDS = {
    'temperature':       {'min': -50, 'max': 85,   'critical_max': 100},
    'battery_voltage':   {'min': 22,  'max': 32,   'critical_min': 18},
    'battery_current':   {'min': -5,  'max': 20,   'critical_max': 25},
    'fuel_level':        {'min': 5,   'max': 100,  'critical_min': 5},
    'radiation':         {'min': 0,   'max': 50,   'critical_max': 100},
    'pressure':          {'min': 95,  'max': 110,  'critical_max': 120},
    'signal_strength':   {'min': -120,'max': -40,  'critical_min': -130},
    'velocity':          {'min': 0,   'max': 30,   'critical_max': 35},
    'power_consumption': {'min': 0,   'max': 500,  'critical_max': 600},
}

# Maps sensor parameters to spacecraft subsystems
SUBSYSTEM_MAP = {
    'temperature':       'THERMAL',
    'radiation':         'RADIATION',
    'pressure':          'ENVIRONMENTAL',
    'battery_voltage':   'ELECTRICAL',
    'battery_current':   'ELECTRICAL',
    'power_consumption': 'ELECTRICAL',
    'signal_strength':   'COMMUNICATION',
    'fuel_level':        'PROPULSION',
    'velocity':          'NAVIGATION',
}


def classify_subsystem(suspicious_params: list) -> str:
    """Return the most likely affected subsystem from a list of anomalous parameters."""
    if not suspicious_params:
        return 'UNKNOWN'
    counts = {}
    for param in suspicious_params:
        subsystem = SUBSYSTEM_MAP.get(param, 'UNKNOWN')
        counts[subsystem] = counts.get(subsystem, 0) + 1
    return max(counts, key=counts.get)


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector.
    Trains on available telemetry, caches the model to disk.
    """

    MODEL_PATH = None  # set in __init__

    def __init__(self):
        self.MODEL_PATH = settings.ML_MODELS_DIR / 'isolation_forest.pkl'
        self._model = None

    def _get_model(self):
        """Load from disk if available, otherwise return None (train required)."""
        if self._model is not None:
            return self._model
        if os.path.exists(self.MODEL_PATH):
            try:
                self._model = joblib.load(self.MODEL_PATH)
                logger.info('Loaded Isolation Forest model from %s', self.MODEL_PATH)
                return self._model
            except Exception as exc:
                logger.warning('Failed to load cached model: %s', exc)
        return None

    def train(self, telemetry_queryset):
        """
        Train the Isolation Forest on the provided telemetry queryset.
        Saves the model to disk after training.
        """
        from sklearn.ensemble import IsolationForest

        records = list(telemetry_queryset.values(*FEATURE_COLUMNS))
        if len(records) < 10:
            logger.warning('Insufficient training data (%d records). Using default model.', len(records))
            model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            # generate synthetic normal data to seed the model
            rng = np.random.default_rng(42)
            X_synthetic = rng.normal(
                loc=[25, 28, 8, 75, 10, 101, -70, 7.5, 250],
                scale=[5, 1, 1, 5, 3, 2, 5, 0.5, 30],
                size=(200, 9),
            )
            model.fit(X_synthetic)
        else:
            X = np.array([[r[col] for col in FEATURE_COLUMNS] for r in records])
            model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            model.fit(X)
            logger.info('Trained Isolation Forest on %d records.', len(records))

        os.makedirs(self.MODEL_PATH.parent, exist_ok=True)
        joblib.dump(model, self.MODEL_PATH)
        self._model = model
        return model

    def load_or_train(self, mission):
        """Load cached model or train on all mission telemetry."""
        model = self._get_model()
        if model is None:
            queryset = mission.telemetry_records.all()
            model = self.train(queryset)
        return model

    def analyze(self, telemetry_record) -> dict:
        """
        Analyze a single telemetry record.
        Returns a structured result dict with anomaly classification.
        """
        mission = telemetry_record.mission
        model = self.load_or_train(mission)

        # Build feature vector
        features = np.array([[
            getattr(telemetry_record, col) for col in FEATURE_COLUMNS
        ]])

        # Isolation Forest score: -1 anomaly, 1 normal
        prediction = model.predict(features)[0]
        raw_score = model.score_samples(features)[0]  # more negative = more anomalous
        # Normalize to 0-1 range (0 = normal, 1 = critical anomaly)
        anomaly_score = float(max(0.0, min(1.0, (-raw_score - 0.3) / 0.7)))
        is_anomaly = prediction == -1

        # Identify suspicious parameters (those outside normal thresholds)
        suspicious_params = []
        for col, limits in THRESHOLDS.items():
            val = getattr(telemetry_record, col)
            if val < limits['min'] or val > limits['max']:
                suspicious_params.append(col)

        # Rule-based severity escalation
        severity = 'NORMAL'
        for col in suspicious_params:
            limits = THRESHOLDS[col]
            val = getattr(telemetry_record, col)
            critical_breach = (
                ('critical_max' in limits and val > limits['critical_max']) or
                ('critical_min' in limits and val < limits['critical_min'])
            )
            if critical_breach:
                severity = 'CRITICAL'
                break

        if severity == 'NORMAL':
            if anomaly_score >= 0.7:
                severity = 'HIGH'
            elif anomaly_score >= 0.5 or suspicious_params:
                severity = 'MODERATE'
            elif anomaly_score >= 0.3:
                severity = 'LOW'
            elif is_anomaly:
                severity = 'LOW'

        affected_subsystem = classify_subsystem(suspicious_params)

        return {
            'is_anomaly': is_anomaly or bool(suspicious_params),
            'anomaly_score': round(anomaly_score, 4),
            'severity': severity,
            'suspicious_parameters': suspicious_params,
            'affected_subsystem': affected_subsystem,
        }
