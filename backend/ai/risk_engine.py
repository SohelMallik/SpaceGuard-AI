"""
SpaceGuard AI — Risk Engine
Computes spacecraft health score (0-100) and risk level.

What this module does
---------------------
Uses a simple, fully explainable deduction system: every spacecraft starts at
a perfect score of 100, and points are subtracted for three things:
  1. the ML anomaly severity (up to −50 points, see SEVERITY_DEDUCTIONS),
  2. individual sensors outside their thresholds (−2 warning, −10 critical each),
  3. a trend penalty when critical parameters are moving toward their danger
     limits, measured with a linear regression over recent history (up to −10).
The remaining score is mapped to a risk level (NORMAL → CRITICAL) that the
UI and the alerting logic act on. Every deduction is recorded in
`score_breakdown` so operators can see exactly which factor cost how many
points.
"""
from ai.anomaly_detector import THRESHOLDS

# Health score deductions per severity — the worse the ML verdict, the more
# points come off the perfect 100
SEVERITY_DEDUCTIONS = {
    'NORMAL':   0,
    'LOW':      5,
    'MODERATE': 15,
    'HIGH':     30,
    'CRITICAL': 50,
}

# (minimum score, risk level, human-readable category) — checked from the top
# down, so the first threshold the score meets is the correct band
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

    The score is a pure deduction system (start at 100, subtract penalties),
    not a learned model — deliberately simple so operators can audit every
    point via the returned `score_breakdown` dict.
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

        # 2. Deduct for out-of-threshold parameters (2 pts each; 10 pts if critical).
        #    The elif below matters: a critical breach is never double-counted
        #    as a warning, so the worst violation per sensor is the one applied.
        threshold_deduction = 0
        for col, limits in THRESHOLDS.items():
            val = getattr(telemetry_record, col, None)
            if val is None:
                continue  # sensor absent from this record — no penalty
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
        #    Needs at least 5 recent records before a trend is meaningful
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
        """
        Assign up to 10 penalty points if critical parameters are trending TOWARD their danger limits.

        A straight line is fitted through the recent values of each critical
        parameter (numpy.polyfit, degree 1); its slope is the change per
        record. |slope| ≤ 0.05 is treated as noise. Each genuinely worsening
        parameter costs 3 points, capped at 10 in total.
        """
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
                continue  # too few points for a trustworthy slope
            # The record index acts as the time axis (oldest → newest)
            x = np.arange(len(values))
            # polyfit returns [slope, intercept] of the line y = slope·x + intercept
            slope = float(np.polyfit(x, values, 1)[0])
            # Only penalise when trending in the dangerous direction with meaningful slope
            if danger_dir == 'rising' and slope > 0.05:
                penalty += 3
            elif danger_dir == 'falling' and slope < -0.05:
                penalty += 3
        return min(penalty, 10)  # the trend can never cost more than 10 points

    def _classify(self, score: int) -> tuple:
        """Map a numeric score to (risk_level, category) using RISK_LEVELS."""
        # The table is ordered high → low, so the first threshold the score meets wins
        for threshold, risk, category in RISK_LEVELS:
            if score >= threshold:
                return risk, category
        return 'CRITICAL', 'Critical'
