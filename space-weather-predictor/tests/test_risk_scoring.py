import unittest
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from risk_scoring import calculate_risk_score, assign_risk_level

class TestRiskScoring(unittest.TestCase):

    def test_risk_score_calculation(self):
        """Test the logic of the risk score calculation."""
        # Test case 1: No events
        row1 = pd.Series({'xclass_flare_count': 0, 'mclass_flare_count': 0, 'max_kp_index': 0, 'event_trend': 1.0})
        self.assertEqual(calculate_risk_score(row1), 0)

        # Test case 2: One X-class flare
        row2 = pd.Series({'xclass_flare_count': 1, 'mclass_flare_count': 0, 'max_kp_index': 0, 'event_trend': 1.0})
        self.assertEqual(calculate_risk_score(row2), 40)

        # Test case 3: One M-class flare and high Kp
        row3 = pd.Series({'xclass_flare_count': 0, 'mclass_flare_count': 1, 'max_kp_index': 9, 'event_trend': 1.0})
        self.assertAlmostEqual(calculate_risk_score(row3), 25 + 20, places=5)

        # Test case 4: High trend
        row4 = pd.Series({'xclass_flare_count': 0, 'mclass_flare_count': 0, 'max_kp_index': 0, 'event_trend': 2.0})
        self.assertEqual(calculate_risk_score(row4), 15)

        # Test case 5: All maxed out
        row5 = pd.Series({'xclass_flare_count': 2, 'mclass_flare_count': 2, 'max_kp_index': 9, 'event_trend': 3.0})
        # x_score=40, m_score=25, kp_score=20, trend_score=15 -> total = 100
        self.assertEqual(calculate_risk_score(row5), 100)

        # Test case 6: Score exceeds 100 before clipping
        row6 = pd.Series({'xclass_flare_count': 3, 'mclass_flare_count': 3, 'max_kp_index': 9, 'event_trend': 1.0})
        # x_score=40, m_score=25, kp_score=20, trend_score=0 -> total = 85 (mistake in comment, let's re-calculate)
        # x_score (capped at 40), m_score (capped at 25), kp_score = (9/9)*20=20, trend_score = min(max((1-1)*15,0),15) = 0. Total = 40+25+20 = 85
        self.assertEqual(calculate_risk_score(row6), 85)
        
        # New test case for > 100
        row7 = pd.Series({'xclass_flare_count': 3, 'mclass_flare_count': 3, 'max_kp_index': 9, 'event_trend': 3.0})
        # x=40, m=25, kp=20, trend=15 -> total = 100
        self.assertEqual(calculate_risk_score(row7), 100)


    def test_risk_level_assignment(self):
        """Test the assignment of risk levels based on scores."""
        self.assertEqual(assign_risk_level(0), "LOW")
        self.assertEqual(assign_risk_level(10), "LOW")
        self.assertEqual(assign_risk_level(20), "LOW")
        
        self.assertEqual(assign_risk_level(20.1), "MODERATE")
        self.assertEqual(assign_risk_level(30), "MODERATE")
        self.assertEqual(assign_risk_level(40), "MODERATE")

        self.assertEqual(assign_risk_level(40.1), "HIGH")
        self.assertEqual(assign_risk_level(50), "HIGH")
        self.assertEqual(assign_risk_level(60), "HIGH")
        
        self.assertEqual(assign_risk_level(60.1), "EXTREME")
        self.assertEqual(assign_risk_level(80), "EXTREME")
        self.assertEqual(assign_iv`
        self.assertEqual(assign_risk_level(100), "EXTREME")

if __name__ == '__main__':
    unittest.main()
