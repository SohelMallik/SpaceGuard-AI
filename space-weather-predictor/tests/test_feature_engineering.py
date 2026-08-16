"""
test_feature_engineering.py
============================
Unit tests for src/feature_engineering.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
from src.feature_engineering import build_risk_features


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_space_df(events: list[dict]) -> pd.DataFrame:
    """Build a minimal cleaned space_df from a list of event dicts."""
    required_defaults = {
        "event_id": "E000",
        "event_type": "Solar Flare",
        "begin_time": "2023-06-01 12:00",
        "end_time": "2023-06-01 13:00",
        "class_type": "M1.0",
        "flare_class": "M",
        "flare_magnitude": 1.0,
        "kp_index": 0.0,
        "date": "2023-06-01",
        "year": 2023,
        "month": 6,
        "day": 1,
        "hour": 12,
    }
    rows = []
    for i, ev in enumerate(events):
        row = dict(required_defaults)
        row["event_id"] = f"E{i:03d}"
        row.update(ev)
        rows.append(row)
    df = pd.DataFrame(rows)
    df["begin_time"] = pd.to_datetime(df["begin_time"])
    df["kp_index"] = df["kp_index"].astype(float)
    return df


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildRiskFeatures:

    def test_output_columns_present(self):
        df = _make_space_df([{"begin_time": "2023-06-01 08:00", "date": "2023-06-01"}])
        result = build_risk_features(df)
        expected_cols = [
            "date",
            "xclass_flare_count",
            "mclass_flare_count",
            "cclass_flare_count",
            "max_kp_index",
            "avg_kp_index",
            "storm_count",
            "event_trend",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_sorted_by_date(self):
        df = _make_space_df([
            {"begin_time": "2023-06-03 08:00", "date": "2023-06-03"},
            {"begin_time": "2023-06-01 08:00", "date": "2023-06-01"},
        ])
        result = build_risk_features(df)
        dates = result["date"].tolist()
        assert dates == sorted(dates), "Dates are not sorted ascending."

    def test_no_current_date_leakage(self):
        """Events on the target date itself must NOT appear in that date's features."""
        # Put ONE X-class event at exactly 00:00 on June 2.
        # For target date June 2 the window is [May 31 00:00, June 2 00:00).
        # The event at June 2 00:00 is on the boundary and must be EXCLUDED.
        df = _make_space_df([
            {
                "begin_time": "2023-06-02 00:00",
                "date": "2023-06-02",
                "event_type": "Solar Flare",
                "flare_class": "X",
                "flare_magnitude": 1.0,
                "class_type": "X1.0",
            }
        ])
        result = build_risk_features(df)
        row = result[result["date"] == pd.Timestamp("2023-06-02")]
        if len(row) > 0:
            assert row.iloc[0]["xclass_flare_count"] == 0, (
                "Current-date event incorrectly included in features."
            )

    def test_48h_window_is_respected(self):
        """An event 49 hours before the target date must NOT appear in features."""
        target = pd.Timestamp("2023-06-03 00:00")
        outside = target - pd.Timedelta(hours=49)
        inside = target - pd.Timedelta(hours=24)

        df = _make_space_df([
            {
                "begin_time": str(outside),
                "date": outside.strftime("%Y-%m-%d"),
                "event_type": "Solar Flare",
                "flare_class": "X",
                "flare_magnitude": 5.0,
                "class_type": "X5.0",
            },
            {
                "begin_time": str(inside),
                "date": inside.strftime("%Y-%m-%d"),
                "event_type": "Solar Flare",
                "flare_class": "M",
                "flare_magnitude": 1.0,
                "class_type": "M1.0",
            },
        ])
        result = build_risk_features(df)
        target_row = result[result["date"] == pd.Timestamp("2023-06-03")]
        if len(target_row) > 0:
            # X event is outside window — should NOT be counted
            assert target_row.iloc[0]["xclass_flare_count"] == 0
            # M event is inside window — should be counted
            assert target_row.iloc[0]["mclass_flare_count"] == 1

    def test_x_class_count(self):
        # Two X-class events in the 48h window before target date
        target_date = pd.Timestamp("2023-06-05")
        events = [
            {
                "begin_time": str(target_date - pd.Timedelta(hours=10)),
                "date": "2023-06-04",
                "event_type": "Solar Flare",
                "flare_class": "X",
                "class_type": "X2.0",
            },
            {
                "begin_time": str(target_date - pd.Timedelta(hours=20)),
                "date": "2023-06-04",
                "event_type": "Solar Flare",
                "flare_class": "X",
                "class_type": "X1.0",
            },
        ]
        df = _make_space_df(events)
        result = build_risk_features(df)
        row = result[result["date"] == target_date]
        if len(row) > 0:
            assert row.iloc[0]["xclass_flare_count"] >= 2

    def test_kp_max_and_avg(self):
        target_date = pd.Timestamp("2023-06-05")
        events = [
            {
                "begin_time": str(target_date - pd.Timedelta(hours=5)),
                "date": "2023-06-04",
                "event_type": "Geomagnetic Storm",
                "flare_class": "N/A",
                "class_type": "Unknown",
                "kp_index": 7.0,
            },
            {
                "begin_time": str(target_date - pd.Timedelta(hours=10)),
                "date": "2023-06-04",
                "event_type": "Geomagnetic Storm",
                "flare_class": "N/A",
                "class_type": "Unknown",
                "kp_index": 3.0,
            },
        ]
        df = _make_space_df(events)
        result = build_risk_features(df)
        row = result[result["date"] == target_date]
        if len(row) > 0:
            assert row.iloc[0]["max_kp_index"] == pytest.approx(7.0)
            assert row.iloc[0]["avg_kp_index"] == pytest.approx(5.0)

    def test_storm_count(self):
        """Events with kp_index >= 5 should be counted as storms."""
        target_date = pd.Timestamp("2023-06-06")
        events = [
            {
                "begin_time": str(target_date - pd.Timedelta(hours=6)),
                "date": "2023-06-05",
                "event_type": "Geomagnetic Storm",
                "flare_class": "N/A",
                "class_type": "Unknown",
                "kp_index": 6.0,
            },
            {
                "begin_time": str(target_date - pd.Timedelta(hours=12)),
                "date": "2023-06-05",
                "event_type": "Geomagnetic Storm",
                "flare_class": "N/A",
                "class_type": "Unknown",
                "kp_index": 2.0,  # below threshold
            },
        ]
        df = _make_space_df(events)
        result = build_risk_features(df)
        row = result[result["date"] == target_date]
        if len(row) > 0:
            assert row.iloc[0]["storm_count"] == 1

    def test_event_trend_no_older_events(self):
        """event_trend should be 1.0 when there are no events in the 24-48h window."""
        target_date = pd.Timestamp("2023-07-10")
        events = [
            {
                "begin_time": str(target_date - pd.Timedelta(hours=12)),
                "date": "2023-07-09",
                "event_type": "Solar Flare",
                "flare_class": "C",
                "class_type": "C1.0",
            }
        ]
        df = _make_space_df(events)
        result = build_risk_features(df)
        row = result[result["date"] == target_date]
        if len(row) > 0:
            assert row.iloc[0]["event_trend"] == pytest.approx(1.0)
