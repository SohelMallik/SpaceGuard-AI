import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from pathlib import Path

def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, feature_cols: list):
    """
    Evaluates the trained model and prints the results.

    Args:
        model: The trained RandomForestClassifier model.
        X_test: The test features.
        y_test: The test target variable.
        feature_cols: The list of feature columns used for training.
    """
    if model is None or X_test.empty or y_test.empty:
        print("Cannot evaluate model: model or test data is missing.")
        return

    print("\n--- Model Evaluation ---")
    y_pred = model.predict(X_test)

    # Accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {accuracy:.4f}")

    # Classification Report
    report = classification_report(y_test, y_pred, zero_division=0)
    print("\nClassification Report:\n", report)

    # Feature Importances
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\nFeature Importances:\n", importances)

    # Save report
    report_path = Path("space-weather-predictor/outputs/reports")
    report_path.mkdir(exist_ok=True)
    with open(report_path / "model_evaluation_report.txt", "w") as f:
        f.write("Model Evaluation Report\n")
        f.write("="*25 + "\n\n")
        f.write(f"Test Accuracy: {accuracy:.4f}\n\n")
        f.write("Classification Report:\n")
        f.write(report)
        f.write("\n\nFeature Importances:\n")
        f.write(importances.to_string())
    
    print(f"\nEvaluation report saved to {report_path / 'model_evaluation_report.txt'}")


if __name__ == '__main__':
    from feature_engineering import build_risk_features
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    from risk_scoring import apply_risk_scoring
    from model_training import train_model
    
    # This setup is duplicated from model_training.py for standalone execution
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for model evaluation testing.")
        data_path.mkdir(exist_ok=True)
        dates = pd.to_datetime([f'2024-12-{(i%31)+1:02d}' for i in range(20)] + [f'2025-01-{(i%28)+1:02d}' for i in range(20)])
        dummy_data = {
            'event_id': [f'2024-{i:02d}' for i in range(1, 41)],
            'event_type': ['Solar Flare', 'CME', 'Geomagnetic Storm', 'High Speed Stream'] * 10,
            'begin_time': dates,
            'peak_time': dates + pd.Timedelta(hours=1),
            'end_time': dates + pd.Timedelta(hours=2),
            'class_type': ['X1.0', 'C-type', 'G1', '', 'M2.0', 'C3.0'] * 6 + ['X1.0', 'C-type', 'G1','','',''],
            'source_location': ['S10W20'] * 40,
            'active_region': ['12345'] * 40,
            'date': dates,
            'kp_index': [5, 0, 6, 0, 8, 2] * 6 + [5,0,6,0],
            'note': [''] * 40,
            'observed_time': [None] * 40,
            'source': [''] * 40
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv(file_path, index=False)

    raw_df = load_dataset()
    if raw_df is not None:
        cleaned_df = clean_space_weather_data(raw_df)
        risk_features_df = build_risk_features(cleaned_df)
        scored_df = apply_risk_scoring(risk_features_df)
        
        scored_df['date'] = pd.to_datetime(scored_df['date'])

        feature_cols = [
            "xclass_flare_count", "mclass_flare_count", "cclass_flare_count",
            "max_kp_index", "avg_kp_index", "storm_count", "event_trend"
        ]
        
        model, X_train, y_train, X_test, y_test = train_model(scored_df)

        if model and not X_test.empty:
            evaluate_model(model, X_test, y_test, feature_cols)
        else:
            print("Skipping evaluation due to missing model or test data.")
