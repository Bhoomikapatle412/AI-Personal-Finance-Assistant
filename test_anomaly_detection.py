import unittest

from services.anomaly_detection_service import (
    calculate_mad,
    calculate_robust_z_score,
    detect_anomaly,
)


class TestAnomalyDetection(unittest.TestCase):

    def test_mad_calculation(self):
        values = [100, 110, 120, 130, 140]
        self.assertEqual(calculate_mad(values), 10)

    def test_normal_transaction(self):
        history = [100, 110, 120, 130, 140, 110, 120, 130]
        result = detect_anomaly(150, history)
        self.assertFalse(result["is_anomaly"])

    def test_anomalous_transaction(self):
        history = [100, 110, 120, 130, 140, 110, 120, 130]
        result = detect_anomaly(1000, history)
        self.assertTrue(result["is_anomaly"])

    def test_insufficient_history(self):
        result = detect_anomaly(1000, [100, 200, 300])
        self.assertFalse(result["is_anomaly"])
        self.assertEqual(result["message"], "Not enough transaction history.")

    def test_zero_mad(self):
        history = [100] * 8
        result = detect_anomaly(500, history)
        self.assertTrue(result["is_anomaly"])

    def test_robust_z_score(self):
        history = [100, 110, 120, 130, 140]
        score = calculate_robust_z_score(200, history)
        self.assertGreater(score, 3.5)


if __name__ == "__main__":
    unittest.main()