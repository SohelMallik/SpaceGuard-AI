"""
feature_engineering.py
=======================
Builds historical 48-hour launch-risk features from the cleaned space_df.

Design: Each row in the output represents a single calendar date.
Features are computed using ONLY events from the previous 48 hours
(i.e. [date - 48h, date) — the current date itself is excluded).
This prevents any future-data leakage.

Usage:
    from src.feature_engineering import build_risk_features
    risk_features_df = build_risk_features(space_df)
"""

import pandas as pd
import numpy as np


def build_risk_features(space_df: pd.DataFrame) -> pd.DataFrame:
    """Build historical 48-hour risk features for every unique date.

    Data leakage protection
    -----------------------
    For each target date D, only events satisfying::

        D - 48h  <=  begin_time  <  D

    are included in feature calculations.
    The date D itself is never included.

    Parameters
    ----------
    space_df:
        Cleaned DataFrame returned by :func:`src.data_cleaning.clean_space_weather_data`.

    Returns
    -------
    pd.DataFrame
        ``risk_features_df`` with columns:
        date, xclass_flare_count, mclass_flare_count, cclass_flare_count,
        max_kp_index, avg_kp_index, storm_count, event_trend.
        Sorted ascending by date.
    """
    print("\n=== Feature Engineering ===")

    # Ensure begin_time is datetime
    if not pd.api.types.is_datetime64_any_dtype(space_df["begin_time"]):
        space_df = space_df.copy()
        space_df["begin_time"] = pd.to_datetime(space_df["begin_time"], errors="coerce")

    # Ensure kp_index exists (default 0.0 if absent)
    if "kp_index" not in space_df.columns:
        space_df = space_df.copy()
        space_df["kp_index"] = 0.0

    # Work with timezone-naive timestamps
    space_df = space_df.copy()
    space_df["begin_time"] = space_df["begin_time"].dt.tz_localize(None)

    # Derive a normalized date column for grouping
    space_df["_event_date"] = space_df["begin_time"].dt.normalize()

    # Determine the full set of dates we will produce features for
    all_dates = sorted(space_df["_event_date"].dropna().unique())

    if len(all_dates) == 0:
        raise ValueError(
            "No valid dates found in space_df. "
            "Ensure begin_time was correctly parsed by clean_space_weather_data()."
        )

    rows: list[dict] = []

    for current_date in all_dates:
        current_dt = pd.Timestamp(current_date)
        window_start = current_dt - pd.Timedelta(hours=48)
        window_end = current_dt  # exclusive — current date NOT included

        mask = (
            (space_df["begin_time"] >= window_start)
            & (space_df["begin_time"] < window_end)
        )
        window_df = space_df[mask]

        # X / M / C class flare counts
        solar_mask = window_df["event_type"] == "Solar Flare"
        solar_df = window_df[solar_mask]

        xclass_count = int(
            (solar_df["flare_class"] == "X").sum()
            if "flare_class" in solar_df.columns
            else 0
        )
        mclass_count = int(
            (solar_df["flare_class"] == "M").sum()
            if "flare_class" in solar_df.columns
            else 0
        )
        cclass_count = int(
            (solar_df["flare_class"] == "C").sum()
            if "flare_class" in solar_df.columns
            else 0
        )

        # Kp features
        kp_values = window_df["kp_index"].dropna()
        max_kp = float(kp_values.max()) if len(kp_values) > 0 else 0.0
        avg_kp = float(kp_values.mean()) if len(kp_values) > 0 else 0.0

        # Storm count (Kp >= 5)
        storm_count = int((kp_values >= 5).sum())

        # Event trend: events in latest 24h vs events in prior 24-48h
        mid_point = current_dt - pd.Timedelta(hours=24)
        recent_mask = (space_df["begin_time"] >= mid_point) & (space_df["begin_time"] < window_end)
        older_mask = (space_df["begin_time"] >= window_start) & (space_df["begin_time"] < mid_point)

        recent_count = int(recent_mask.sum())
        older_count = int(older_mask.sum())

        if older_count == 0:
            event_trend = 1.0
        else:
            event_trend = recent_count / older_count

        rows.append(
            {
                "date": current_dt.normalize(),
                "xclass_flare_count": xclass_count,
                "mclass_flare_count": mclass_count,
                "cclass_flare_count": cclass_count,
                "max_kp_index": max_kp,
                "avg_kp_index": avg_kp,
                "storm_count": storm_count,
                "event_trend": event_trend,
            }
        )

    risk_features_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    print(f"  Total dates with features : {len(risk_features_df)}")
    print(f"  Date range : {risk_features_df['date'].min()} → {risk_features_df['date'].max()}")
    print(f"  X-class events in window  : {risk_features_df['xclass_flare_count'].sum()}")
    print(f"  M-class events in window  : {risk_features_df['mclass_flare_count'].sum()}")
    print(f"  Max Kp observed           : {risk_features_df['max_kp_index'].max():.1f}")

    return risk_features_df
