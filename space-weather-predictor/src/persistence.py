import joblib
from pathlib import Path
import pandas as pd

def get_recommendation(risk_level: str) -> str:
    """Gets a recommendation based on the risk level."""
    recommendation_map = {
        "LOW": "GO",
        "MODERATE": "CAUTION",
        "HIGH": "DELAY",
        "EXTREME": "NO-GO"
    }
    return recommendation_map.get(risk_level, "UNKNOWN")

def save_artifacts(model, scored_df: pd.DataFrame, feature_cols: list):
    """
    Saves the trained model and processed data.

    Args:
        model: The trained RandomForestClassifier model.
        scored_df: The DataFrame with features and risk scores.
        feature_cols: The list of feature columns used for training.
    """
    if model is None or scored_df.empty:
        print("Cannot save artifacts: model or data is missing.")
        return

    models_dir = Path("space-weather-predictor/models")
    models_dir.mkdir(exist_ok=True)

    # Save the model
    model_path = models_dir / "launch_decision_model.pkl"
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

    # Prepare data for saving
    latest_record = scored_df.iloc[-1]
    current_stats = {
        'latest_date': latest_record['date'],
        'latest_risk_score': latest_record['risk_score'],
        'latest_risk_level': latest_record['risk_level'],
        'recommendation': get_recommendation(latest_record['risk_level']),
        'xclass_48h': latest_record['xclass_flare_count'],
        'mclass_48h': latest_record['mclass_flare_count'],
        'max_kp_48h': latest_record['max_kp_index'],
    }

    # Last 30 risk feature records
    last_30_records = scored_df.tail(30).to_dict(orient='records')

    data_to_save = {
        'current_stats': current_stats,
        'feature_cols': feature_cols,
        'risk_features': last_30_records
    }

    data_path = models_dir / "space_weather_data.pkl"
    joblib.dump(data_to_save, data_path)
    print(f"Space weather data saved to {data_path}")

if __name__ == '__main__':
    from feature_engineering import build_risk_features
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    from risk_scoring import apply_risk_scoring
    from model_training import train_model

    # This setup is for standalone execution and testing
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for persistence testing.")
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
        
        model, _, _, _, _ = train_model(scored_df)

        if model:
            save_artifacts(model, scored_df, feature_cols)
