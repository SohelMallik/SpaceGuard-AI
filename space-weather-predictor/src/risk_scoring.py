import pandas as pd

def calculate_risk_score(row: pd.Series) -> float:
    """Calculates the risk score for a given row of features."""
    x_score = min(row.get('xclass_flare_count', 0) * 40, 40)
    m_score = min(row.get('mclass_flare_count', 0) * 25, 25)
    kp_score = (row.get('max_kp_index', 0) / 9) * 20
    trend_score = min(max((row.get('event_trend', 1) - 1) * 15, 0), 15)
    
    total_score = x_score + m_score + kp_score + trend_score
    return min(total_score, 100)

def assign_risk_level(score: float) -> str:
    """Assigns a risk level based on the score."""
    if score <= 20:
        return "LOW"
    elif score <= 40:
        return "MODERATE"
    elif score <= 60:
        return "HIGH"
    else:
        return "EXTREME"

def apply_risk_scoring(risk_features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies risk scoring and level assignment to the features DataFrame.

    Args:
        risk_features_df: DataFrame with historical risk features.

    Returns:
        DataFrame with 'risk_score' and 'risk_level' columns added.
    """
    risk_features_df['risk_score'] = risk_features_df.apply(calculate_risk_score, axis=1)
    risk_features_df['risk_level'] = risk_features_df['risk_score'].apply(assign_risk_level)
    
    print("\n--- Risk Scoring Complete ---")
    print("\nRisk Level Distribution:\n", risk_features_df['risk_level'].value_counts())
    print("\nRisk Score Statistics:\n", risk_features_df['risk_score'].describe())
    print("\nTop 5 Highest-Risk Dates:\n", risk_features_df.nlargest(5, 'risk_score'))
    
    return risk_features_df

if __name__ == '__main__':
    from feature_engineering import build_risk_features
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    from pathlib import Path

    # Ensure a dummy file exists for testing
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for risk scoring testing.")
        data_path.mkdir(exist_ok=True)
        dummy_data = {
            'event_id': [f'2023-{i:02d}' for i in range(1, 40)],
            'event_type': ['Solar Flare', 'CME', 'Geomagnetic Storm', 'High Speed Stream'] * 10,
            'begin_time': pd.to_datetime([f'2023-01-{(i%5)+1:02d}T{i%24:02d}:00:00' for i in range(39)]),
            'peak_time': pd.to_datetime([f'2023-01-{(i%5)+1:02d}T{i%24+1:02d}:00:00' for i in range(39)]),
            'end_time': pd.to_datetime([f'2023-01-{(i%5)+1:02d}T{i%24+2:02d}:00:00' for i in range(39)]),
            'class_type': ['X1.0', 'C-type', 'G1', '', 'M2.0', 'C3.0'] * 6 + ['X1.0', 'C-type', 'G1'],
            'source_location': ['S10W20'] * 39,
            'active_region': ['12345'] * 39,
            'date': pd.to_datetime([f'2023-01-{(i%5)+1:02d}' for i in range(39)]),
            'kp_index': [5, 0, 6, 0, 8, 2] * 6 + [5,0,6],
            'note': [''] * 39,
            'observed_time': [None] * 39,
            'source': [''] * 39
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv(file_path, index=False)

    raw_df = load_dataset()
    if raw_df is not None:
        cleaned_df = clean_space_weather_data(raw_df)
        risk_features = build_risk_features(cleaned_df)
        scored_df = apply_risk_scoring(risk_features)
        print("\nScored DataFrame:")
        print(scored_df.head())
