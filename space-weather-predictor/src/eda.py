import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def analyze_event_distribution(df: pd.DataFrame):
    """Analyzes and prints the distribution of event types."""
    print("\n--- Event Distribution ---")
    event_counts = df["event_type"].value_counts()
    event_percentages = df["event_type"].value_counts(normalize=True) * 100
    print("Event Counts:\n", event_counts)
    print("\nEvent Percentages:\n", event_percentages)

def analyze_temporal_patterns(df: pd.DataFrame):
    """Analyzes and prints temporal patterns of events."""
    print("\n--- Temporal Analysis ---")
    print("\nEvents per year:\n", df["year"].value_counts().sort_index())
    print("\nEvents per month:\n", df["month"].value_counts().sort_index())
    print("\nEvents per hour:\n", df["hour"].value_counts().sort_index())

def analyze_solar_flares(df: pd.DataFrame):
    """Analyzes and prints statistics for solar flares."""
    print("\n--- Solar Flare Analysis ---")
    flares_df = df[df["event_type"] == "Solar Flare"].copy()
    print("Total solar flares:", len(flares_df))
    if not flares_df.empty:
        print("\nFlare class distribution:\n", flares_df["flare_class"].value_counts())
        print("\nFlare magnitude stats:\n", flares_df["flare_magnitude"].describe())
        print("\nFlare duration stats (minutes):\n", flares_df["duration_minutes"].describe())

def analyze_geomagnetic_storms(df: pd.DataFrame):
    """Analyzes and prints statistics for geomagnetic storms."""
    print("\n--- Geomagnetic Storm Analysis ---")
    storms_df = df[df["event_type"] == "Geomagnetic Storm"].copy()
    print("Total geomagnetic storms:", len(storms_df))
    if not storms_df.empty:
        print("\nStorm class distribution:\n", storms_df["class_type"].value_counts())
        print("\nKp index stats:\n", storms_df["kp_index"].describe())

def create_visualizations(df: pd.DataFrame, output_dir: Path):
    """Creates and saves a 2x2 summary visualization."""
    print("\n--- Creating Visualizations ---")
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Space Weather Event Analysis", fontsize=16)

    # Event Type Distribution
    df["event_type"].value_counts().plot(kind="pie", ax=axes[0, 0], autopct="%1.1f%%")
    axes[0, 0].set_title("Event Type Distribution")
    axes[0, 0].set_ylabel("")

    # Events per Month
    df["month"].value_counts().sort_index().plot(kind="bar", ax=axes[0, 1])
    axes[0, 1].set_title("Events per Month")
    axes[0, 1].set_xlabel("Month")
    axes[0, 1].set_ylabel("Number of Events")

    # Solar Flare Class Breakdown
    flares_df = df[df["event_type"] == "Solar Flare"]
    flares_df["flare_class"].value_counts().plot(kind="bar", ax=axes[1, 0], color="orange")
    axes[1, 0].set_title("Solar Flare Class Breakdown")
    axes[1, 0].set_xlabel("Flare Class")
    axes[1, 0].set_ylabel("Count")

    # Events per Year
    df["year"].value_counts().sort_index().plot(kind="line", ax=axes[1, 1], marker='o')
    axes[1, 1].set_title("Events per Year")
    axes[1, 1].set_xlabel("Year")
    axes[1, 1].set_ylabel("Number of Events")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    save_path = output_dir / "eda_summary.png"
    plt.savefig(save_path)
    print(f"Visualization saved to {save_path}")
    plt.close()

def run_eda(df: pd.DataFrame):
    """Runs the full exploratory data analysis pipeline."""
    if df is None:
        print("DataFrame is None. Cannot run EDA.")
        return
    analyze_event_distribution(df)
    analyze_temporal_patterns(df)
    analyze_solar_flares(df)
    analyze_geomagnetic_storms(df)
    create_visualizations(df, Path("space-weather-predictor/outputs/figures"))

if __name__ == "__main__":
    # This block is for testing with some sample data.
    # In the full pipeline, this would be called from run.py
    from data_loader import load_dataset
    from data_cleaning import clean_space_weather_data
    
    # Create a dummy csv for testing if it doesn't exist
    data_path = Path("space-weather-predictor/data")
    file_path = data_path / "space_weather_unified.csv"
    if not file_path.exists():
        print("Creating a dummy space_weather_unified.csv for EDA testing.")
        data_path.mkdir(exist_ok=True)
        dummy_data = {
            'event_id': [f'2023-{i:02d}' for i in range(1, 21)],
            'event_type': ['Solar Flare', 'CME', 'Geomagnetic Storm', 'High Speed Stream'] * 5,
            'begin_time': pd.to_datetime([f'2023-{(i%12)+1:02d}-{(i%28)+1:02d}T{i%24:02d}:00:00' for i in range(20)]),
            'peak_time': pd.to_datetime([f'2023-{(i%12)+1:02d}-{(i%28)+1:02d}T{i%24+1:02d}:00:00' for i in range(20)]),
            'end_time': pd.to_datetime([f'2023-{(i%12)+1:02d}-{(i%28)+1:02d}T{i%24+2:02d}:00:00' for i in range(20)]),
            'class_type': ['X1.0', 'C-type', 'G1', ''] * 5,
            'source_location': ['S10W20'] * 20,
            'active_region': ['12345'] * 20,
            'date': pd.to_datetime([f'2023-{(i%12)+1:02d}-{(i%28)+1:02d}' for i in range(20)]),
            'kp_index': [5, 0, 6, 0] * 5,
            'note': [''] * 20,
            'observed_time': [None] * 20,
            'source': [''] * 20
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv(file_path, index=False)

    raw_df = load_dataset()
    if raw_df is not None:
        cleaned_df = clean_space_weather_data(raw_df)
        run_eda(cleaned_df)
