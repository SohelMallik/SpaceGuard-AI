"""
test_data_cleaning.py
=====================
Unit tests for src/data_cleaning.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
from src.data_cleaning import (
    clean_space_weather_data,
    _parse_flare_class,
    _fill_missing_values,
    _remove_duplicates,
    _convert_datetimes,
    _calculate_duration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_df(**overrides) -> pd.DataFrame:
    """Build a minimal valid space weather DataFrame for testing."""
    base = {
        "event_id": ["E001", "E002"],
        "event_type": ["Solar Flare", "Geomagnetic Storm"],
        "begin_time": ["2023-01-01 08:00", "2023-01-02 10:00"],
        "peak_time": ["2023-01-01 08:30", "2023-01-02 10:30"],
        "end_time": ["2023-01-01 09:00", "2023-01-02 11:00"],
        "class_type": ["X5.2", "G2"],
        "source_location": [None, "N25W30"],
        "active_region": [None, "AR12345"],
        "date": ["2023-01-01", "2023-01-02"],
        "year": [2023, 2023],
        "month": [1, 1],
        "day": [1, 2],
        "hour": [8, 10],
        "instruments": ["GOES-16", "GOES-16"],
        "note": [None, "moderate storm"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFillMissingValues:
    def test_kp_index_filled_with_zero(self):
        df = _minimal_df(kp_index=[None, 3.5])
        result = _fill_missing_values(df)
        assert result["kp_index"].iloc[0] == 0.0

    def test_class_type_filled(self):
        df = _minimal_df(class_type=[None, "G2"])
        result = _fill_missing_values(df)
        assert result["class_type"].iloc[0] == "Unknown"

    def test_note_filled_with_empty_string(self):
        df = _minimal_df()
        result = _fill_missing_values(df)
        assert result["note"].iloc[0] == ""

    def test_source_location_filled(self):
        df = _minimal_df()
        result = _fill_missing_values(df)
        assert result["source_location"].iloc[0] == "Unknown"

    def test_active_region_filled(self):
        df = _minimal_df()
        result = _fill_missing_values(df)
        assert result["active_region"].iloc[0] == "Unknown"


class TestRemoveDuplicates:
    def test_duplicates_removed(self):
        df = _minimal_df(
            event_id=["E001", "E001"],
            event_type=["Solar Flare", "Solar Flare"],
            begin_time=["2023-01-01 08:00", "2023-01-01 08:00"],
            end_time=["2023-01-01 09:00", "2023-01-01 09:00"],
        )
        result = _remove_duplicates(df)
        assert len(result) == 1

    def test_no_duplicates_unchanged(self):
        df = _minimal_df()
        result = _remove_duplicates(df)
        assert len(result) == 2


class TestDatetimeConversion:
    def test_begin_time_parsed(self):
        df = _minimal_df()
        result = _convert_datetimes(df)
        assert pd.api.types.is_datetime64_any_dtype(result["begin_time"])

    def test_invalid_datetime_becomes_nat(self):
        df = _minimal_df(begin_time=["not-a-date", "2023-01-02 10:00"])
        result = _convert_datetimes(df)
        assert pd.isna(result["begin_time"].iloc[0])


class TestDurationCalculation:
    def test_duration_in_minutes(self):
        df = _minimal_df()
        df = _convert_datetimes(df)
        result = _calculate_duration(df)
        # 08:00 → 09:00 = 60 minutes
        assert result["duration_minutes"].iloc[0] == pytest.approx(60.0)

    def test_missing_duration_becomes_zero(self):
        df = _minimal_df(end_time=[None, "2023-01-02 11:00"])
        df = _convert_datetimes(df)
        result = _calculate_duration(df)
        assert result["duration_minutes"].iloc[0] == 0.0


class TestFlareClassParsing:
    def test_x_class(self):
        fc, fm = _parse_flare_class("X5.2")
        assert fc == "X"
        assert fm == pytest.approx(5.2)

    def test_m_class(self):
        fc, fm = _parse_flare_class("M2.1")
        assert fc == "M"
        assert fm == pytest.approx(2.1)

    def test_c_class(self):
        fc, fm = _parse_flare_class("C3.4")
        assert fc == "C"
        assert fm == pytest.approx(3.4)

    def test_unknown_returns_na(self):
        fc, fm = _parse_flare_class("Unknown")
        assert fc == "N/A"
        assert fm == 0.0

    def test_non_flare_event_gets_na(self):
        df = _minimal_df()
        result = clean_space_weather_data(df)
        # Row 1 is Geomagnetic Storm — should be N/A
        assert result.loc[result["event_type"] == "Geomagnetic Storm", "flare_class"].iloc[0] == "N/A"

    def test_solar_flare_gets_class(self):
        df = _minimal_df()
        result = clean_space_weather_data(df)
        row = result.loc[result["event_type"] == "Solar Flare"].iloc[0]
        assert row["flare_class"] == "X"
        assert row["flare_magnitude"] == pytest.approx(5.2)
