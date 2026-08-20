import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add the src directory to the path to import modules from there
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

try:
    from prediction import load_model, load_saved_data
    from charts import plot_risk_score, plot_daily_recommendation, plot_solar_events
    from dashboard_utils import calculate_summary
except ImportError as e:
    st.error(f"Error importing modules: {e}. Make sure the src and dashboard directories are structured correctly.")
    st.stop()


def main():
    st.set_page_config(page_title="Space Weather Launch Safety Predictor", layout="wide")

    st.title("🚀 Space Weather Launch Safety Predictor")

    try:
        # Load model and data
        model = load_model()
        saved_data = load_saved_data()
        current_stats = saved_data.get('current_stats', {})
        risk_features_df = pd.DataFrame(saved_data.get('risk_features', []))
        risk_features_df['date'] = pd.to_datetime(risk_features_df['date'])

    except FileNotFoundError as e:
        st.error(f"Error: {e}. Please run the main pipeline (`run.py`) to generate the necessary model and data files.")
        st.warning("The dashboard is running with sample data. For accurate predictions, please generate the artifacts.")
        # Create sample data for display if files are not found
        current_stats = {'latest_date': pd.Timestamp('2025-01-01'), 'latest_risk_score': 10, 'latest_risk_level': 'LOW', 'recommendation': 'GO', 'xclass_48h': 0, 'mclass_48h': 0, 'max_kp_48h': 2}
        risk_features_df = pd.DataFrame({
            'date': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03']),
            'risk_score': [10, 25, 50],
            'risk_level': ['LOW', 'MODERATE', 'HIGH'],
            'xclass_flare_count': [0, 0, 1],
            'mclass_flare_count': [0, 1, 0],
            'cclass_flare_count': [1, 1, 2],
            'storm_count': [0, 0, 1],
        })
        
    # --- Current Status ---
    st.header("Current Status")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Date", current_stats.get('latest_date', pd.Timestamp.now()).strftime('%Y-%m-%d'))
    col2.metric("Risk Score", f"{current_stats.get('latest_risk_score', 0):.2f}")
    col3.metric("Risk Level", current_stats.get('latest_risk_level', 'N/A'))
    col4.metric("Recommendation", current_stats.get('recommendation', 'N/A'))

    st.subheader("Key Metrics (in last 48h)")
    col1, col2, col3 = st.columns(3)
    col1.metric("X-class Flares", current_stats.get('xclass_48h', 0))
    col2.metric("M-class Flares", current_stats.get('mclass_48h', 0))
    col3.metric("Max Kp Index", f"{current_stats.get('max_kp_48h', 0):.2f}")

    # --- Date Range Analysis ---
    st.header("Date-Range Analysis")
    
    min_date = risk_features_df['date'].min()
    max_date = risk_features_df['date'].max()

    start_date, end_date = st.select_slider(
        'Select a date range',
        options=risk_features_df['date'].dt.date.unique(),
        value=(min_date.date(), max_date.date())
    )
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filter data
    filtered_df = risk_features_df[(risk_features_df['date'] >= start_date) & (risk_features_df['date'] <= end_date)]

    if not filtered_df.empty:
        # Display summary
        summary = calculate_summary(filtered_df)
        st.subheader("Summary for Selected Range")
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("Total Days", summary['total_days'])
        s_col2.metric("Avg. Risk Score", f"{summary['average_risk_score']:.2f}")
        s_col3.metric("Highest Risk Score", f"{summary['highest_risk_score']:.2f} on {summary['highest_risk_date']}")
        s_col4.metric("Overall Recommendation", summary['overall_recommendation'])


        # --- Visualizations ---
        st.subheader("Risk Trend")
        st.pyplot(plot_risk_score(filtered_df))

        st.subheader("Recommendation Trend")
        st.pyplot(plot_daily_recommendation(filtered_df))

        st.subheader("Solar Event Breakdown")
        st.pyplot(plot_solar_events(filtered_df))

    else:
        st.warning("No data available for the selected date range.")

    # --- Model Information ---
    with st.expander("Model Information"):
        st.text("Model: Random Forest Classifier")
        st.text("Number of estimators: 100")
        st.text("Max depth: 10")
        st.text("Random seed: 42")
        st.text("Features used: xclass_flare_count, mclass_flare_count, cclass_flare_count, max_kp_index, avg_kp_index, storm_count, event_trend")

if __name__ == "__main__":
    main()
