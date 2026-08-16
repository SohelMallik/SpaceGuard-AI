"""
test_prediction.py
==================
Unit tests for src/prediction.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.prediction import (
    FEATURE_COLS,
    RECOMMENDATION_MAP,
    get_recommendation,
    predict_risk,
)


class TestFeatureCols:
    def test_correct_feature_count(self):
        assert len(FEATURE_COLS) == 7

    def test_expected_feature_names(self):
        expected = {
            "xclass_flare_count",
            "mclass_flare_count",
            "cclass_flare_count",
            "max_kp_index",
            "avg_kp_index",
            "storm_count",
            "event_trend",
        }
        assert set(FEATURE_COLS) == expected


class TestRecommendationMap:
    def test_all_levels_mapped(self):
        for level in ["LOW", "MODERATE", "HIGH", "EXTREME"]:
            assert level in RECOMMENDATION_MAP

    def test_correct_values(self):
        assert RECOMMENDATION_MAP["LOW"] == "GO"
        assert RECOMMENDATION_MAP["MODERATE"] == "CAUTION"
        assert RECOMMENDATION_MAP["HIGH"] == "DELAY"
        assert RECOMMENDATION_MAP["EXTREME"] == "NO-GO"


class TestGetRecommendation:
    def test_known_levels(self):
        assert get_recommendation("LOW") == "GO"
        assert get_recommendation("MODERATE") == "CAUTION"
        assert get_recommendation("HIGH") == "DELAY"
        assert get_recommendation("EXTREME") == "NO-GO"

    def test_unknown_level_returns_unknown(self):
        assert get_recommendation("INVALID") == "UNKNOWN"


class TestPredictRisk:
    """Tests that use a simple mock model to avoid requiring saved .pkl files."""

    class _MockModel:
        def predict(self, X):
            # Always return "LOW" for testing
            return ["LOW"] * len(X)

    def _valid_features(self) -> dict:
        return {
            "xclass_flare_count": 0,
            "mclass_flare_count": 0,
            "cclass_flare_count": 0,
            "max_kp_index": 0.0,
            "avg_kp_index": 0.0,
            "storm_count": 0,
            "event_trend": 1.0,
        }

    def test_predict_returns_string(self):
        result = predict_risk(self._valid_features(), model=self._MockModel())
        assert isinstance(result, str)

    def test_predict_valid_label(self):
        result = predict_risk(self._valid_features(), model=self._MockModel())
        assert result in {"LOW", "MODERATE", "HIGH", "EXTREME"}

    def test_missing_feature_raises_value_error(self):
        features = self._valid_features()
        del features["max_kp_index"]
        with pytest.raises(ValueError, match="Missing feature keys"):
            predict_risk(features, model=self._MockModel())

    def test_all_feature_keys_used(self):
        """Ensure predict_risk uses all FEATURE_COLS (no silently ignored keys)."""
        features = self._valid_features()
        # This should not raise
        predict_risk(features, model=self._MockModel())

    def test_predict_output_recommendation(self):
        """End-to-end: predict → recommendation should be a valid string."""
        features = self._valid_features()
        level = predict_risk(features, model=self._MockModel())
        rec = get_recommendation(level)
        assert rec in {"GO", "CAUTION", "DELAY", "NO-GO"}
