"""
app.py
======
Streamlit Go/No-Go Dashboard for the Space Weather Launch Safety Predictor.

Run:
    streamlit run dashboard/app.py

The dashboard loads pre-computed risk data from models/space_weather_data.pkl.
It never re-trains the model.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so src/ and dashboard/ can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.prediction import load_model, load_saved_data
from dashboard.dashboard_utils import (
    filter_date_range,
    compute_date_range_summary,
    RISK_COLORS,
    LEVEL_COLORS,
)
from dashboard.charts import (
    chart_risk_score_per_day,
    chart_daily_recommendation,
    chart_solar_events_48h,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Space Weather Launch Safety Predictor",
    page_icon="🚀",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_resource
def _load_model():
    try:
        return load_model()
    except (FileNotFoundError, RuntimeError) as exc:
        return None, str(exc)


@st.cache_data
def _load_data() -> tuple[dict | None, str]:
    try:
        data = load_saved_data()
        return data, ""
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🚀 Space Weather Launch Safety Predictor")
st.caption(
    "Educational risk-assessment system. "
    "Not an operational NASA launch decision tool."
)

# ---------------------------------------------------------------------------
# Load artifacts
# ---------------------------------------------------------------------------
model = _load_model()
data, data_error = _load_data()

if data is None:
    st.error(f"⚠️ Cannot load saved data: {data_error}")
    st.info(
        "Run the training pipeline first:\n\n"
        "```bash\npython run.py\n```"
    )
    st.stop()

current_stats: dict = data["current_stats"]
feature_cols: list[str] = data["feature_cols"]
recent_features: pd.DataFrame = data["recent_features"]

# Convert date column
recent_features["date"] = pd.to_datetime(recent_features["date"])

# Build full risk features (use recent_features as display source)
full_df = recent_features.copy()
if "risk_score" not in full_df.columns:
    from src.risk_scoring import calculate_risk_score, score_to_risk_level, get_recommendation as _rec
    full_df["risk_score"] = full_df.apply(calculate_risk_score, axis=1)
    full_df["risk_level"] = full_df["risk_score"].apply(score_to_risk_level)
    full_df["recommendation"] = full_df["risk_level"].apply(_rec)

# ---------------------------------------------------------------------------
# Current status card
# ---------------------------------------------------------------------------
st.subheader("📡 Current Status")
col1, col2, col3, col4 = st.columns(4)

rec_color = RISK_COLORS.get(current_stats.get("recommendation", "GO"), "#888")
level = current_stats.get("latest_risk_level", "UNKNOWN")

col1.metric("Current Date", current_stats.get("latest_date", "N/A"))
col2.metric("Risk Score", f"{current_stats.get('latest_risk_score', 0):.1f} / 100")
col3.metric("Risk Level", level)
col4.metric("Recommendation", current_stats.get("recommendation", "UNKNOWN"))

# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------
st.subheader("📊 Key Metrics (48h Window)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("X-class Flares", current_stats.get("xclass_48h", 0))
m2.metric("M-class Flares", current_stats.get("mclass_48h", 0))
m3.metric("Max Kp Index", f"{current_stats.get('max_kp_48h', 0):.1f}")
m4.metric("Avg Kp Index", "—")

# ---------------------------------------------------------------------------
# Date-range selector
# ---------------------------------------------------------------------------
st.subheader("📅 Date-Range Analysis")

min_date = full_df["date"].min().date()
max_date = full_df["date"].max().date()

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
with col_end:
    end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

try:
    filtered = filter_date_range(full_df, str(start_date), str(end_date))
    summary = compute_date_range_summary(filtered)
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

# Summary row
s1, s2, s3, s4, s5, s6 = st.columns(6)
s1.metric("Total Days", summary["total_days"])
s2.metric("Avg Risk Score", f"{summary['avg_risk_score']:.1f}")
s3.metric("GO days", summary["go_days"])
s4.metric("CAUTION days", summary["caution_days"])
s5.metric("DELAY days", summary["delay_days"])
s6.metric("NO-GO days", summary["no_go_days"])

st.info(
    f"📌 Highest risk: **{summary['highest_risk_date']}** "
    f"(score {summary['highest_risk_score']:.1f})   |   "
    f"Overall recommendation: **{summary['overall_recommendation']}**"
)

# ---------------------------------------------------------------------------
# Chart 1 — Risk Score per Day
# ---------------------------------------------------------------------------
st.subheader("📈 Risk Score per Day")
fig1 = chart_risk_score_per_day(filtered)
st.pyplot(fig1)
plt.close(fig1)

# ---------------------------------------------------------------------------
# Chart 2 — Daily Recommendation
# ---------------------------------------------------------------------------
st.subheader("🚦 Daily Recommendation")
fig2 = chart_daily_recommendation(filtered)
st.pyplot(fig2)
plt.close(fig2)

# ---------------------------------------------------------------------------
# Chart 3 — Solar Events in 48h Window
# ---------------------------------------------------------------------------
st.subheader("☀️ Solar Events in 48-Hour Window")
fig3 = chart_solar_events_48h(filtered)
st.pyplot(fig3)
plt.close(fig3)

# ---------------------------------------------------------------------------
# Model information
# ---------------------------------------------------------------------------
st.subheader("🤖 Model Information")
st.markdown(
    """
| Parameter | Value |
|---|---|
| Model | Random Forest Classifier |
| Number of estimators | 100 |
| Max depth | 10 |
| Random seed | 42 |
| Train/test split | Time-based — cutoff 2025-01-01 |
| Features | xclass_flare_count, mclass_flare_count, cclass_flare_count, max_kp_index, avg_kp_index, storm_count, event_trend |
| Target | risk_level (LOW / MODERATE / HIGH / EXTREME) |
"""
)

st.caption(
    "⚠️ Educational Disclaimer: This system is built for learning purposes. "
    "The risk scores and recommendations are derived from a simplified educational model "
    "and are NOT suitable for real spacecraft launch decisions."
)
