"""
model_evaluation.py
===================
Evaluates the trained Random Forest classifier and saves a text report.

Usage:
    from src.model_evaluation import evaluate_model
    evaluate_model(model, X_test, y_test, y_pred, feature_cols)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, classification_report

REPORTS_DIR: Path = Path(__file__).resolve().parent.parent / "outputs" / "reports"


def evaluate_model(
    model,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    y_pred,
    feature_cols: list[str],
) -> dict:
    """Evaluate model performance and save a text report.

    Parameters
    ----------
    model:
        Fitted :class:`~sklearn.ensemble.RandomForestClassifier`.
    X_train, X_test, y_train, y_test:
        Training and test arrays.
    y_pred:
        Predictions on X_test from :func:`src.model_training.train_model`.
    feature_cols:
        List of feature column names (same order as X_train columns).

    Returns
    -------
    dict
        ``{"accuracy": float, "report": str, "feature_importances": pd.Series}``
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== Model Evaluation ===")
    print(f"  Training shape : {X_train.shape}")
    print(f"  Testing shape  : {X_test.shape}")

    if len(y_test) == 0 or len(y_pred) == 0:
        print("  WARNING: Test set is empty — skipping accuracy calculation.")
        results = {
            "accuracy": None,
            "report": "Test set empty — no evaluation performed.",
            "feature_importances": pd.Series(
                model.feature_importances_, index=feature_cols
            ).sort_values(ascending=False),
        }
    else:
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, zero_division=0)

        print(f"  Test Accuracy  : {accuracy:.4f}  ({accuracy * 100:.2f}%)")
        print(f"\n  Classification Report:\n{report}")

        fi_series = pd.Series(model.feature_importances_, index=feature_cols).sort_values(
            ascending=False
        )
        print("  Feature Importances (high → low):")
        for feat, imp in fi_series.items():
            print(f"    {feat:<30} {imp:.4f}")

        results = {
            "accuracy": accuracy,
            "report": report,
            "feature_importances": fi_series,
        }

    # -----------------------------------------------------------------------
    # Save report to file
    # -----------------------------------------------------------------------
    report_path = REPORTS_DIR / "model_evaluation.txt"
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("Space Weather Launch Safety Predictor — Model Evaluation\n")
        fh.write("=" * 60 + "\n\n")
        fh.write(f"Training samples : {X_train.shape[0]}\n")
        fh.write(f"Testing samples  : {X_test.shape[0]}\n")
        if results["accuracy"] is not None:
            fh.write(f"Test Accuracy    : {results['accuracy']:.4f}\n\n")
            fh.write("Classification Report:\n")
            fh.write(results["report"] + "\n")
        else:
            fh.write("Test Accuracy    : N/A (empty test set)\n\n")
        fh.write("Feature Importances:\n")
        for feat, imp in results["feature_importances"].items():
            fh.write(f"  {feat:<30} {imp:.4f}\n")

    print(f"\n  Evaluation report saved → {report_path}")

    return results
