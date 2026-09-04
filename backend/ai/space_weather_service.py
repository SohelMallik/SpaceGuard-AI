"""
SpaceGuard AI — Space Weather Service
Loads the trained Random Forest model (space-weather-predictor) and provides
per-date launch risk scores to the SpaceGuard mission pipeline.
Falls back gracefully to a rule-based low-risk response if model files are absent.
"""
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Paths are relative to the monorepo root (two levels above backend/)
_MODEL_PKL = Path(__file__).resolve().parents[3] / 'models' / 'launch_decision_model.pkl'
_DATA_PKL  = Path(__file__).resolve().parents[3] / 'models' / 'space_weather_data.pkl'

RECOMMENDATION_MAP = {
    'LOW':      'GO',
    'MODERATE': 'CAUTION',
    'HIGH':     'DELAY',
    'EXTREME':  'NO-GO',
}

RISK_IMPACT = {
    # risk_level → which spacecraft subsystems to watch
    'LOW':      [],
    'MODERATE': ['RADIATION', 'COMMUNICATION'],
    'HIGH':     ['RADIATION', 'THERMAL', 'COMMUNICATION', 'ELECTRICAL'],
    'EXTREME':  ['RADIATION', 'THERMAL', 'COMMUNICATION', 'ELECTRICAL', 'NAVIGATION'],
}


class SpaceWeatherService:
    """
    Provides space weather risk data keyed to a calendar date.
    Uses cached pkl artefacts produced by the space-weather-predictor pipeline.
    """

    def __init__(self):
        self._data = None   # cached space_weather_data dict
        self._model = None  # cached Random Forest model
        self._loaded = False

    def _load(self):
        """Lazy-load model and data files once."""
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

            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'])

            if query_date is not None:
                target = pd.Timestamp(query_date)
                # Find exact or nearest previous date
                past = df[df['date'] <= target]
                row = past.iloc[-1] if not past.empty else df.iloc[-1]
            else:
                row = df.iloc[-1]

            risk_score = float(row.get('risk_score', 0))
            risk_level = str(row.get('risk_level', 'LOW'))
            recommendation = RECOMMENDATION_MAP.get(risk_level, 'GO')
            xclass  = int(row.get('xclass_flare_count', 0))
            mclass  = int(row.get('mclass_flare_count', 0))
            max_kp  = float(row.get('max_kp_index', 0))
            trend   = float(row.get('event_trend', 1.0))
            storm_c = int(row.get('storm_count', 0))

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
