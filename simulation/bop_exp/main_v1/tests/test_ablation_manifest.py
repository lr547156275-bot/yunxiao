import csv
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class AblationTest(unittest.TestCase):
    def test_ablation(self):
        rows = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "ablation_scenarios.csv"))))
        self.assertEqual(5, len(rows))
        self.assertTrue(all(x["algorithms"] == "crfm_gate|bop" for x in rows))
        self.assertEqual(10, sum(len(x["algorithms"].split("|")) for x in rows))


if __name__ == "__main__":
    unittest.main()
