import pandas as pd
import numpy as np

def clean_space_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the space weather DataFrame by handling missing values, duplicates,
    and performing data type conversions.

    Args:
        df: The raw space weather DataFrame.

    Returns:
        The cleaned DataFrame.
    """
    print("Initial number of rows:", len(df))

    # Fill missing values
    df["kp_index"] = df["kp_index"].fillna(0.0)
    df["class_type"] = df["class_type"].fillna("Unknown")
    df["source_location"] = df["source_location"].fillna("Unknown")
    df["active_region"] = df["active_region"].fillna("Unknown")
    df["note"] = df["note"].fillna("")

    # Handle duplicates
    df.drop_duplicates(subset="event_id", keep="first", inplace=True)
    print("Duplicates removed. Number of rows:", len(df))

    # Convert datetime columns
    for col in ["begin_time", "peak_time", "end_time", "observed_time"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Extract time features
    df["year"] = df["begin_time"].dt.year
    df["month"] = df["begin_time"].dt.month
    df["hour"] = df["begin_time"].dt.hour

    # Calculate duration
    df["duration_minutes"] = (df["end_time"] - df["begin_time"]).dt.total_seconds() / 60
    df["duration_minutes"] = df["duration_minutes"].fillna(0.0)

    # Parse solar flare data
    df["flare_class"] = "N/A"
    df["flare_magnitude"] = 0.0

    flare_mask = df["event_type"] == "Solar Flare"
    df.loc[flare_mask, "flare_class"] = df.loc[flare_mask, "class_type"].str[0]
    df.loc[flare_mask, "flare_magnitude"] = df.loc[flare_mask, "class_type"].str[1:].astype(float)
    
    # Fill NaN values in flare_magnitude that might result from parsing
    df["flare_magnitude"] = df["flare_magnitude"].fillna(0.0)


    print("Final number of rows:", len(df))
    return df

if __name__ == '__main__':
    # Example usage with a sample DataFrame
    data = {
        'event_id': ['2023-01', '2023-01', '2023-02', '2023-03'],
        'event_type': ['Solar Flare', 'Solar Flare', 'Geomagnetic Storm', 'CME'],
        'begin_time': ['2023-01-01 12:00', '2023-01-01 12:00', '2023-01-02 01:00', '2023-01-03 04:00'],
        'peak_time': ['2023-01-01 12:30', '2023-01-01 12:30', '2023-01-02 02:00', '2023-01-03 05:00'],
        'end_time': ['2023-01-01 13:00', '2023-01-01 13:00', '2023-01-02 03:00', '2023-01-03 06:00'],
        'class_type': ['X5.2', 'X5.2', 'G1', 'Unknown'],
        'source_location': ['S10W20', 'S10W20', 'Unknown', 'N30E10'],
        'active_region': ['12345', '12345', 'Unknown', '12346'],
        'date': ['2023-01-01', '2023-01-01', '2023-01-02', '2023-01-03'],
        'kp_index': [None, 5, 6, None],
        'note': ['', '', '', ''],
        'observed_time': [None, None, None, None]
    }
    sample_df = pd.DataFrame(data)
    cleaned_df = clean_space_weather_data(sample_df.copy())
    print("\nCleaned DataFrame sample:")
    print(cleaned_df)
    print("\nInfo:")
    cleaned_df.info()

