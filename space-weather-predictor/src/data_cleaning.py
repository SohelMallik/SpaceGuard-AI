"""
data_cleaning.py
================
Cleans and transforms the raw space weather DataFrame.

Usage:
    from src.data_cleaning import clean_space_weather_data
    space_df = clean_space_weather_data(df)
"""

import re
import pandas as pd


def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values according to domain rules."""
    df = df.copy()

    # Numeric fill
    if "kp_index" in df.columns:
        df["kp_index"] = df["kp_index"].fillna(0.0)

    # Categorical fill
    for col, fill in [
        ("class_type", "Unknown"),
        ("source_location", "Unknown"),
        ("active_region", "Unknown"),
        ("note", ""),
    ]:
        if col in df.columns:
            df[col] = df[col].fillna(fill)

    # Columns with intentionally preserved missing values:
    # observed_time, source — do NOT fill.

    return df


def _remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows keyed on event_id, keeping the first occurrence."""
    initial_rows = len(df)
    df = df.drop_duplicates(subset=["event_id"], keep="first")
    removed = initial_rows - len(df)
    print(f"  Duplicates removed: {removed}")
    return df


def _convert_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamp columns to datetime using errors='coerce'."""
    for col in ["begin_time", "peak_time", "end_time", "observed_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _extract_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Derive year, month, hour from begin_time (overwrite if already present)."""
    if "begin_time" in df.columns:
        df["year"] = df["begin_time"].dt.year
        df["month"] = df["begin_time"].dt.month
        df["hour"] = df["begin_time"].dt.hour
    return df


def _calculate_duration(df: pd.DataFrame) -> pd.DataFrame:
    """Compute event duration in minutes from end_time - begin_time."""
    if "begin_time" in df.columns and "end_time" in df.columns:
        duration_td = df["end_time"] - df["begin_time"]
        df["duration_minutes"] = duration_td.dt.total_seconds().div(60).fillna(0.0)
        df["duration_minutes"] = df["duration_minutes"].clip(lower=0.0)
    return df


def _parse_flare_class(class_type_val: str) -> tuple[str, float]:
    """Extract flare class letter and numeric magnitude from a class_type string.

    Examples
    --------
    "X5.2"  → ("X",  5.2)
    "M2.1"  → ("M",  2.1)
    "C3.4"  → ("C",  3.4)
    "Unknown" → ("N/A", 0.0)
    """
    if not isinstance(class_type_val, str) or class_type_val in ("Unknown", "", "N/A"):
        return "N/A", 0.0

    match = re.match(r"^([A-Za-z])(\d+\.?\d*)$", class_type_val.strip())
    if match:
        letter = match.group(1).upper()
        try:
            magnitude = float(match.group(2))
        except ValueError:
            magnitude = 0.0
        return letter, magnitude

    # Single-letter class with no number (e.g. "X")
    if re.match(r"^[A-Za-z]$", class_type_val.strip()):
        return class_type_val.strip().upper(), 0.0

    return "N/A", 0.0


def _add_flare_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add flare_class and flare_magnitude columns.

    For Solar Flare events: parsed from class_type.
    For all other events:  flare_class="N/A", flare_magnitude=0.0.
    """
    flare_class_list: list[str] = []
    flare_mag_list: list[float] = []

    for _, row in df.iterrows():
        if row.get("event_type") == "Solar Flare":
            fc, fm = _parse_flare_class(str(row.get("class_type", "")))
        else:
            fc, fm = "N/A", 0.0
        flare_class_list.append(fc)
        flare_mag_list.append(fm)

    df["flare_class"] = flare_class_list
    df["flare_magnitude"] = flare_mag_list
    return df


def clean_space_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the raw space weather DataFrame.

    Steps performed
    ---------------
    1. Fill missing values by column-specific rules.
    2. Remove duplicate event_id rows.
    3. Convert timestamp columns to datetime.
    4. Re-derive year, month, hour from begin_time.
    5. Compute duration_minutes.
    6. Parse flare_class and flare_magnitude for Solar Flare events.

    Parameters
    ----------
    df:
        Raw DataFrame loaded by :func:`src.data_loader.load_dataset`.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame named ``space_df`` by convention.
    """
    print("\n=== Data Cleaning ===")
    initial_rows = len(df)
    print(f"  Initial rows : {initial_rows}")

    df = _fill_missing_values(df)
    df = _remove_duplicates(df)
    df = _convert_datetimes(df)
    df = _extract_time_columns(df)
    df = _calculate_duration(df)
    df = _add_flare_columns(df)

    final_rows = len(df)
    print(f"  Final rows   : {final_rows}")

    # Reset index after potential duplicate drops
    df = df.reset_index(drop=True)

    # Rename to space_df by convention — the variable name matters in notebooks.
    space_df = df
    return space_df
