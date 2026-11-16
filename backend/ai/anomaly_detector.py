"""
SpaceGuard AI — Anomaly Detection Service
Uses Isolation Forest (scikit-learn) to detect multi-parameter anomalies.

What this module does
---------------------
An Isolation Forest is an *unsupervised* model: it is trained on telemetry
(no fault labels) and learns what typical readings look like. At inference
time it measures how easily a record can be "isolated" from the rest by
random splits of the feature space — an unusual reading is isolated in very
few splits, which shows up as a lower (more negative) raw score. On top of
the ML verdict this module applies plain threshold rules (THRESHOLDS below),
so obviously dangerous readings are still flagged even when the model has
never seen anything like them.

How it fits the pipeline
------------------------
`pipeline.run_analysis_pipeline()` calls `AnomalyDetector.analyze()` first;
its output (is_anomaly, anomaly_score, severity, suspicious_parameters,
affected_subsystem) feeds the RiskEngine, the TrendPredictor and the Granite
explanation prompt.
"""
import os
import logging
import numpy as np
import joblib
from django.conf import settings

logger = logging.getLogger(__name__)

# Feature columns used for ML detection. Order matters: the synthetic-data
# fallback in AnomalyDetector.train() fills its per-sensor means/scales in
# exactly this order.
FEATURE_COLUMNS = [
    'temperature', 'battery_voltage', 'battery_current',
    'fuel_level', 'radiation', 'pressure',
    'signal_strength', 'velocity', 'power_consumption',
]

# Normal operating ranges (used for threshold-based rules and subsystem mapping)
# Per sensor:
#   'min'/'max'                     → normal band; outside it = warning violation
#   'critical_min' / 'critical_max' → optional harder limits; crossing one is
#                                     immediately treated as a CRITICAL breach
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
    """Return the most likely affected subsystem from a list of anomalous parameters.

    Counts how many suspicious parameters belong to each subsystem (via
    SUBSYSTEM_MAP) and returns the one with the most hits — e.g. both
    battery_voltage and power_consumption failing points at ELECTRICAL.
    """
    if not suspicious_params:
        return 'UNKNOWN'
    # Tally suspicious parameters per subsystem
    counts = {}
    for param in suspicious_params:
        subsystem = SUBSYSTEM_MAP.get(param, 'UNKNOWN')
        counts[subsystem] = counts.get(subsystem, 0) + 1
    return max(counts, key=counts.get)


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector.
    Trains on available telemetry, caches the model to disk.

    How Isolation Forest works: it builds random trees that split the feature
    space and measures how many splits are needed to isolate each record.
    Normal readings (similar to the training data) need many splits; outliers
    are isolated quickly. `contamination=0.1` tells scikit-learn to expect
    roughly 10% of the data to be anomalous, which sets the decision
    threshold `predict()` uses (output -1 = anomaly, +1 = normal). The model
    is cached to disk (joblib) so it is trained once and then reused.
    """

    MODEL_PATH = None  # set in __init__

    def __init__(self):
        # Trained models live in settings.ML_MODELS_DIR; this one is a joblib
        # pickle that `joblib.load` can restore without retraining
        self.MODEL_PATH = settings.ML_MODELS_DIR / 'isolation_forest.pkl'
        # In-memory cache so the .pkl file is read at most once per process
        self._model = None

    def _get_model(self):
        """
        Load from disk if available, otherwise return None (train required).
        The loaded model is memoized in `self._model` for later calls.
        """
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

        Hyperparameters (same in both branches):
          n_estimators=100 → number of random trees in the forest
          contamination=0.1 → expect ~10% of records to be outliers
          random_state=42  → fixed seed so results are reproducible

        With fewer than 10 real records there is not enough data to learn
        what "normal" looks like, so the model is fitted on 200 synthetic
        records sampled around known-nominal sensor values instead.
        """
        from sklearn.ensemble import IsolationForest

        records = list(telemetry_queryset.values(*FEATURE_COLUMNS))
        if len(records) < 10:
            logger.warning('Insufficient training data (%d records). Using default model.', len(records))
            model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            # generate synthetic normal data to seed the model:
            # draw 200 samples from Gaussian distributions whose means (`loc`)
            # and standard deviations (`scale`) are the nominal values of the
            # 9 sensors, in FEATURE_COLUMNS order — e.g. temperature ≈ 25 °C,
            # battery ≈ 28 V, pressure ≈ 101 kPa, signal ≈ −70 dBm ...
            rng = np.random.default_rng(42)
            X_synthetic = rng.normal(
                loc=[25, 28, 8, 75, 10, 101, -70, 7.5, 250],
                scale=[5, 1, 1, 5, 3, 2, 5, 0.5, 30],
                size=(200, 9),
            )
            model.fit(X_synthetic)
        else:
            # Build the (n_records × 9) feature matrix from real telemetry
            X = np.array([[r[col] for col in FEATURE_COLUMNS] for r in records])
            model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            model.fit(X)
            logger.info('Trained Isolation Forest on %d records.', len(records))

        # Persist so later processes can joblib.load() instead of retraining
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

        Combines two independent signals:
          1. the ML verdict from the Isolation Forest (is_anomaly, anomaly_score),
          2. threshold rules on each sensor (suspicious_parameters), which
             then drive the severity ladder (LOW → MODERATE → HIGH → CRITICAL).
        """
        mission = telemetry_record.mission
        model = self.load_or_train(mission)

        # Build feature vector — a 1×9 matrix in exactly the column order used
        # during training (FEATURE_COLUMNS)
        features = np.array([[
            getattr(telemetry_record, col) for col in FEATURE_COLUMNS
        ]])

        # Isolation Forest score: -1 anomaly, 1 normal
        prediction = model.predict(features)[0]
        raw_score = model.score_samples(features)[0]  # more negative = more anomalous
        # `score_samples` returns the raw isolation score, roughly in (-1, 1):
        # near +1 for clearly normal points, near -1 for strong anomalies.
        # Normalize to 0-1 range (0 = normal, 1 = critical anomaly):
        # (-raw - 0.3) / 0.7 shifts the scale so a raw score of about -0.3
        # maps to 0.0 and about -1.0 maps to 1.0; the outer min/max clamps
        # mild in-between values into the valid [0, 1] band.
        anomaly_score = float(max(0.0, min(1.0, (-raw_score - 0.3) / 0.7)))
        is_anomaly = prediction == -1

        # Identify suspicious parameters (those outside normal thresholds).
        # These are the plain-English evidence backing the ML verdict.
        suspicious_params = []
        for col, limits in THRESHOLDS.items():
            val = getattr(telemetry_record, col)
            if val < limits['min'] or val > limits['max']:
                suspicious_params.append(col)

        # Rule-based severity escalation.
        # Ladder, highest rung first: any sensor past its hard critical limit
        # (critical_min/critical_max) is CRITICAL and stops the loop.
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

        # No hard critical breach → grade the severity from the ML anomaly
        # score and the number of threshold warnings
        if severity == 'NORMAL':
            if anomaly_score >= 0.7:
                severity = 'HIGH'
            elif anomaly_score >= 0.5 or suspicious_params:
                severity = 'MODERATE'
            elif anomaly_score >= 0.3:
                severity = 'LOW'
            elif is_anomaly:
                severity = 'LOW'

        # Subsystem with the most suspicious parameters wins (see helper above)
        affected_subsystem = classify_subsystem(suspicious_params)

        return {
            # Flagged if the ML model OR the threshold rules fired
            'is_anomaly': is_anomaly or bool(suspicious_params),
            'anomaly_score': round(anomaly_score, 4),
            'severity': severity,
            'suspicious_parameters': suspicious_params,
            'affected_subsystem': affected_subsystem,
        }
