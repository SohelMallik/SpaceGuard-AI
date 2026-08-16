"""
prediction.py
=============
Prediction layer for the Space Weather Launch Safety Predictor.

Loads saved model artifacts and exposes clean prediction functions.
The dashboard uses only this module — it never re-trains the model.

Usage:
    from src.prediction import load_model, load_saved_data, predict_risk, get_recommendation
"""

from pathlib import Path
import joblib
import pandas as pd
import numpy as np

MODELS_DIR: Path = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH: Path = MODELS_DIR / "launch_decision_model.pkl"
DATA_PATH: Path = MODELS_DIR / "space_weather_data.pkl"

FEATURE_COLS: list[str] = [
    "xclass_flare_count",
    "mclass_flare_count",
    "cclass_flare_count",
    "max_kp_index",
    "avg_kp_index",
    "storm_count",
    "event_trend",
]

RECOMMENDATION_MAP: dict[str, str] = {
    "LOW": "GO",
    "MODERATE": "CAUTION",
    "HIGH": "DELAY",
    "EXTREME": "NO-GO",
}


def load_model():
    """Load the trained Random Forest classifier from disk.

    Returns
    -------
    sklearn estimator

    Raises
    ------
    FileNotFoundError
        If ``models/launch_decision_model.pkl`` does not exist.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}\n"
            "Run the training pipeline first:\n"
            "    python run.py"
        )
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load model from {MODEL_PATH}. The file may be corrupted.\n"
            f"Error: {exc}"
        ) from exc
    return model


def load_saved_data() -> dict:
    """Load the saved risk data and metadata.

    Returns
    -------
    dict
        Keys: ``current_stats``, ``feature_cols``, ``recent_features``

    Raises
    ------
    FileNotFoundError
        If ``models/space_weather_data.pkl`` does not exist.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Data file not found: {DATA_PATH}\n"
            "Run the training pipeline first:\n"
            "    python run.py"
        )
    try:
        data = joblib.load(DATA_PATH)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load data from {DATA_PATH}. The file may be corrupted.\n"
            f"Error: {exc}"
        ) from exc

    # Validate expected keys
    for key in ("current_stats", "feature_cols", "recent_features"):
        if key not in data:
            raise ValueError(
                f"Saved data file is missing expected key '{key}'. "
                "Re-run the pipeline to regenerate."
            )
    return data


def predict_risk(features: dict, model=None) -> str:
    """Predict the risk level for a single set of features.

    Parameters
    ----------
    features:
        Dict with keys matching ``FEATURE_COLS``.
    model:
        Optional pre-loaded model. If None, loads from disk.

    Returns
    -------
    str
        Predicted risk level: ``"LOW"``, ``"MODERATE"``, ``"HIGH"``, or ``"EXTREME"``.
    """
    if model is None:
        model = load_model()

    # Validate that all required feature keys are present
    missing = [k for k in FEATURE_COLS if k not in features]
    if missing:
        raise ValueError(f"Missing feature keys: {missing}")

    X = np.array([[features[k] for k in FEATURE_COLS]], dtype=float)
    prediction = model.predict(X)[0]
    return str(prediction)


def get_recommendation(risk_level: str) -> str:
    """Map a risk level to a launch recommendation string."""
    return RECOMMENDATION_MAP.get(risk_level, "UNKNOWN")
