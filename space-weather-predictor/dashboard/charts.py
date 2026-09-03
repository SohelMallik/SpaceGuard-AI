import matplotlib.pyplot as plt
import pandas as pd
from .dashboard_utils import get_recommendation

def plot_risk_score(df: pd.DataFrame):
    """Plots the daily risk score over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['date'], df['risk_score'], marker='o', linestyle='-')
    
    # Threshold lines
    ax.axhline(y=20, color='green', linestyle='--', label='GO Threshold (<=20)')
    ax.axhline(y=60, color='red', linestyle='--', label='NO-GO Threshold (>60)')
    
    ax.set_title("Risk Score per Day")
    ax.set_xlabel("Date")
    ax.set_ylabel("Risk Score (0-100)")
    ax.set_ylim(0, 105)
    ax.legend()
    plt.xticks(rotation=45)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    return fig

def plot_daily_recommendation(df: pd.DataFrame):
    """Plots the daily launch recommendations."""
    df['recommendation'] = df['risk_level'].apply(get_recommendation)
    recommendation_order = ["GO", "CAUTION", "DELAY", "NO-GO"]
    recommendation_colors = {"GO": "green", "CAUTION": "yellow", "DELAY": "orange", "NO-GO": "red"}

    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create a categorical type for ordering
    df['recommendation'] = pd.Categorical(df['recommendation'], categories=recommendation_order, ordered=True)
    
    # Plotting each day as a bar
    for i, row in df.iterrows():
        ax.bar(row['date'], 1, color=recommendation_colors.get(row['recommendation']), width=1.0)
        
    # Formatting the plot
    ax.set_title("Daily Recommendation")
    ax.set_xlabel("Date")
    ax.set_yticks([]) # Hide y-axis ticks
    plt.xticks(rotation=45)

    # Custom legend
    patches = [plt.Rectangle((0,0),1,1, color=color) for color in recommendation_colors.values()]
    ax.legend(patches, recommendation_colors.keys(), loc='upper left')

    plt.tight_layout()
    return fig

def plot_solar_events(df: pd.DataFrame):
    """Plots the solar events in a stacked bar chart."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    features_to_plot = ['xclass_flare_count', 'mclass_flare_count', 'cclass_flare_count', 'storm_count']
    
    df.plot(x='date', y=features_to_plot, kind='bar', stacked=True, ax=ax)
    
    ax.set_title("Solar Events in 48 Hours")
    ax.set_xlabel("Date")
    ax.set_ylabel("Event Count")
    plt.xticks(rotation=45)
    ax.legend(["X-class Flares", "M-class Flares", "C-class Flares", "Storms (Kp>=5)"])
    plt.tight_layout()
    return fig
