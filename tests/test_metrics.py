import unittest

from model.evaluate import calculate_metrics


class PairStub:
    def __init__(self, ground_truth, final_match, ml_score, features_payload, decision_source="ml"):
        self.ground_truth = ground_truth
        self.final_match = final_match
        self.ml_score = ml_score
        self.features_payload = features_payload
        self.decision_source = decision_source


class MetricsTests(unittest.TestCase):
    def test_calculates_live_metrics_from_pairs(self):
        pairs = [
            PairStub(True, True, 0.99, {"first_name_similarity": 1.0, "last_name_similarity": 1.0, "dob_exact_match": 1}),
            PairStub(True, True, 0.92, {"first_name_similarity": 0.9, "last_name_similarity": 0.95, "dob_exact_match": 1}),
            PairStub(False, False, 0.01, {"first_name_similarity": 0.1, "last_name_similarity": 0.1, "dob_exact_match": 0}),
        ]

        metrics = calculate_metrics(pairs)

        self.assertEqual(metrics["evaluated_pairs"], 3)
        self.assertEqual(metrics["positive_pairs"], 2)
        self.assertGreaterEqual(metrics["hybrid_accuracy"], 0.99)
        self.assertIn("baseline_accuracy", metrics)
        self.assertIn("ml_only_accuracy", metrics)


if __name__ == "__main__":
    unittest.main()
