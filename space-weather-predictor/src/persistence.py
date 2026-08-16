"""
persistence.py
==============
Saves and loads trained model artifacts.

Usage (called automatically by run.py / model_training pipeline):
    from src.persistence import save_artifacts
    save_artifacts(model, scored_df, feature_cols)
"""

from pathlib import Path
import joblib
import pandas as pd

MODELS_DIR: Path = Path(__file__).resolve().parent.parent / "models"


def save_artifacts(model, scored_df: pd.DataFrame, feature_cols: list[str]) -> None:
    """Save the trained model and risk data to disk.

    Files created
    -------------
    * ``models/launch_decision_model.pkl`` — fitted RandomForestClassifier
    * ``models/space_weather_data.pkl``    — dict with current_stats, feature_cols,
                                             and last 30 risk feature records.

    Parameters
    ----------
    model:
        Fitted :class:`~sklearn.ensemble.RandomForestClassifier`.
    scored_df:
        DataFrame with risk features + risk_score, risk_level, recommendation.
    feature_cols:
        List of feature column names.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # 1. Save model
    # -----------------------------------------------------------------------
    model_path = MODELS_DIR / "launch_decision_model.pkl"
    joblib.dump(model, model_path)
    print(f"\n  Model saved → {model_path}")

    # -----------------------------------------------------------------------
    # 2. Build current_stats from the latest row in scored_df
    # -----------------------------------------------------------------------
    scored_df = scored_df.copy()
    scored_df["date"] = pd.to_datetime(scored_df["date"])
    latest = scored_df.loc[scored_df["date"].idxmax()]

    from src.risk_scoring import RECOMMENDATION_MAP
    risk_level = str(latest.get("risk_level", "UNKNOWN"))

    current_stats = {
        "latest_date": str(latest["date"].date()),
        "latest_risk_score": float(latest.get("risk_score", 0.0)),
        "latest_risk_level": risk_level,
        "xclass_48h": int(latest.get("xclass_flare_count", 0)),
        "mclass_48h": int(latest.get("mclass_flare_count", 0)),
        "max_kp_48h": float(latest.get("max_kp_index", 0.0)),
        "recommendation": RECOMMENDATION_MAP.get(risk_level, "UNKNOWN"),
    }

    # Last 30 records
    recent_features = scored_df.tail(30).reset_index(drop=True)

    data_payload = {
        "current_stats": current_stats,
        "feature_cols": feature_cols,
        "recent_features": recent_features,
    }

    data_path = MODELS_DIR / "space_weather_data.pkl"
    joblib.dump(data_payload, data_path)
    print(f"  Data saved  → {data_path}")
    print(f"\n  Current status: {current_stats['latest_date']} | "
          f"Score={current_stats['latest_risk_score']:.1f} | "
          f"Level={current_stats['latest_risk_level']} | "
          f"Rec={current_stats['recommendation']}")
