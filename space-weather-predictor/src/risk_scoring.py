"""
risk_scoring.py
===============
Educational deterministic risk engine for the Space Weather Launch Safety Predictor.

The weighting scheme is an EDUCATIONAL SIMPLIFICATION and is NOT an operational
NASA launch-safety or space-weather forecasting model.

Usage:
    from src.risk_scoring import calculate_risk_score, apply_risk_scoring
    risk_df = apply_risk_scoring(risk_features_df)
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Risk score weights (educational simplified model)
# ---------------------------------------------------------------------------
WEIGHT_X_CLASS: float = 40.0   # max contribution from X-class flares
WEIGHT_M_CLASS: float = 25.0   # max contribution from M-class flares
WEIGHT_KP: float = 20.0        # max contribution from Kp index
WEIGHT_TREND: float = 15.0     # max contribution from event trend
MAX_SCORE: float = 100.0
MAX_KP: float = 9.0            # planetary Kp scale top

# Risk level thresholds
LEVEL_LOW = 20.0
LEVEL_MODERATE = 40.0
LEVEL_HIGH = 60.0
# >= HIGH → EXTREME

# Recommendation mapping
RECOMMENDATION_MAP: dict[str, str] = {
    "LOW": "GO",
    "MODERATE": "CAUTION",
    "HIGH": "DELAY",
    "EXTREME": "NO-GO",
}


def calculate_risk_score(row: pd.Series) -> float:
    """Calculate a 0–100 educational launch risk score for a single feature row.

    Formula
    -------
    ::

        x_score     = min(xclass_flare_count × 40, 40)
        m_score     = min(mclass_flare_count × 25, 25)
        kp_score    = (max_kp_index / 9) × 20
        trend_score = min(max((event_trend - 1) × 15, 0), 15)
        total       = x_score + m_score + kp_score + trend_score
        final       = min(total, 100)

    Parameters
    ----------
    row:
        A single row from ``risk_features_df``.

    Returns
    -------
    float
        Risk score in the range [0, 100].
    """
    x_score = min(float(row["xclass_flare_count"]) * 40.0, 40.0)
    m_score = min(float(row["mclass_flare_count"]) * 25.0, 25.0)
    kp_score = (float(row["max_kp_index"]) / MAX_KP) * WEIGHT_KP
    trend_score = min(max((float(row["event_trend"]) - 1.0) * 15.0, 0.0), 15.0)

    total = x_score + m_score + kp_score + trend_score
    return float(min(total, MAX_SCORE))


def score_to_risk_level(score: float) -> str:
    """Convert a numeric risk score to a risk level label.

    Boundaries
    ----------
    [0,  20)  → LOW
    [20, 40)  → MODERATE
    [40, 60)  → HIGH
    [60, 100] → EXTREME
    """
    if score < LEVEL_LOW:
        return "LOW"
    elif score < LEVEL_MODERATE:
        return "MODERATE"
    elif score < LEVEL_HIGH:
        return "HIGH"
    else:
        return "EXTREME"


def get_recommendation(risk_level: str) -> str:
    """Map a risk level label to a launch recommendation."""
    return RECOMMENDATION_MAP.get(risk_level, "UNKNOWN")


def apply_risk_scoring(risk_features_df: pd.DataFrame) -> pd.DataFrame:
    """Add risk_score, risk_level, and recommendation columns to risk_features_df.

    Parameters
    ----------
    risk_features_df:
        Output from :func:`src.feature_engineering.build_risk_features`.

    Returns
    -------
    pd.DataFrame
        Copy of the input with three additional columns:
        ``risk_score``, ``risk_level``, ``recommendation``.
    """
    df = risk_features_df.copy()
    df["risk_score"] = df.apply(calculate_risk_score, axis=1)
    df["risk_level"] = df["risk_score"].apply(score_to_risk_level)
    df["recommendation"] = df["risk_level"].apply(get_recommendation)

    # -----------------------------------------------------------------------
    # Summary statistics
    # -----------------------------------------------------------------------
    print("\n=== Risk Scoring ===")

    level_counts = df["risk_level"].value_counts()
    print("\n  Risk Level Distribution:")
    for level in ["LOW", "MODERATE", "HIGH", "EXTREME"]:
        n = level_counts.get(level, 0)
        pct = n / len(df) * 100 if len(df) > 0 else 0.0
        rec = RECOMMENDATION_MAP.get(level, "?")
        print(f"    {level:<10} ({rec:<8}): {n:>5}  ({pct:.1f}%)")

    scores = df["risk_score"]
    print(f"\n  Risk Score Statistics:")
    print(f"    Mean   : {scores.mean():.2f}")
    print(f"    Median : {scores.median():.2f}")
    print(f"    Min    : {scores.min():.2f}")
    print(f"    Max    : {scores.max():.2f}")

    print("\n  Top 5 Highest-Risk Dates:")
    top5 = df.nlargest(5, "risk_score")[["date", "risk_score", "risk_level"]]
    print(top5.to_string(index=False))

    return df
