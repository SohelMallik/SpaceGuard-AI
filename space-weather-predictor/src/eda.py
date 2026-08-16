"""
eda.py
======
Exploratory Data Analysis functions for the space weather dataset.

Usage:
    from src.eda import run_eda
    run_eda(space_df)
"""

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server / pipeline use
import matplotlib.pyplot as plt

FIGURES_DIR: Path = Path(__file__).resolve().parent.parent / "outputs" / "figures"


def _ensure_figures_dir() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Individual analysis functions
# ---------------------------------------------------------------------------

def analyze_event_distribution(space_df: pd.DataFrame) -> pd.Series:
    """Count and print events per event_type."""
    counts = space_df["event_type"].value_counts()
    total = len(space_df)
    print("\n--- Event Distribution ---")
    for event_type, count in counts.items():
        pct = count / total * 100
        print(f"  {event_type:<25} {count:>6}  ({pct:.1f}%)")
    return counts


def analyze_temporal_patterns(space_df: pd.DataFrame) -> dict[str, pd.Series]:
    """Analyze events per year, month, and hour."""
    by_year = space_df.groupby("year").size()
    by_month = space_df.groupby("month").size()
    by_hour = space_df.groupby("hour").size()

    print("\n--- Temporal Analysis ---")
    print(f"  Events per year  (total years: {len(by_year)})")
    print(by_year.to_string())
    print(f"\n  Events per month:\n{by_month.to_string()}")
    print(f"\n  Events per hour  (top 5):\n{by_hour.nlargest(5).to_string()}")

    return {"by_year": by_year, "by_month": by_month, "by_hour": by_hour}


def analyze_solar_flares(space_df: pd.DataFrame) -> dict:
    """Summarize solar flare statistics."""
    flares = space_df[space_df["event_type"] == "Solar Flare"].copy()
    total = len(flares)

    class_dist = flares["flare_class"].value_counts()
    mag = flares["flare_magnitude"]
    dur = flares["duration_minutes"] if "duration_minutes" in flares.columns else pd.Series(dtype=float)

    stats = {
        "total_flares": total,
        "class_distribution": class_dist,
        "magnitude_mean": mag.mean(),
        "magnitude_median": mag.median(),
        "magnitude_min": mag.min(),
        "magnitude_max": mag.max(),
        "duration_mean": dur.mean() if len(dur) > 0 else 0.0,
        "duration_median": dur.median() if len(dur) > 0 else 0.0,
        "duration_min": dur.min() if len(dur) > 0 else 0.0,
        "duration_max": dur.max() if len(dur) > 0 else 0.0,
    }

    print("\n--- Solar Flare Analysis ---")
    print(f"  Total flares   : {total}")
    print(f"  Class distribution:\n{class_dist.to_string()}")
    print(f"  Magnitude — mean: {stats['magnitude_mean']:.2f}  median: {stats['magnitude_median']:.2f}"
          f"  min: {stats['magnitude_min']:.2f}  max: {stats['magnitude_max']:.2f}")
    print(f"  Duration (min) — mean: {stats['duration_mean']:.1f}  median: {stats['duration_median']:.1f}"
          f"  min: {stats['duration_min']:.1f}  max: {stats['duration_max']:.1f}")
    return stats


def analyze_geomagnetic_storms(space_df: pd.DataFrame) -> dict:
    """Summarize geomagnetic storm statistics."""
    storms = space_df[space_df["event_type"] == "Geomagnetic Storm"].copy()
    total = len(storms)

    if "kp_index" in storms.columns:
        kp = storms["kp_index"]
        kp_stats = {
            "mean": kp.mean(),
            "median": kp.median(),
            "min": kp.min(),
            "max": kp.max(),
        }
    else:
        kp_stats = {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}

    class_dist = storms["class_type"].value_counts() if "class_type" in storms.columns else pd.Series(dtype=int)

    stats = {
        "total_storms": total,
        "class_distribution": class_dist,
        "kp_mean": kp_stats["mean"],
        "kp_median": kp_stats["median"],
        "kp_min": kp_stats["min"],
        "kp_max": kp_stats["max"],
    }

    print("\n--- Geomagnetic Storm Analysis ---")
    print(f"  Total storms   : {total}")
    print(f"  Class distribution:\n{class_dist.head(10).to_string()}")
    print(f"  Kp — mean: {kp_stats['mean']:.2f}  median: {kp_stats['median']:.2f}"
          f"  min: {kp_stats['min']:.2f}  max: {kp_stats['max']:.2f}")
    return stats


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

def create_eda_figure(space_df: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Create a 2x2 EDA overview figure.

    Panels
    ------
    [0,0]  Event Type Distribution (bar)
    [0,1]  Events per Month (bar)
    [1,0]  Solar Flare Class Breakdown (bar)
    [1,1]  Events per Year (line)
    """
    _ensure_figures_dir()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Space Weather Event Analysis", fontsize=16, fontweight="bold")

    # --- Panel 1: Event Type Distribution ---
    ax = axes[0, 0]
    event_counts = space_df["event_type"].value_counts()
    ax.bar(event_counts.index, event_counts.values, color="#3b82d4")
    ax.set_title("Event Type Distribution")
    ax.set_xlabel("Event Type")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=20)
    for i, v in enumerate(event_counts.values):
        ax.text(i, v + max(event_counts.values) * 0.01, str(v), ha="center", fontsize=9)

    # --- Panel 2: Events per Month ---
    ax = axes[0, 1]
    by_month = space_df.groupby("month").size()
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.bar(
        [month_labels[m - 1] for m in by_month.index],
        by_month.values,
        color="#7c5cd8",
    )
    ax.set_title("Events per Month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Count")

    # --- Panel 3: Solar Flare Class Breakdown ---
    ax = axes[1, 0]
    flares = space_df[space_df["event_type"] == "Solar Flare"]
    flare_classes = flares["flare_class"].value_counts()
    colors = ["#e74c3c", "#f39c12", "#27ae60", "#3498db", "#9b59b6", "#95a5a6"]
    ax.bar(
        flare_classes.index,
        flare_classes.values,
        color=colors[: len(flare_classes)],
    )
    ax.set_title("Solar Flare Class Breakdown")
    ax.set_xlabel("Flare Class")
    ax.set_ylabel("Count")

    # --- Panel 4: Events per Year ---
    ax = axes[1, 1]
    by_year = space_df.groupby("year").size()
    ax.plot(by_year.index, by_year.values, marker="o", color="#3b82d4", linewidth=2)
    ax.fill_between(by_year.index, by_year.values, alpha=0.15, color="#3b82d4")
    ax.set_title("Events per Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Count")

    plt.tight_layout()

    if save:
        fig_path = FIGURES_DIR / "eda_overview.png"
        fig.savefig(fig_path, dpi=120, bbox_inches="tight")
        print(f"\n  EDA figure saved → {fig_path}")

    return fig


# ---------------------------------------------------------------------------
# Master EDA runner
# ---------------------------------------------------------------------------

def run_eda(space_df: pd.DataFrame) -> dict:
    """Run the complete EDA pipeline and return collected statistics."""
    print("\n=== Exploratory Data Analysis ===")

    event_counts = analyze_event_distribution(space_df)
    temporal = analyze_temporal_patterns(space_df)
    flare_stats = analyze_solar_flares(space_df)
    storm_stats = analyze_geomagnetic_storms(space_df)
    fig = create_eda_figure(space_df)
    plt.close(fig)

    return {
        "event_counts": event_counts,
        "temporal": temporal,
        "flare_stats": flare_stats,
        "storm_stats": storm_stats,
    }
