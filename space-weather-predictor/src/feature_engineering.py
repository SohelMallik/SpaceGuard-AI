import pandas as pd
from tqdm import tqdm

def build_risk_features(space_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds historical risk features from the cleaned space weather data.

    Args:
        space_df: The cleaned space weather DataFrame.

    Returns:
        A DataFrame with historical risk features for each day.
    """
    if 'begin_time' not in space_df.columns or not pd.api.types.is_datetime64_any_dtype(space_df['begin_time']):
        raise ValueError("The 'begin_time' column must be of datetime type.")

    space_df = space_df.set_index('begin_time').sort_index()
    
    unique_dates = space_df.index.normalize().unique()
    
    features = []

    for current_date in tqdm(unique_dates, desc="Building risk features"):
        # Define the 48-hour historical window, excluding the current date
        end_time = current_date
        start_time = end_time - pd.Timedelta(hours=48)
        
        window_df = space_df.loc[start_time:end_time]
        
        # Features from the last 48 hours
        xclass_flare_count = window_df[(window_df['event_type'] == 'Solar Flare') & (window_df['flare_class'] == 'X')].shape[0]
        mclass_flare_count = window_df[(window_df['event_type'] == 'Solar Flare') & (window_df['flare_class'] == 'M')].shape[0]
        cclass_flare_count = window_df[(window_df['event_type'] == 'Solar Flare') & (window_df['flare_class'] == 'C')].shape[0]
        
        max_kp_index = window_df['kp_index'].max() if not window_df.empty else 0
        avg_kp_index = window_df['kp_index'].mean() if not window_df.empty else 0
        storm_count = window_df[window_df['kp_index'] >= 5].shape[0]

        # Event trend calculation
        latest_24h_end = current_date
        latest_24h_start = latest_24h_end - pd.Timedelta(hours=24)
        previous_24h_end = latest_24h_start
        previous_24h_start = previous_24h_end - pd.Timedelta(hours=24)

        latest_24h_events = space_df.loc[latest_24h_start:latest_24h_end].shape[0]
        previous_24h_events = space_df.loc[previous_24h_start:previous_24h_end].shape[0]

        if previous_24h_events > 0:
            event_trend = latest_24h_events / previous_24h_events
        else:
            event_trend = 1.0 # Avoid division by zero

        features.append({
            'date': current_date,
            'xclass_flare_count': xclass_flare_count,
            'mclass_flare_count': mclass_flare_count,
            'cclass_flare_count': cclass_flare_count,
            'max_kp_index': max_kp_index,
            'avg_kp_index': avg_kp_index,
            'storm_count': storm_count,
            'event_trend': event_trend
        })

    risk_features_df = pd.DataFrame(features)
    risk_features_df['date'] = pd.to_datetime(risk_features_df['date'])
    risk_features_df = risk_features_df.fillna(0)
    
    return risk_features_df.sort_values(by='date').reset_index(drop=True)

if __name__ == '__main__':
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    from pathlib import Path
    
    # Ensure a dummy file exists for testing
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for feature engineering testing.")
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
        print("\nRisk Features DataFrame:")
        print(risk_features.head())
        print("\nRisk Features DataFrame Info:")
        risk_features.info()
        print("\nRisk Features Description:")
        print(risk_features.describe())
