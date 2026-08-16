# Data Directory

## space_weather_unified.csv

Primary dataset for the Space Weather Launch Safety Predictor.

### Source

NASA/DONKI (Heliophysics Digital Archive and Notifications System) — historical space weather event catalog.

### Required Columns

| Column | Description |
|---|---|
| event_id | Unique event identifier |
| event_type | Solar Flare / CME / Geomagnetic Storm / High Speed Stream |
| begin_time | Event start timestamp |
| peak_time | Event peak timestamp |
| end_time | Event end timestamp |
| class_type | e.g. X5.2, M2.1, C3.4 |
| source_location | Active region location |
| active_region | NOAA active region number |
| date | Date of event (YYYY-MM-DD) |
| year | Year extracted from date |
| month | Month extracted from date |
| day | Day extracted from date |
| hour | Hour extracted from begin_time |
| instruments | Observing instrument(s) |
| note | Additional notes |

### Usage

Place `space_weather_unified.csv` in this directory.
The pipeline loads it via `src/data_loader.py`.

**Do not modify this file directly.**
All transformations operate on derived DataFrames.

### Data Leakage Note

Feature engineering uses **only historical 48-hour windows** ending before each prediction date.
The current date is never included in feature calculations.
