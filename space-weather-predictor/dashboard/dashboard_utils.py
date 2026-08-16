"""
dashboard_utils.py
==================
Utility functions shared across the dashboard.
"""

from pathlib import Path
import pandas as pd

RISK_COLORS: dict[str, str] = {
    "GO": "#27ae60",
    "CAUTION": "#f39c12",
    "DELAY": "#e67e22",
    "NO-GO": "#e74c3c",
}

LEVEL_COLORS: dict[str, str] = {
    "LOW": "#27ae60",
    "MODERATE": "#f39c12",
    "HIGH": "#e67e22",
    "EXTREME": "#e74c3c",
}

RECOMMENDATION_MAP: dict[str, str] = {
    "LOW": "GO",
    "MODERATE": "CAUTION",
    "HIGH": "DELAY",
    "EXTREME": "NO-GO",
}


def risk_level_from_score(score: float) -> str:
    """Return risk level string from a numeric score."""
    if score < 20:
        return "LOW"
    elif score < 40:
        return "MODERATE"
    elif score < 60:
        return "HIGH"
    else:
        return "EXTREME"


def get_recommendation(risk_level: str) -> str:
    return RECOMMENDATION_MAP.get(risk_level, "UNKNOWN")


def filter_date_range(
    df: pd.DataFrame,
    start_date: "pd.Timestamp | str",
    end_date: "pd.Timestamp | str",
) -> pd.DataFrame:
    """Return rows where date is in [start_date, end_date]."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start > end:
        raise ValueError(f"start_date ({start.date()}) must be before end_date ({end.date()}).")
    mask = (df["date"] >= start) & (df["date"] <= end)
    filtered = df[mask].copy()
    if len(filtered) == 0:
        raise ValueError(
            f"No data found between {start.date()} and {end.date()}. "
            "Try a different date range."
        )
    return filtered


def compute_date_range_summary(filtered_df: pd.DataFrame) -> dict:
    """Compute summary statistics for a filtered date range."""
    if len(filtered_df) == 0:
        raise ValueError("filtered_df is empty — cannot compute summary.")

    filtered_df = filtered_df.copy()
    if "risk_level" not in filtered_df.columns:
        filtered_df["risk_level"] = filtered_df["risk_score"].apply(risk_level_from_score)
    if "recommendation" not in filtered_df.columns:
        filtered_df["recommendation"] = filtered_df["risk_level"].apply(get_recommendation)

    rec_counts = filtered_df["recommendation"].value_counts().to_dict()
    top_row = filtered_df.loc[filtered_df["risk_score"].idxmax()]

    # Overall recommendation: use average score
    avg_score = filtered_df["risk_score"].mean()
    overall_level = risk_level_from_score(avg_score)
    overall_rec = get_recommendation(overall_level)

    return {
        "total_days": len(filtered_df),
        "avg_risk_score": round(avg_score, 2),
        "go_days": rec_counts.get("GO", 0),
        "caution_days": rec_counts.get("CAUTION", 0),
        "delay_days": rec_counts.get("DELAY", 0),
        "no_go_days": rec_counts.get("NO-GO", 0),
        "highest_risk_date": str(pd.Timestamp(top_row["date"]).date()),
        "highest_risk_score": round(float(top_row["risk_score"]), 2),
        "overall_recommendation": overall_rec,
        "overall_risk_level": overall_level,
    }
