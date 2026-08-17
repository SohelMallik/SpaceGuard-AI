import joblib
from pathlib import Path
import pandas as pd

MODEL_PATH = Path("space-weather-predictor/models/launch_decision_model.pkl")
DATA_PATH = Path("space-weather-predictor/models/space_weather_data.pkl")

def load_model():
    """Loads the trained model from disk."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def load_saved_data():
    """Loads the saved data from disk."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data not found at {DATA_PATH}")
    return joblib.load(DATA_PATH)

def predict_risk(model, features: pd.DataFrame) -> list:
    """
    Predicts the risk level for a given set of features.

    Args:
        model: The trained model.
        features: A DataFrame with the feature columns.

    Returns:
        A list of predicted risk levels.
    """
    return model.predict(features)

def get_recommendation(risk_level: str) -> str:
    """Gets a recommendation based on the risk level."""
    # This function is duplicated in persistence.py, could be moved to a shared utils file
    recommendation_map = {
        "LOW": "GO",
        "MODERATE": "CAUTION",
        "HIGH": "DELAY",
        "EXTREME": "NO-GO"
    }
    return recommendation_map.get(risk_level, "UNKNOWN")

if __name__ == '__main__':
    # Example of how to use the prediction functions
    try:
        model = load_model()
        saved_data = load_saved_data()
        
        print("Model and data loaded successfully.")
        
        # Get features for prediction from the loaded data
        risk_features_data = saved_data.get('risk_features', [])
        if risk_features_data:
            risk_features_df = pd.DataFrame(risk_features_data)
            feature_cols = saved_data.get('feature_cols', [])
            
            if not risk_features_df.empty and feature_cols:
                # Predict on the last record
                last_record_features = risk_features_df.tail(1)[feature_cols]
                prediction = predict_risk(model, last_record_features)
                recommendation = get_recommendation(prediction[0])
                
                print("\n--- Prediction Example ---")
                print("Latest data features:\n", last_record_features)
                print(f"Predicted Risk Level: {prediction[0]}")
                print(f"Recommendation: {recommendation}")

    except FileNotFoundError as e:
        print(e)
        print("\nPlease run the main pipeline (run.py) to train the model and save artifacts.")
    except Exception as e:
        print(f"An error occurred: {e}")

