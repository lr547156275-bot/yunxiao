import csv
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class MetricsTest(unittest.TestCase):
    def test_required_metrics(self):
        rows = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "metrics_schema.csv"))))
        actual = {(x["file"], x["field"]) for x in rows}
        required = {
            ("algorithm_summary.csv", "group_rct_mean_us"),
            ("algorithm_summary.csv", "flow_fct_p99_us"),
            ("algorithm_summary.csv", "active_wire_utilization"),
            ("queue_summary.csv", "queue_max_bytes"),
            ("congestion_summary.csv", "ecn_marks"),
            ("wire_summary.csv", "application_payload_bytes"),
            ("algorithm_summary.csv", "T_star_us"),
            ("algorithm_summary.csv", "safety_formula_valid"),
        }
        self.assertTrue(required <= actual)


if __name__ == "__main__":
    unittest.main()
