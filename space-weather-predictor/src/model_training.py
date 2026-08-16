"""
model_training.py
=================
Trains a Random Forest classifier on the historical risk features.

Design decisions
----------------
* A TIME-BASED split is used: training on dates before 2025-01-01,
  testing on 2025-01-01 and later.  The data is NEVER shuffled before
  splitting to respect the temporal ordering of space-weather events
  and prevent look-ahead bias.
* Cross-validation is intentionally omitted for this required baseline
  implementation.
* random_state=42 ensures reproducibility across runs.

Usage:
    from src.model_training import train_model
    model, X_train, X_test, y_train, y_test, y_pred = train_model(scored_df)
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FEATURE_COLS: list[str] = [
    "xclass_flare_count",
    "mclass_flare_count",
    "cclass_flare_count",
    "max_kp_index",
    "avg_kp_index",
    "storm_count",
    "event_trend",
]
TARGET_COL: str = "risk_level"
TRAIN_CUTOFF: str = "2025-01-01"

RF_PARAMS: dict = {
    "n_estimators": 100,
    "max_depth": 10,
    "random_state": 42,
    "n_jobs": -1,
}


def train_model(
    scored_df: pd.DataFrame,
) -> tuple:
    """Train a Random Forest classifier using a time-based train/test split.

    Parameters
    ----------
    scored_df:
        DataFrame produced by :func:`src.risk_scoring.apply_risk_scoring`.
        Must contain ``date``, all columns in ``FEATURE_COLS``, and ``risk_level``.

    Returns
    -------
    tuple
        ``(model, X_train, X_test, y_train, y_test, y_pred)``
        where *model* is the fitted :class:`RandomForestClassifier`.
    """
    print("\n=== Model Training ===")

    # Validate required columns
    missing = [c for c in FEATURE_COLS + [TARGET_COL, "date"] if c not in scored_df.columns]
    if missing:
        raise ValueError(f"scored_df is missing required columns: {missing}")

    # Ensure date column is datetime
    scored_df = scored_df.copy()
    scored_df["date"] = pd.to_datetime(scored_df["date"])

    cutoff = pd.Timestamp(TRAIN_CUTOFF)
    train_df = scored_df[scored_df["date"] < cutoff].copy()
    test_df = scored_df[scored_df["date"] >= cutoff].copy()

    print(f"  Train/test cutoff : {TRAIN_CUTOFF}")
    print(f"  Training samples  : {len(train_df)}")
    print(f"  Testing samples   : {len(test_df)}")

    if len(train_df) == 0:
        raise ValueError(
            f"Training set is empty. All dates are on or after {TRAIN_CUTOFF}. "
            "Check that your dataset contains historical data before this cutoff."
        )

    if len(test_df) == 0:
        print(
            f"  WARNING: Test set is empty — no dates on or after {TRAIN_CUTOFF}. "
            "Evaluation will be skipped."
        )

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df[TARGET_COL].values
    X_test = test_df[FEATURE_COLS].values if len(test_df) > 0 else X_train[:0]
    y_test = test_df[TARGET_COL].values if len(test_df) > 0 else y_train[:0]

    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train, y_train)
    print(f"  Model trained: RandomForestClassifier(n_estimators={RF_PARAMS['n_estimators']}, "
          f"max_depth={RF_PARAMS['max_depth']})")

    y_pred = model.predict(X_test) if len(X_test) > 0 else []

    return model, X_train, X_test, y_train, y_test, y_pred
