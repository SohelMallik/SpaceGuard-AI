"""
SpaceGuard AI — Trend Predictor
Uses linear regression to extrapolate future parameter values and estimate
time-to-threshold crossings.

What this module does
---------------------
For each monitored parameter a straight line is fitted through the last 20
telemetry values (oldest → newest). The slope of that line is the per-minute
trend, and it is used for two things: extrapolating the value
`horizon_minutes` into the future, and estimating how many minutes remain
before a rising/falling parameter crosses its warning limit.

How it fits the pipeline
------------------------
`TrendPredictor.predict_all()` runs on every analysis in
`ai/pipeline.py`; its predictions are stored with the AIAnalysis record and
injected into the Granite explanation prompt.
"""
import numpy as np
import logging
from ai.anomaly_detector import THRESHOLDS

logger = logging.getLogger(__name__)

# Parameters actively monitored for predictions — a subset of the keys in
# anomaly_detector.THRESHOLDS chosen for their operational impact
MONITORED_PARAMS = ['temperature', 'battery_voltage', 'signal_strength', 'fuel_level', 'radiation']


class TrendPredictor:
    """
    Predicts future values of key telemetry parameters using linear regression
    over the most recent records.

    One simplifying assumption: 1 regression step ≈ 1 minute of mission time
    (telemetry arrives roughly once per minute — see the note in `predict`).
    """

    def predict(self, mission, parameter: str, horizon_minutes: int = 15) -> dict:
        """
        Predict the value of `parameter` `horizon_minutes` in the future.

        Fits a line through the last 20 records (needs at least 5), then:
          - extrapolates the value at (last index + horizon_minutes),
          - classifies the trend as STABLE / RISING / FALLING from the slope,
          - if the parameter is heading for its warning limit within the next
            60 minutes, computes the exact time-to-threshold and a warning.

        Returns:
            dict with current_value, predicted_value, trend_direction,
                       time_to_threshold_minutes, warning_message
        """
        if parameter not in THRESHOLDS:
            return {'error': f'Unknown parameter: {parameter}'}

        # Fetch last 20 records ordered oldest-first for regression
        records = list(
            mission.telemetry_records.order_by('-timestamp')[:20]
        )
        records.reverse()  # oldest first — the regression x-axis must increase with time

        if len(records) < 5:
            return {
                'parameter': parameter,
                'trend_direction': 'INSUFFICIENT_DATA',
                'current_value': None,
                'predicted_value': None,
                'time_to_threshold_minutes': None,
                'warning_message': 'Insufficient telemetry data for trend prediction.',
            }

        # y-values = the sensor readings; x-values = their position in the window
        values = np.array([getattr(r, parameter) for r in records], dtype=float)
        x = np.arange(len(values), dtype=float)

        # Linear regression: y = slope * x + intercept
        # np.polyfit(x, values, 1) returns [slope, intercept] of the best-fit line
        coeffs = np.polyfit(x, values, 1)
        slope = float(coeffs[0])
        intercept = float(coeffs[1])

        current_value = float(values[-1])
        # Each step ≈ avg telemetry interval (assume 1 step ≈ 1 minute for demo)
        # Extrapolation: index len(values)-1 is "now", so "now + horizon" is
        # evaluated at x = len(values) - 1 + horizon_minutes on the fitted line
        predicted_value = float(slope * (len(values) - 1 + horizon_minutes) + intercept)

        # Determine trend direction.
        # |slope| < 0.05 units/minute is treated as flat (sensor noise, not drift)
        if abs(slope) < 0.05:
            trend_direction = 'STABLE'
        elif slope > 0:
            trend_direction = 'RISING'
        else:
            trend_direction = 'FALLING'

        # Estimate time-to-threshold crossing.
        # Classic approach: solve "current + slope·t = limit" for t, so
        # t = (limit − current) / slope. Only reported when the crossing
        # happens within the next 60 minutes — anything further out is too
        # speculative to act on.
        limits = THRESHOLDS[parameter]
        time_to_threshold = None
        warning_message = None

        # Rising parameter → minutes until it reaches its upper limit
        if slope > 0.05 and 'max' in limits:
            steps_to_limit = (limits['max'] - current_value) / slope if slope != 0 else None
            if steps_to_limit is not None and 0 < steps_to_limit <= 60:
                time_to_threshold = round(steps_to_limit)
                warning_message = (
                    f'{parameter.replace("_", " ").title()} is rising and may reach the '
                    f'warning threshold ({limits["max"]}) in approximately '
                    f'{time_to_threshold} minutes.'
                )

        # Falling parameter → minutes until it reaches its lower limit
        elif slope < -0.05 and 'min' in limits:
            steps_to_limit = (current_value - limits['min']) / abs(slope) if slope != 0 else None
            if steps_to_limit is not None and 0 < steps_to_limit <= 60:
                time_to_threshold = round(steps_to_limit)
                warning_message = (
                    f'{parameter.replace("_", " ").title()} is falling and may reach the '
                    f'warning threshold ({limits["min"]}) in approximately '
                    f'{time_to_threshold} minutes.'
                )

        return {
            'parameter': parameter,
            'current_value': round(current_value, 2),
            'predicted_value': round(predicted_value, 2),
            'trend_direction': trend_direction,
            'slope_per_minute': round(slope, 4),
            'time_to_threshold_minutes': time_to_threshold,
            'warning_message': warning_message,
        }

    def predict_all(self, mission) -> list:
        """Run predictions for all monitored parameters.

        Returns a list of result dicts (one per parameter in
        MONITORED_PARAMS), each shaped like `predict()`'s return value.
        """
        return [self.predict(mission, p) for p in MONITORED_PARAMS]
