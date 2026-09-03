"""
SpaceGuard AI — Risk Engine
Computes spacecraft health score (0-100) and risk level.
"""
from ai.anomaly_detector import THRESHOLDS

# Health score deductions per severity
SEVERITY_DEDUCTIONS = {
    'NORMAL':   0,
    'LOW':      5,
    'MODERATE': 15,
    'HIGH':     30,
    'CRITICAL': 50,
}

RISK_LEVELS = [
    (90, 'NORMAL',   'Excellent'),
    (75, 'LOW',      'Good'),
    (60, 'MODERATE', 'Moderate Risk'),
    (40, 'HIGH',     'High Risk'),
    (0,  'CRITICAL', 'Critical'),
]


class RiskEngine:
    """
    Computes overall spacecraft health score from anomaly results and raw telemetry.
    Each component is documented in score_breakdown for explainability.
    """

    def compute_health(self, telemetry_record, anomaly_result: dict, recent_records=None) -> dict:
        """
        Args:
            telemetry_record: Telemetry model instance
            anomaly_result: dict from AnomalyDetector.analyze()
            recent_records: optional queryset/list of last N telemetry records for trend analysis
        Returns:
            dict with health_score, risk_level, health_category, score_breakdown
        """
        score = 100
        breakdown = {}

        # 1. Deduct for anomaly severity
        severity_deduction = SEVERITY_DEDUCTIONS.get(anomaly_result.get('severity', 'NORMAL'), 0)
        score -= severity_deduction
        breakdown['anomaly_severity'] = -severity_deduction

        # 2. Deduct for out-of-threshold parameters (2 pts each; 10 pts if critical)
        threshold_deduction = 0
        for col, limits in THRESHOLDS.items():
            val = getattr(telemetry_record, col, None)
            if val is None:
                continue
            is_critical = (
                ('critical_max' in limits and val > limits['critical_max']) or
                ('critical_min' in limits and val < limits['critical_min'])
            )
            is_warning = val < limits['min'] or val > limits['max']
            if is_critical:
                threshold_deduction += 10
            elif is_warning:
                threshold_deduction += 2
        score -= threshold_deduction
        breakdown['threshold_violations'] = -threshold_deduction

        # 3. Deduct for worsening trend (up to -10 pts)
        trend_deduction = 0
        if recent_records and len(recent_records) >= 5:
            trend_deduction = self._compute_trend_deduction(recent_records)
        score -= trend_deduction
        breakdown['trend_penalty'] = -trend_deduction

        # Clamp score to 0-100
        score = max(0, min(100, score))

        risk_level, category = self._classify(score)

        return {
            'health_score': score,
            'risk_level': risk_level,
            'health_category': category,
            'score_breakdown': breakdown,
        }

    def _compute_trend_deduction(self, recent_records) -> int:
        """Assign up to 10 penalty points if critical parameters are trending TOWARD their danger limits."""
        import numpy as np
        penalty = 0
        # (param, dangerous direction): rising temp is bad, falling battery/signal is bad
        critical_params = [
            ('temperature',    'rising'),
            ('battery_voltage', 'falling'),
            ('signal_strength', 'falling'),
        ]
        for param, danger_dir in critical_params:
            values = [getattr(r, param) for r in recent_records if hasattr(r, param)]
            if len(values) < 3:
                continue
            x = np.arange(len(values))
            slope = float(np.polyfit(x, values, 1)[0])
            # Only penalise when trending in the dangerous direction with meaningful slope
            if danger_dir == 'rising' and slope > 0.05:
                penalty += 3
            elif danger_dir == 'falling' and slope < -0.05:
                penalty += 3
        return min(penalty, 10)

    def _classify(self, score: int) -> tuple:
        for threshold, risk, category in RISK_LEVELS:
            if score >= threshold:
                return risk, category
        return 'CRITICAL', 'Critical'
