"""
SpaceGuard AI — Space Weather Service
Loads the trained Random Forest model (space-weather-predictor) and provides
per-date launch risk scores to the SpaceGuard mission pipeline.
Falls back gracefully to a rule-based low-risk response if model files are absent.

What this module does
---------------------
Turns daily solar-activity measurements — sunspot activity, X-class and
M-class solar flares, the geomagnetic Kp index, storm counts — into a single
0-100 space-weather risk score plus a GO / CAUTION / DELAY / NO-GO launch
recommendation for a given calendar date.

How it fits the pipeline
------------------------
The heavy lifting happens offline in the space-weather-predictor project,
which trains a Random Forest and saves two artefacts (the model and a dict
of daily feature rows) as .pkl files under /models. This service lazy-loads
those files and serves per-date risk to `ai/pipeline.py`, which uses it to
escalate anomaly severity and raise space-weather alerts. If the artefacts
are missing, a neutral "all quiet" response is returned so nothing
downstream ever crashes.
"""
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Paths are relative to the monorepo root (two levels above backend/)
# launch_decision_model.pkl → the trained Random Forest classifier
# space_weather_data.pkl    → dict with daily 'risk_features' rows
#                             (date, flare counts, Kp index, risk score, ...)
_MODEL_PKL = Path(__file__).resolve().parents[3] / 'models' / 'launch_decision_model.pkl'
_DATA_PKL  = Path(__file__).resolve().parents[3] / 'models' / 'space_weather_data.pkl'

# Maps the model's categorical risk level to a human launch decision
RECOMMENDATION_MAP = {
    'LOW':      'GO',
    'MODERATE': 'CAUTION',
    'HIGH':     'DELAY',
    'EXTREME':  'NO-GO',
}

RISK_IMPACT = {
    # risk_level → which spacecraft subsystems to watch. More active space
    # weather threatens more subsystems: solar particles hit radiation and
    # comms first; extreme storms also disturb thermal, electrical and
    # navigation (Kp-induced errors, single-event upsets, radio blackouts).
    'LOW':      [],
    'MODERATE': ['RADIATION', 'COMMUNICATION'],
    'HIGH':     ['RADIATION', 'THERMAL', 'COMMUNICATION', 'ELECTRICAL'],
    'EXTREME':  ['RADIATION', 'THERMAL', 'COMMUNICATION', 'ELECTRICAL', 'NAVIGATION'],
}


class SpaceWeatherService:
    """
    Provides space weather risk data keyed to a calendar date.
    Uses cached pkl artefacts produced by the space-weather-predictor pipeline.

    The service is lazy and cached: the model/data files are only loaded on
    the first query, and the loaded objects stay in memory for every later
    call. All public methods return a dict and never raise.
    """

    def __init__(self):
        self._data = None   # cached space_weather_data dict
        self._model = None  # cached Random Forest model
        self._loaded = False

    def _load(self):
        """
        Lazy-load model and data files once.
        `_loaded` is set even when loading fails, so a broken artefact is not
        re-read (and re-logged) on every request — we prefer serving the
        neutral fallback over throwing repeated exceptions.
        """
        if self._loaded:
            return
        self._loaded = True
        try:
            import joblib
            if _DATA_PKL.exists():
                self._data = joblib.load(_DATA_PKL)
                logger.info('Space weather data loaded from %s', _DATA_PKL)
            else:
                logger.warning('Space weather data not found at %s — using fallback', _DATA_PKL)
            if _MODEL_PKL.exists():
                self._model = joblib.load(_MODEL_PKL)
                logger.info('Space weather model loaded from %s', _MODEL_PKL)
        except Exception as exc:
            logger.warning('Failed to load space weather artefacts: %s', exc)

    # ------------------------------------------------------------------
    def get_risk_for_date(self, query_date=None) -> dict:
        """
        Return space weather risk for a given date.
        Falls back to the most-recent known day when the exact date is absent.
        Always returns a valid dict — never raises.

        Args:
            query_date: the date to look up (date/datetime), or None for the
                        most recent record in the dataset.
        Returns:
            dict with risk_score (0-100), risk_level, launch recommendation,
            X/M-class flare counts, max Kp index, storm count, event trend
            and the list of spacecraft subsystems most at risk.
        """
        self._load()

        # If no data available, return a safe neutral response
        if not self._data:
            return self._neutral()

        try:
            import pandas as pd
            records = self._data.get('risk_features', [])
            if not records:
                return self._neutral()

            # Load the pickled daily rows into a DataFrame for date filtering
            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'])

            if query_date is not None:
                target = pd.Timestamp(query_date)
                # Find exact or nearest previous date: telemetry can exist for
                # a day with no weather row, so use the last known conditions
                # before it. If the query predates every row, fall back to the
                # latest row available rather than failing.
                past = df[df['date'] <= target]
                row = past.iloc[-1] if not past.empty else df.iloc[-1]
            else:
                # No date given → use the most recent day in the dataset
                row = df.iloc[-1]

            # Copy the model's feature columns out of the row, coercing each
            # to a plain Python type so the dict is JSON-serializable
            risk_score = float(row.get('risk_score', 0))
            risk_level = str(row.get('risk_level', 'LOW'))
            recommendation = RECOMMENDATION_MAP.get(risk_level, 'GO')
            xclass  = int(row.get('xclass_flare_count', 0))
            mclass  = int(row.get('mclass_flare_count', 0))
            max_kp  = float(row.get('max_kp_index', 0))
            trend   = float(row.get('event_trend', 1.0))
            storm_c = int(row.get('storm_count', 0))

            # One flat dict with everything the pipeline / frontend needs:
            #   xclass/mclass_flares_48h → strong solar flares in the prior
            #                              48 hours (X-class are the strongest)
            #   max_kp_index             → peak geomagnetic storm level (Kp runs 0-9)
            #   event_trend              → activity multiplier vs the previous day
            #   at_risk_subsystems       → subsystems to watch at this risk level
            return {
                'date': row['date'].strftime('%Y-%m-%d'),
                'risk_score': round(risk_score, 1),
                'risk_level': risk_level,
                'recommendation': recommendation,
                'xclass_flares_48h': xclass,
                'mclass_flares_48h': mclass,
                'max_kp_index': round(max_kp, 1),
                'storm_count': storm_c,
                'event_trend': round(trend, 2),
                'at_risk_subsystems': RISK_IMPACT.get(risk_level, []),
                'source': 'SpaceWeatherPredictor (Random Forest)',
            }
        except Exception as exc:
            logger.error('SpaceWeatherService.get_risk_for_date error: %s', exc)
            return self._neutral()

    def get_latest(self) -> dict:
        """Return the most-recent space weather risk record."""
        return self.get_risk_for_date(None)

    @staticmethod
    def _neutral() -> dict:
        """Safe 'all quiet' response used when no model/data is available —
        lets downstream code keep working with zero space-weather risk."""
        return {
            'date': str(date.today()),
            'risk_score': 0,
            'risk_level': 'LOW',
            'recommendation': 'GO',
            'xclass_flares_48h': 0,
            'mclass_flares_48h': 0,
            'max_kp_index': 0.0,
            'storm_count': 0,
            'event_trend': 1.0,
            'at_risk_subsystems': [],
            'source': 'Fallback (model not loaded)',
        }
