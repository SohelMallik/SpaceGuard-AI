"""
SpaceGuard AI — Trend Predictor
Uses linear regression to extrapolate future parameter values and estimate
time-to-threshold crossings.
"""
import numpy as np
import logging
from ai.anomaly_detector import THRESHOLDS

logger = logging.getLogger(__name__)

# Parameters actively monitored for predictions
MONITORED_PARAMS = ['temperature', 'battery_voltage', 'signal_strength', 'fuel_level', 'radiation']


class TrendPredictor:
    """
    Predicts future values of key telemetry parameters using linear regression
    over the most recent records.
    """

    def predict(self, mission, parameter: str, horizon_minutes: int = 15) -> dict:
        """
        Predict the value of `parameter` `horizon_minutes` in the future.

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
        records.reverse()  # oldest first

        if len(records) < 5:
            return {
                'parameter': parameter,
                'trend_direction': 'INSUFFICIENT_DATA',
                'current_value': None,
                'predicted_value': None,
                'time_to_threshold_minutes': None,
                'warning_message': 'Insufficient telemetry data for trend prediction.',
            }

        values = np.array([getattr(r, parameter) for r in records], dtype=float)
        x = np.arange(len(values), dtype=float)

        # Linear regression: y = slope * x + intercept
        coeffs = np.polyfit(x, values, 1)
        slope = float(coeffs[0])
        intercept = float(coeffs[1])

        current_value = float(values[-1])
        # Each step ≈ avg telemetry interval (assume 1 step ≈ 1 minute for demo)
        predicted_value = float(slope * (len(values) - 1 + horizon_minutes) + intercept)

        # Determine trend direction
        if abs(slope) < 0.05:
            trend_direction = 'STABLE'
        elif slope > 0:
            trend_direction = 'RISING'
        else:
            trend_direction = 'FALLING'

        # Estimate time-to-threshold crossing
        limits = THRESHOLDS[parameter]
        time_to_threshold = None
        warning_message = None

        if slope > 0.05 and 'max' in limits:
            steps_to_limit = (limits['max'] - current_value) / slope if slope != 0 else None
            if steps_to_limit is not None and 0 < steps_to_limit <= 60:
                time_to_threshold = round(steps_to_limit)
                warning_message = (
                    f'{parameter.replace("_", " ").title()} is rising and may reach the '
                    f'warning threshold ({limits["max"]}) in approximately '
                    f'{time_to_threshold} minutes.'
                )

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
        """Run predictions for all monitored parameters."""
        return [self.predict(mission, p) for p in MONITORED_PARAMS]
