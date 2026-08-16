"""
test_risk_scoring.py
====================
Unit tests for src/risk_scoring.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
from src.risk_scoring import (
    calculate_risk_score,
    score_to_risk_level,
    get_recommendation,
    apply_risk_scoring,
    RECOMMENDATION_MAP,
)


def _row(
    x: int = 0,
    m: int = 0,
    c: int = 0,
    kp: float = 0.0,
    avg_kp: float = 0.0,
    storms: int = 0,
    trend: float = 1.0,
) -> pd.Series:
    return pd.Series(
        {
            "xclass_flare_count": x,
            "mclass_flare_count": m,
            "cclass_flare_count": c,
            "max_kp_index": kp,
            "avg_kp_index": avg_kp,
            "storm_count": storms,
            "event_trend": trend,
        }
    )


class TestCalculateRiskScore:
    def test_zero_input_gives_zero(self):
        score = calculate_risk_score(_row())
        assert score == pytest.approx(0.0)

    def test_x_class_max_40(self):
        # 1 X-class → 40; 2 X-class still capped at 40
        assert calculate_risk_score(_row(x=1)) == pytest.approx(40.0)
        assert calculate_risk_score(_row(x=2)) == pytest.approx(40.0)

    def test_m_class_max_25(self):
        # 1 M-class → 25; 2 M-class still capped at 25
        assert calculate_risk_score(_row(m=1)) == pytest.approx(25.0)
        assert calculate_risk_score(_row(m=2)) == pytest.approx(25.0)

    def test_kp_score(self):
        # max_kp = 9 → (9/9) * 20 = 20
        score = calculate_risk_score(_row(kp=9.0))
        assert score == pytest.approx(20.0)
        # max_kp = 4.5 → (4.5/9) * 20 = 10
        score_half = calculate_risk_score(_row(kp=4.5))
        assert score_half == pytest.approx(10.0)

    def test_trend_score(self):
        # trend = 2.0 → (2-1)*15 = 15 (max)
        score = calculate_risk_score(_row(trend=2.0))
        assert score == pytest.approx(15.0)
        # trend = 1.5 → (1.5-1)*15 = 7.5
        score_half = calculate_risk_score(_row(trend=1.5))
        assert score_half == pytest.approx(7.5)
        # trend = 0.5 → clamped to 0
        score_low = calculate_risk_score(_row(trend=0.5))
        assert score_low == pytest.approx(0.0)

    def test_maximum_score_capped_at_100(self):
        # All components maxed out: 40 + 25 + 20 + 15 = 100
        score = calculate_risk_score(_row(x=2, m=2, kp=9.0, trend=2.0))
        assert score == pytest.approx(100.0)

    def test_score_always_in_range(self):
        for _ in range(100):
            import random
            score = calculate_risk_score(_row(
                x=random.randint(0, 5),
                m=random.randint(0, 5),
                kp=random.uniform(0, 9),
                trend=random.uniform(0, 3),
            ))
            assert 0.0 <= score <= 100.0


class TestScoreToRiskLevel:
    def test_low(self):
        assert score_to_risk_level(0.0) == "LOW"
        assert score_to_risk_level(19.9) == "LOW"

    def test_moderate(self):
        assert score_to_risk_level(20.0) == "MODERATE"
        assert score_to_risk_level(39.9) == "MODERATE"

    def test_high(self):
        assert score_to_risk_level(40.0) == "HIGH"
        assert score_to_risk_level(59.9) == "HIGH"

    def test_extreme(self):
        assert score_to_risk_level(60.0) == "EXTREME"
        assert score_to_risk_level(100.0) == "EXTREME"


class TestGetRecommendation:
    def test_low_gives_go(self):
        assert get_recommendation("LOW") == "GO"

    def test_moderate_gives_caution(self):
        assert get_recommendation("MODERATE") == "CAUTION"

    def test_high_gives_delay(self):
        assert get_recommendation("HIGH") == "DELAY"

    def test_extreme_gives_no_go(self):
        assert get_recommendation("EXTREME") == "NO-GO"


class TestApplyRiskScoring:
    def test_adds_required_columns(self):
        df = pd.DataFrame(
            [
                {
                    "date": "2024-01-01",
                    "xclass_flare_count": 0,
                    "mclass_flare_count": 0,
                    "cclass_flare_count": 0,
                    "max_kp_index": 0.0,
                    "avg_kp_index": 0.0,
                    "storm_count": 0,
                    "event_trend": 1.0,
                }
            ]
        )
        result = apply_risk_scoring(df)
        assert "risk_score" in result.columns
        assert "risk_level" in result.columns
        assert "recommendation" in result.columns

    def test_risk_score_range(self):
        rows = [
            {"date": f"2024-01-0{i}", "xclass_flare_count": i % 3,
             "mclass_flare_count": i % 2, "cclass_flare_count": i % 4,
             "max_kp_index": float(i), "avg_kp_index": float(i) / 2,
             "storm_count": i % 2, "event_trend": 1.0}
            for i in range(1, 6)
        ]
        df = pd.DataFrame(rows)
        result = apply_risk_scoring(df)
        assert (result["risk_score"] >= 0).all()
        assert (result["risk_score"] <= 100).all()
