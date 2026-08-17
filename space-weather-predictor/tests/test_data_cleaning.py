import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path to import cleaning functions
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from data_cleaning import clean_space_weather_data

class TestDataCleaning(unittest.TestCase):

    def setUp(self):
        """Set up a sample DataFrame for testing."""
        self.data = {
            'event_id': ['2023-01', '2023-01', '2023-02', '2023-03'],
            'event_type': ['Solar Flare', 'Solar Flare', 'Geomagnetic Storm', 'CME'],
            'begin_time': ['2023-01-01 12:00', '2023-01-01 12:00', '2023-01-02 01:00', '2023-01-03 04:00'],
            'peak_time': ['2023-01-01 12:30', '2023-01-01 12:30', '2023-01-02 02:00', '2023-01-03 05:00'],
            'end_time': ['2023-01-01 13:00', '2023-01-01 13:00', '2023-01-02 03:00', '2023-01-03 06:00'],
            'class_type': ['X5.2', 'X5.2', 'G1', np.nan],
            'source_location': ['S10W20', 'S10W20', np.nan, 'N30E10'],
            'active_region': ['12345', '12345', np.nan, '12346'],
            'date': ['2023-01-01', '2023-01-01', '2023-01-02', '2023-01-03'],
            'kp_index': [np.nan, 5, 6, np.nan],
            'note': [np.nan, '', '', np.nan],
            'observed_time': [np.nan, np.nan, 'bad-date', np.nan]
        }
        self.df = pd.DataFrame(self.data)

    def test_duplicate_removal(self):
        """Test that duplicate event_ids are removed."""
        cleaned_df = clean_space_weather_data(self.df.copy())
        self.assertEqual(len(cleaned_df), 3)
        self.assertEqual(cleaned_df['event_id'].tolist(), ['2023-01', '2023-02', '2023-03'])

    def test_missing_value_handling(self):
        """Test that missing values are filled correctly."""
        cleaned_df = clean_space_weather_data(self.df.copy())
        self.assertEqual(cleaned_df['kp_index'].iloc[1], 0.0) # 2023-02 has kp_index filled
        self.assertEqual(cleaned_df['class_type'].iloc[2], "Unknown") # 2023-03 has class_type filled
        self.assertEqual(cleaned_df['note'].iloc[2], "")
    
    def test_datetime_conversion(self):
        """Test that datetime columns are converted correctly."""
        cleaned_df = clean_space_weather_data(self.df.copy())
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df['begin_time']))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df['peak_time']))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df['end_time']))
        # Check that 'bad-date' is coerced to NaT
        self.assertTrue(pd.isna(cleaned_df.loc[cleaned_df['event_id'] == '2023-02', 'observed_time'].iloc[0]))


    def test_flare_class_extraction(self):
        """Test that solar flare class and magnitude are extracted correctly."""
        cleaned_df = clean_space_weather_data(self.df.copy())
        flare_row = cleaned_df[cleaned_df['event_id'] == '2023-01']
        self.assertEqual(flare_row['flare_class'].iloc[0], 'X')
        self.assertEqual(flare_row['flare_magnitude'].iloc[0], 5.2)
        non_flare_row = cleaned_df[cleaned_df['event_id'] == '2023-02']
        self.assertEqual(non_flare_row['flare_class'].iloc[0], 'N/A')
        self.assertEqual(non_flare_row['flare_magnitude'].iloc[0], 0.0)

    def test_duration_calculation(self):
        """Test that the duration is calculated correctly in minutes."""
        cleaned_df = clean_space_weather_data(self.df.copy())
        # 2023-01: 13:00 - 12:00 = 60 minutes
        self.assertEqual(cleaned_df.loc[cleaned_df['event_id'] == '2023-01', 'duration_minutes'].iloc[0], 60.0)
        # 2023-02: 03:00 - 01:00 = 120 minutes
        self.assertEqual(cleaned_df.loc[cleaned_df['event_id'] == '2023-02', 'duration_minutes'].iloc[0], 120.0)

if __name__ == '__main__':
    unittest.main()
