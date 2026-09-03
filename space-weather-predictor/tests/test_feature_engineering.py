import unittest
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from feature_engineering import build_risk_features

class TestFeatureEngineering(unittest.TestCase):

    def setUp(self):
        """Set up a sample DataFrame for testing feature engineering."""
        data = {
            'event_type': ['Solar Flare', 'Solar Flare', 'Geomagnetic Storm', 'Solar Flare', 'Solar Flare'],
            'begin_time': pd.to_datetime([
                '2023-01-01 10:00',  # Event 1 (C-class)
                '2023-01-02 12:00',  # Event 2 (X-class)
                '2023-01-02 18:00',  # Event 3 (Storm Kp=6)
                '2023-01-03 14:00',  # Event 4 (M-class)
                '2023-01-04 09:00'   # Event 5 (C-class) - This is on the day of prediction, should be included
            ]),
            'flare_class': ['C', 'X', 'N/A', 'M', 'C'],
            'kp_index': [2.0, 3.0, 6.0, 4.0, 1.0]
        }
        self.df = pd.DataFrame(data)
        # Add required columns from cleaning
        self.df['date'] = self.df['begin_time'].dt.normalize()


    def test_48_hour_window(self):
        """Test that features are calculated correctly within the 48-hour window."""
        # For date 2023-01-03, window is from 2023-01-01 14:00 to 2023-01-03 14:00
        # This includes events 2, 3, and 4
        features_df = build_risk_features(self.df)
        
        # Check features for 2023-01-03
        day_features = features_df[features_df['date'] == pd.Timestamp('2023-01-03')].iloc[0]
        
        # In the 48h before 2023-01-03 00:00:00 (i.e. 2023-01-01 00:00 to 2023-01-02 23:59)
        # We have events 1, 2, 3
        # Expected counts for 2023-01-03:
        # X-flares: 1 (Event 2)
        # M-flares: 0
        # C-flares: 1 (Event 1)
        # Max Kp: 6.0 (Event 3)
        # Avg Kp: (2+3+6)/3 = 3.666
        # Storms (Kp>=5): 1 (Event 3)
        
        # The logic in build_risk_features is slightly different from my comment above.
        # Let's trace it for current_date = 2023-01-03.
        # end_time = 2023-01-03 00:00:00
        # start_time = 2023-01-01 00:00:00
        # window_df contains events from 2023-01-01 and 2023-01-02.
        # So events 1, 2, 3 are in the window.
        
        self.assertEqual(day_features['xclass_flare_count'], 1)
        self.assertEqual(day_features['mclass_flare_count'], 0)
        self.assertEqual(day_features['cclass_flare_count'], 1)
        self.assertEqual(day_features['max_kp_index'], 6.0)
        self.assertAlmostEqual(day_features['avg_kp_index'], (2.0 + 3.0 + 6.0) / 3, places=5)
        self.assertEqual(day_features['storm_count'], 1)

    def test_no_future_leakage(self):
        """Test that events on the current date are not included in the feature calculation window."""
        # For date 2023-01-04, the window should only include events up to 2023-01-04 00:00
        # This means Event 5 should not be in the feature calculation for 2023-01-03.
        
        day_features = build_risk_features(self.df)
        day_features_01_04 = day_features[day_features['date'] == pd.Timestamp('2023-01-04')].iloc[0]

        # Window for 2023-01-04 is from 2023-01-02 00:00 to 2023-01-03 23:59
        # This includes events 2, 3, 4
        self.assertEqual(day_features_01_04['xclass_flare_count'], 1)
        self.assertEqual(day_features_01_04['mclass_flare_count'], 1)
        self.assertEqual(day_features_01_04['cclass_flare_count'], 0) # Event 1 is out of window
        self.assertEqual(day_features_01_04['max_kp_index'], 6.0)
        self.assertAlmostEqual(day_features_01_04['avg_kp_index'], (3.0 + 6.0 + 4.0) / 3, places=5)

    def test_event_trend(self):
        """Test the event trend calculation."""
        features_df = build_risk_features(self.df)
        day_features = features_df[features_df['date'] == pd.Timestamp('2023-01-03')].iloc[0]

        # For 2023-01-03:
        # Latest 24h (2023-01-02): 2 events (Event 2, 3)
        # Previous 24h (2023-01-01): 1 event (Event 1)
        # Trend = 2 / 1 = 2.0
        self.assertEqual(day_features['event_trend'], 2.0)

        # Test division by zero case
        df_no_prior = self.df[self.df.begin_time > '2023-01-02']
        features_no_prior = build_risk_features(df_no_prior)
        day_features_no_prior = features_no_prior[features_no_prior['date'] == pd.Timestamp('2023-01-03')].iloc[0]
        # Previous 24h has 0 events, so trend should default to 1.0
        self.assertEqual(day_features_no_prior['event_trend'], 1.0)


if __name__ == '__main__':
    unittest.main()
