"""
data_loader.py
==============
Loads the space weather dataset from disk or a remote URL.

Usage:
    from src.data_loader import load_dataset
    df = load_dataset()
"""

from pathlib import Path
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration — update DATA_URL if the original source URL changes.
# ---------------------------------------------------------------------------
DATA_URL: str = (
    "https://raw.githubusercontent.com/your-org/space-weather-data/"
    "main/space_weather_unified.csv"
)
DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
DATA_PATH: Path = DATA_DIR / "space_weather_unified.csv"

REQUIRED_COLUMNS: list[str] = [
    "event_id",
    "event_type",
    "begin_time",
    "peak_time",
    "end_time",
    "class_type",
    "source_location",
    "active_region",
    "date",
    "year",
    "month",
    "day",
    "hour",
    "instruments",
    "note",
]


def _download_dataset(url: str, dest: Path) -> None:
    """Download the CSV from *url* and save it to *dest*."""
    print(f"Downloading dataset from:\n  {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Failed to download dataset from {url}.\n"
            f"Error: {exc}\n"
            "Please place space_weather_unified.csv manually in the data/ directory "
            "or update DATA_URL in src/data_loader.py."
        ) from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    print(f"  Saved to {dest}")


def _validate_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if any required column is absent."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )


def load_dataset(url: str = DATA_URL, path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the space weather dataset.

    If the CSV already exists at *path* it is used directly.
    Otherwise the file is downloaded from *url*.

    Parameters
    ----------
    url:
        Remote source URL for the dataset.
    path:
        Local path where the CSV is (or will be) stored.

    Returns
    -------
    pd.DataFrame
        Raw dataset with the ``date`` column parsed as datetime.
    """
    if path.exists():
        print(f"Using cached {path}")
    else:
        _download_dataset(url, path)

    df = pd.read_csv(path, low_memory=False)
    _validate_columns(df)

    # Parse date column — keep errors as NaT rather than raising immediately.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    print(f"\nDataset loaded:")
    print(f"  Shape  : {df.shape}")
    print(f"  Min date: {df['date'].min()}")
    print(f"  Max date: {df['date'].max()}")
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string())

    return df
