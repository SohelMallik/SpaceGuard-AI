"""
charts.py
=========
Matplotlib chart generators for the Go/No-Go dashboard.

All functions return a matplotlib Figure.
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from dashboard.dashboard_utils import LEVEL_COLORS, RISK_COLORS


# ---------------------------------------------------------------------------
# Chart 1 — Risk Score per Day
# ---------------------------------------------------------------------------

def chart_risk_score_per_day(filtered_df: pd.DataFrame) -> plt.Figure:
    """Line chart: daily risk score with GO and NO-GO threshold lines."""
    fig, ax = plt.subplots(figsize=(12, 4))

    dates = pd.to_datetime(filtered_df["date"])
    scores = filtered_df["risk_score"].values

    ax.plot(dates, scores, color="#3b82d4", linewidth=1.5, label="Risk Score")
    ax.fill_between(dates, scores, alpha=0.10, color="#3b82d4")

    ax.axhline(y=20, color="#27ae60", linestyle="--", linewidth=1.2, label="GO threshold (20)")
    ax.axhline(y=60, color="#e74c3c", linestyle="--", linewidth=1.2, label="NO-GO threshold (60)")

    ax.set_title("Daily Launch Risk Score", fontsize=13, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Risk Score (0–100)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9)
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Chart 2 — Daily Recommendation
# ---------------------------------------------------------------------------

_REC_ORDER = {"GO": 0, "CAUTION": 1, "DELAY": 2, "NO-GO": 3}
_REC_LABELS = {0: "GO", 1: "CAUTION", 2: "DELAY", 3: "NO-GO"}
_REC_COLORS_LIST = ["#27ae60", "#f39c12", "#e67e22", "#e74c3c"]


def chart_daily_recommendation(filtered_df: pd.DataFrame) -> plt.Figure:
    """Scatter/step chart showing GO / CAUTION / DELAY / NO-GO per day."""
    df = filtered_df.copy()
    if "recommendation" not in df.columns:
        from dashboard.dashboard_utils import get_recommendation, risk_level_from_score
        df["risk_level"] = df["risk_score"].apply(risk_level_from_score)
        df["recommendation"] = df["risk_level"].apply(get_recommendation)

    df["rec_num"] = df["recommendation"].map(_REC_ORDER).fillna(0).astype(int)
    dates = pd.to_datetime(df["date"])
    colors = [_REC_COLORS_LIST[n] for n in df["rec_num"]]

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.scatter(dates, df["rec_num"], c=colors, s=30, zorder=3)
    ax.step(dates, df["rec_num"], color="#aaaaaa", linewidth=0.8, where="mid", alpha=0.5)

    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["GO", "CAUTION", "DELAY", "NO-GO"])
    ax.set_title("Daily Launch Recommendation", fontsize=13, fontweight="bold")
    ax.set_xlabel("Date")
    ax.tick_params(axis="x", rotation=30)

    patches = [mpatches.Patch(color=c, label=l) for l, c in RISK_COLORS.items()]
    ax.legend(handles=patches, fontsize=8, loc="upper right")
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Chart 3 — Solar Events in 48-Hour Window (stacked bar)
# ---------------------------------------------------------------------------

def chart_solar_events_48h(filtered_df: pd.DataFrame) -> plt.Figure:
    """Stacked bar chart: X/M/C flare counts and storm counts per day."""
    df = filtered_df.copy()
    dates = pd.to_datetime(df["date"])

    x = filtered_df["xclass_flare_count"].values
    m = filtered_df["mclass_flare_count"].values
    c = filtered_df["cclass_flare_count"].values
    s = filtered_df["storm_count"].values

    fig, ax = plt.subplots(figsize=(12, 4))

    width = 0.8
    ax.bar(dates, x, width=width, label="X-class Flares", color="#e74c3c", alpha=0.9)
    ax.bar(dates, m, width=width, bottom=x, label="M-class Flares", color="#f39c12", alpha=0.9)
    ax.bar(dates, c, width=width, bottom=x + m, label="C-class Flares", color="#27ae60", alpha=0.9)
    ax.bar(dates, s, width=width, bottom=x + m + c, label="Storms (Kp≥5)", color="#3b82d4", alpha=0.9)

    ax.set_title("Solar Events in 48-Hour Window", fontsize=13, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Event Count")
    ax.legend(fontsize=9)
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    return fig
