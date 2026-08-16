# Space Weather Launch Safety Predictor

> **Educational Disclaimer:** This is an educational risk-assessment system built for learning purposes.
> The risk scores and recommendations are derived from a simplified educational model
> and are **NOT suitable** for real spacecraft launch decisions.

---

## Overview

The Space Weather Launch Safety Predictor analyzes historical NASA/DONKI-style space weather events and produces a Go/No-Go launch risk assessment. It demonstrates a complete machine-learning pipeline — from raw CSV to interactive dashboard — built with Python, scikit-learn, matplotlib, and Streamlit.

---

## Problem Statement

Space weather events — solar flares, coronal mass ejections (CMEs), geomagnetic storms, and high-speed streams — can interfere with spacecraft electronics and communications. Mission operators need a systematic way to assess risk levels based on historical space weather activity before approving a launch.

---

## Objectives

1. Load and validate historical space weather event data.
2. Clean and transform the raw dataset.
3. Perform exploratory data analysis.
4. Build meaningful historical 48-hour risk features (no data leakage).
5. Calculate a simplified 0–100 educational launch risk score.
6. Classify risk into: `LOW` → `MODERATE` → `HIGH` → `EXTREME`.
7. Map risk to launch recommendations: `GO` / `CAUTION` / `DELAY` / `NO-GO`.
8. Train a Random Forest classifier using a time-based split.
9. Evaluate model accuracy, produce classification report and feature importances.
10. Save the trained model and risk data for dashboard use.
11. Provide an interactive Streamlit Go/No-Go dashboard.

---

## Dataset

**File:** `data/space_weather_unified.csv`

**Source:** NASA/DONKI (Heliophysics Digital Archive and Notifications System)

### Dataset Columns

| Column | Description |
|---|---|
| `event_id` | Unique event identifier |
| `event_type` | Solar Flare / CME / Geomagnetic Storm / High Speed Stream |
| `begin_time` | Event start timestamp |
| `peak_time` | Event peak timestamp |
| `end_time` | Event end timestamp |
| `class_type` | e.g. X5.2, M2.1, C3.4 |
| `source_location` | Active region heliographic location |
| `active_region` | NOAA active region number |
| `date` | Date of event (YYYY-MM-DD) |
| `year` | Year |
| `month` | Month |
| `day` | Day |
| `hour` | Hour (from begin_time) |
| `instruments` | Observing instrument(s) |
| `note` | Additional notes |

---

## System Architecture

```
flowchart TD
    A[space_weather_unified.csv] --> B[Data Validation]
    B --> C[Data Cleaning]
    C --> D[Clean space_df]
    D --> E[Exploratory Data Analysis]
    D --> F[Historical Feature Engineering]
    F --> G[risk_features_df]
    G --> H[Risk Score 0-100]
    H --> I[Risk Level]
    I --> J{Risk Level}
    J -->|LOW| K[GO]
    J -->|MODERATE| L[CAUTION]
    J -->|HIGH| M[DELAY]
    J -->|EXTREME| N[NO-GO]
    G --> O[Time-Based Split]
    O --> P[Random Forest Classifier]
    P --> Q[Model Evaluation]
    P --> R[launch_decision_model.pkl]
    G --> S[space_weather_data.pkl]
    R --> T[Prediction Layer]
    S --> T
    T --> U[Dashboard]
    U --> V[Risk Score Chart]
    U --> W[Recommendation Chart]
    U --> X[48h Solar Event Chart]
```

---

## Project Structure

```
space-weather-predictor/
│
├── data/
│   ├── space_weather_unified.csv   ← place dataset here
│   └── README.md
│
├── notebooks/
│   ├── ai-in-space.ipynb           ← 9-task educational notebook
│   └── bob_generated_code.ipynb    ← IBM Bob audit notebook
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py              ← load_dataset()
│   ├── data_cleaning.py            ← clean_space_weather_data()
│   ├── eda.py                      ← run_eda()
│   ├── feature_engineering.py      ← build_risk_features()
│   ├── risk_scoring.py             ← calculate_risk_score(), apply_risk_scoring()
│   ├── model_training.py           ← train_model()
│   ├── model_evaluation.py         ← evaluate_model()
│   ├── persistence.py              ← save_artifacts()
│   └── prediction.py               ← load_model(), predict_risk()
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py                      ← Streamlit dashboard
│   ├── dashboard_utils.py          ← filter, summary, color maps
│   └── charts.py                   ← 3 matplotlib chart functions
│
├── models/
│   ├── launch_decision_model.pkl   ← saved after pipeline run
│   └── space_weather_data.pkl      ← saved after pipeline run
│
├── outputs/
│   ├── figures/                    ← EDA charts
│   ├── reports/                    ← model evaluation text
│   └── predictions/
│
├── tests/
│   ├── __init__.py
│   ├── test_data_cleaning.py
│   ├── test_feature_engineering.py
│   ├── test_risk_scoring.py
│   └── test_prediction.py
│
├── requirements.txt
├── README.md
├── LICENSE
└── run.py
```

---

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Data Processing | pandas, numpy |
| Machine Learning | scikit-learn (RandomForestClassifier) |
| Visualization | matplotlib |
| Dashboard | Streamlit |
| Model Persistence | joblib |
| HTTP | requests |
| Dev Tool | IBM Bob |

---

## Machine Learning Workflow

### Data Cleaning

| Step | Action |
|---|---|
| Missing `kp_index` | Fill with `0.0` |
| Missing `class_type` | Fill with `"Unknown"` |
| Missing `source_location`, `active_region` | Fill with `"Unknown"` |
| Missing `note` | Fill with `""` |
| Duplicates | Remove by `event_id`, keep first |
| Timestamps | `pd.to_datetime(..., errors="coerce")` |
| Derived columns | `year`, `month`, `hour` from `begin_time` |
| Duration | `duration_minutes = (end_time - begin_time) / 60s` |
| Flare parsing | `flare_class`, `flare_magnitude` from `class_type` for Solar Flare events |

### Feature Engineering

For each calendar date D, features are computed from events in the window `[D - 48h, D)`.
The current date itself is **never** included to prevent data leakage.

| Feature | Description |
|---|---|
| `xclass_flare_count` | X-class Solar Flare count in 48h window |
| `mclass_flare_count` | M-class Solar Flare count in 48h window |
| `cclass_flare_count` | C-class Solar Flare count in 48h window |
| `max_kp_index` | Maximum Kp index in 48h window (0 if none) |
| `avg_kp_index` | Mean Kp index in 48h window (0 if none) |
| `storm_count` | Count of events with Kp ≥ 5 |
| `event_trend` | (events last 24h) / (events 24–48h ago); 1.0 if no older events |

### Risk Scoring

Educational simplified weighting:

```
x_score     = min(xclass_flare_count × 40, 40)
m_score     = min(mclass_flare_count × 25, 25)
kp_score    = (max_kp_index / 9) × 20
trend_score = min(max((event_trend - 1) × 15, 0), 15)
total       = min(x_score + m_score + kp_score + trend_score, 100)
```

| Component | Max contribution |
|---|---|
| X-class flares | 40 |
| M-class flares | 25 |
| Kp index | 20 |
| Event trend | 15 |
| **Total** | **100** |

### Random Forest Model

| Parameter | Value |
|---|---|
| Algorithm | RandomForestClassifier |
| n_estimators | 100 |
| max_depth | 10 |
| random_state | 42 |
| n_jobs | -1 |
| Train cutoff | Before 2025-01-01 |
| Test set | 2025-01-01 and later |
| Split method | Chronological (no shuffle) |

### Model Evaluation

Outputs saved to `outputs/reports/model_evaluation.txt`:
- Training and testing sample counts
- Test accuracy
- Classification report (precision, recall, F1 per class)
- Feature importances sorted high → low

---

## Dashboard

The Streamlit dashboard (`dashboard/app.py`) loads `models/space_weather_data.pkl` and provides:

- **Current status card** — latest date, risk score, risk level, recommendation
- **Key metrics** — X-class flares, M-class flares, max Kp, avg Kp
- **Date-range selector** — choose start and end date
- **Summary statistics** — GO / CAUTION / DELAY / NO-GO day counts
- **Chart 1** — Risk Score per Day (0–100, with threshold lines at 20 and 60)
- **Chart 2** — Daily Recommendation (categorical GO/CAUTION/DELAY/NO-GO)
- **Chart 3** — Solar Events in 48-Hour Window (stacked bar)
- **Model information** — algorithm, parameters, features

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/space-weather-predictor.git
cd space-weather-predictor

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Notebook

```bash
# From the project root
jupyter lab notebooks/ai-in-space.ipynb
```

---

## Running the Pipeline

```bash
# Place space_weather_unified.csv in data/ first, then:
python run.py
```

This will:
1. Load and validate the dataset
2. Clean the data
3. Run EDA and save charts to `outputs/figures/`
4. Build 48-hour historical features
5. Calculate risk scores
6. Train the Random Forest model
7. Evaluate the model and save report to `outputs/reports/`
8. Save `models/launch_decision_model.pkl` and `models/space_weather_data.pkl`
9. Print the final launch-risk summary

---

## Running the Dashboard

```bash
streamlit run dashboard/app.py
```

Then open: `http://localhost:8501`

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_risk_scoring.py -v
```

Test coverage:
- `test_data_cleaning.py` — missing values, duplicates, datetime, flare parsing, duration
- `test_feature_engineering.py` — 48h window, no leakage, X/M/C counts, Kp, storms, trend
- `test_risk_scoring.py` — score range, all risk levels, recommendation mapping
- `test_prediction.py` — feature cols, recommendation map, mock model prediction

---

## Example Output

```
=== Risk Scoring ===

  Risk Level Distribution:
    LOW        (GO      ):  3845  (78.3%)
    MODERATE   (CAUTION ):   721  (14.7%)
    HIGH       (DELAY   ):   273  ( 5.6%)
    EXTREME    (NO-GO   ):    71  ( 1.4%)

  Risk Score Statistics:
    Mean   : 8.43
    Median : 3.21
    Min    : 0.00
    Max    : 100.00

=== Model Evaluation ===
  Test Accuracy  : 0.9412  (94.12%)
```

---

## Risk-Level Interpretation

| Score | Level | Recommendation | Meaning |
|---|---|---|---|
| 0–20 | LOW | **GO** | Minimal space weather activity |
| 20–40 | MODERATE | **CAUTION** | Elevated activity — review |
| 40–60 | HIGH | **DELAY** | Significant activity — postpone |
| ≥ 60 | EXTREME | **NO-GO** | Severe space weather — do not launch |

---

## Limitations

- **Educational model only.** The risk weighting (X=40, M=25, Kp=20, Trend=15) is a simplified educational heuristic, not an operationally validated formula.
- **Historical data.** The model predicts derived risk-level labels generated by the project's own risk-scoring rules. It does not predict real-world launch probability.
- **48-hour window.** Feature engineering considers only the previous 48 hours, which may not capture slow-building geomagnetic storm effects.
- **No real-time data.** The pipeline operates on a static dataset. Real-time DONKI API integration is a future improvement.
- **SQLite-scale only.** The current implementation is designed for educational use and is not production-hardened.

---

## Educational Disclaimer

This project is developed as an educational demonstration of machine learning and data science techniques applied to publicly available NASA space weather data. It is NOT an operational NASA launch-safety system. The risk scores, classifications, and recommendations produced by this system should never be used to make real launch decisions.

---

## Future Improvements

- **Real-time DONKI API integration** — automatically fetch the latest events
- **Calibrated probability model** — proper probability output with uncertainty quantification
- **LSTM temporal model** — capture 7–14 day solar cycle patterns
- **Broader feature set** — include CME speed, solar wind pressure, Dst index
- **PostgreSQL backend** — for production-scale data storage
- **Alert notifications** — email / webhook when risk level exceeds threshold
- **Multi-mission comparison** — compare launch windows across missions

---

## Author

Built with **IBM Bob** as part of the IBM AI in Space educational laboratory.
