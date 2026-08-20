import pandas as pd

def get_recommendation(risk_level: str) -> str:
    """Gets a recommendation based on the risk level."""
    # This function is duplicated in other modules.
    # Consider moving to a central utility module in a refactor.
    recommendation_map = {
        "LOW": "GO",
        "MODERATE": "CAUTION",
        "HIGH": "DELAY",
        "EXTREME": "NO-GO"
    }
    return recommendation_map.get(risk_level, "UNKNOWN")

def calculate_summary(df: pd.DataFrame):
    """
    Calculates summary statistics for the given date range.

    Args:
        df: The DataFrame for the selected date range.

    Returns:
        A dictionary with summary statistics.
    """
    if df.empty:
        return {
            "total_days": 0,
            "average_risk_score": 0,
            "go_days": 0,
            "caution_days": 0,
            "delay_days": 0,
            "no_go_days": 0,
            "highest_risk_date": "N/A",
            "highest_risk_score": 0,
            "overall_recommendation": "N/A"
        }

    recommendations = df['risk_level'].apply(get_recommendation).value_counts()
    highest_risk_day = df.loc[df['risk_score'].idxmax()]
    
    summary = {
        "total_days": len(df),
        "average_risk_score": df['risk_score'].mean(),
        "go_days": recommendations.get("GO", 0),
        "caution_days": recommendations.get("CAUTION", 0),
        "delay_days": recommendations.get("DELAY", 0),
        "no_go_days": recommendations.get("NO-GO", 0),
        "highest_risk_date": highest_risk_day['date'].strftime('%Y-%m-%d'),
        "highest_risk_score": highest_risk_day['risk_score'],
        "overall_recommendation": get_recommendation(df['risk_level'].mode()[0])
    }
    return summary
