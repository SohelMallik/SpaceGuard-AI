import unittest
import pandas as pd
import joblib
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from prediction import load_model, load_saved_data, predict_risk, get_recommendation

class TestPrediction(unittest.TestCase):

    def setUp(self):
        """Set up mock model and data files for testing."""
        self.test_dir = Path("space-weather-predictor/tests/test_artifacts")
        self.test_dir.mkdir(exist_ok=True)

        # Mock model
        self.mock_model = MagicMock()
        self.mock_model.predict.return_value = ["HIGH"]
        self.model_path = self.test_dir / "launch_decision_model.pkl"
        joblib.dump(self.mock_model, self.model_path)

        # Mock data
        self.mock_data = {
            'current_stats': {'latest_risk_level': 'HIGH'},
            'feature_cols': ['feature1', 'feature2'],
            'risk_features': [{'date': '2023-01-01', 'feature1': 1, 'feature2': 2}]
        }
        self.data_path = self.test_dir / "space_weather_data.pkl"
        joblib.dump(self.mock_data, self.data_path)

        # Point the prediction module to the test artifacts
        import prediction
        prediction.MODEL_PATH = self.model_path
        prediction.DATA_PATH = self.data_path


    def tearDown(self):
        """Remove mock files after tests."""
        self.model_path.unlink()
        self.data_path.unlink()
        self.test_dir.rmdir()

    def test_load_model(self):
        """Test loading the model."""
        model = load_model()
        self.assertIsNotNone(model)
        # Check if the loaded model's predict method works as mocked
        self.assertEqual(model.predict(pd.DataFrame()), ["HIGH"])

    def test_load_saved_data(self):
        """Test loading the saved data."""
        data = load_saved_data()
        self.assertIsNotNone(data)
        self.assertEqual(data['current_stats']['latest_risk_level'], 'HIGH')

    def test_predict_risk(self):
        """Test the predict_risk function."""
        model = load_model()
        features = pd.DataFrame([{'feature1': 3, 'feature2': 4}])
        prediction = predict_risk(model, features)
        self.assertEqual(prediction, ["HIGH"])
        self.mock_model.predict.assert_called_once()


    def test_get_recommendation(self):
        """Test the recommendation mapping."""
        self.assertEqual(get_recommendation("LOW"), "GO")
        self.assertEqual(get_recommendation("MODERATE"), "CAUTION")
        self.assertEqual(get_recommendation("HIGH"), "DELAY")
        self.assertEqual(get_recommendation("EXTREME"), "NO-GO")
        self.assertEqual(get_recommendation("UNKNOWN_LEVEL"), "UNKNOWN")


if __name__ == '__main__':
    unittest.main()
