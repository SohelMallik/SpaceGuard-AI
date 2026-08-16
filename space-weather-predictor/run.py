"""
run.py
======
Command-line pipeline for the Space Weather Launch Safety Predictor.

Runs the complete workflow:
  1. Load data
  2. Clean data
  3. Run EDA
  4. Build risk features
  5. Calculate risk scores
  6. Train model
  7. Evaluate model
  8. Save model and data
  9. Print launch-risk summary

Usage:
    python run.py

Note: This script does NOT start the Streamlit dashboard.
To launch the dashboard run:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Make src/ and dashboard/ importable when running from project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_dataset
from src.data_cleaning import clean_space_weather_data
from src.eda import run_eda
from src.feature_engineering import build_risk_features
from src.risk_scoring import apply_risk_scoring
from src.model_training import train_model, FEATURE_COLS
from src.model_evaluation import evaluate_model
from src.persistence import save_artifacts


def main() -> None:
    print("=" * 60)
    print("  Space Weather Launch Safety Predictor")
    print("  Full Pipeline Run")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1 — Load data
    # ------------------------------------------------------------------
    print("\n[1/8] Loading dataset...")
    try:
        df = load_dataset()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2 — Clean data
    # ------------------------------------------------------------------
    print("\n[2/8] Cleaning data...")
    space_df = clean_space_weather_data(df)

    # ------------------------------------------------------------------
    # Step 3 — EDA
    # ------------------------------------------------------------------
    print("\n[3/8] Running exploratory data analysis...")
    run_eda(space_df)

    # ------------------------------------------------------------------
    # Step 4 — Feature engineering
    # ------------------------------------------------------------------
    print("\n[4/8] Building 48-hour historical risk features...")
    risk_features_df = build_risk_features(space_df)

    # ------------------------------------------------------------------
    # Step 5 — Risk scoring
    # ------------------------------------------------------------------
    print("\n[5/8] Calculating risk scores...")
    scored_df = apply_risk_scoring(risk_features_df)

    # ------------------------------------------------------------------
    # Step 6 — Train model
    # ------------------------------------------------------------------
    print("\n[6/8] Training Random Forest classifier...")
    try:
        model, X_train, X_test, y_train, y_test, y_pred = train_model(scored_df)
    except ValueError as exc:
        print(f"\nERROR during training: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 7 — Evaluate model
    # ------------------------------------------------------------------
    print("\n[7/8] Evaluating model...")
    evaluate_model(model, X_train, X_test, y_train, y_test, y_pred, FEATURE_COLS)

    # ------------------------------------------------------------------
    # Step 8 — Save artifacts
    # ------------------------------------------------------------------
    print("\n[8/8] Saving model and data artifacts...")
    save_artifacts(model, scored_df, FEATURE_COLS)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  LAUNCH RISK SUMMARY")
    print("=" * 60)

    latest = scored_df.loc[scored_df["date"].idxmax()]
    print(f"  Latest Date        : {latest['date']}")
    print(f"  Risk Score         : {latest['risk_score']:.1f} / 100")
    print(f"  Risk Level         : {latest['risk_level']}")
    print(f"  Recommendation     : {latest['recommendation']}")
    print(f"  X-class Flares(48h): {int(latest['xclass_flare_count'])}")
    print(f"  M-class Flares(48h): {int(latest['mclass_flare_count'])}")
    print(f"  Max Kp (48h)       : {latest['max_kp_index']:.1f}")

    print("\n" + "=" * 60)
    print("  Pipeline complete.")
    print("  To launch the dashboard:")
    print("    streamlit run dashboard/app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
