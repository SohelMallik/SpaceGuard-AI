import pandas as pd
from pathlib import Path
import requests

# The URL for the dataset is currently a placeholder.
# The user should replace this with the actual URL.
DATA_URL = "https://example.com/space_weather_unified.csv"
DATA_PATH = Path("space-weather-predictor/data")
FILE_PATH = DATA_PATH / "space_weather_unified.csv"

def load_dataset():
    """
    Loads the space weather dataset.
    Downloads the dataset if it doesn't exist.
    """
    if FILE_PATH.exists():
        print(f"Using cached data from {FILE_PATH}")
    else:
        print(f"Downloading dataset from {DATA_URL}...")
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        try:
            response = requests.get(DATA_URL)
            response.raise_for_status()  # Raise an exception for bad status codes
            with open(FILE_PATH, "wb") as f:
                f.write(response.content)
            print(f"Dataset downloaded and saved to {FILE_PATH}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading dataset: {e}")
            return None

    try:
        df = pd.read_csv(FILE_PATH, parse_dates=["date"])
        print("Dataset loaded successfully.")
        print("Dataset shape:", df.shape)
        print("Minimum date:", df["date"].min())
        print("Maximum date:", df["date"].max())
        print("First three rows:")
        print(df.head(3))
        return df
    except FileNotFoundError:
        print(f"Error: {FILE_PATH} not found. Please check the data path or download the data.")
        return None
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None

if __name__ == "__main__":
    load_dataset()
