import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def train_model(scored_df: pd.DataFrame):
    """
    Trains a Random Forest Classifier to predict the risk level.

    Args:
        scored_df: DataFrame with features and risk levels.

    Returns:
        A trained model and the train/test data splits.
    """
    if scored_df is None or scored_df.empty:
        print("Scored DataFrame is empty. Cannot train model.")
        return None, None, None, None, None

    feature_cols = [
        "xclass_flare_count",
        "mclass_flare_count",
        "cclass_flare_count",
        "max_kp_index",
        "avg_kp_index",
        "storm_count",
        "event_trend"
    ]
    target_col = "risk_level"

    # Ensure all feature columns are present
    for col in feature_cols:
        if col not in scored_df.columns:
            raise ValueError(f"Missing feature column in DataFrame: {col}")

    # Time-based split
    cutoff_date = "2025-01-01"
    train_df = scored_df[scored_df['date'] < cutoff_date]
    test_df = scored_df[scored_df['date'] >= cutoff_date]

    if train_df.empty:
        print("Training data is empty. Check the date range and cutoff date.")
        return None, None, None, None, None
    if test_df.empty:
        print("Test data is empty. Check the date range and cutoff date.")
        # We can still proceed to train the model, but evaluation will not be possible.
        pass

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols] if not test_df.empty else pd.DataFrame(columns=feature_cols)
    y_test = test_df[target_col] if not test_df.empty else pd.Series()

    print("\n--- Model Training ---")
    print("Training data shape:", X_train.shape)
    print("Testing data shape:", X_test.shape)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    print("Training model...")
    model.fit(X_train, y_train)
    print("Model training complete.")
    
    return model, X_train, y_train, X_test, y_test

if __name__ == '__main__':
    from feature_engineering import build_risk_features
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    from risk_scoring import apply_risk_scoring
    from pathlib import Path

    # Ensure a dummy file exists for testing
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for model training testing.")
        data_path.mkdir(exist_ok=True)
        # Create data that spans the train/test split date
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
        risk_features = build_risk_features(cleaned_df)
        scored_df = apply_risk_scoring(risk_features)
        
        # Make sure date column is in datetime format before splitting
        scored_df['date'] = pd.to_datetime(scored_df['date'])

        model, X_train, y_train, X_test, y_test = train_model(scored_df)

        if model:
            print("\nModel trained successfully.")
            if not X_test.empty:
                print("Test predictions:", model.predict(X_test.head()))
