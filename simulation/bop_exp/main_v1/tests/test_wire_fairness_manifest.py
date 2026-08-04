import csv
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class WireFairnessTest(unittest.TestCase):
    def test_wire_matrix(self):
        rows = list(csv.DictReader(open(os.path.join(
            ROOT, "config", "wire_fairness_manifest.csv"))))
        self.assertEqual(6, len(rows))
        self.assertEqual(3, sum(x["scenario"] == "single_round_n16_64k"
                                for x in rows))
        self.assertTrue(all(x["algorithm"] in {
            "dcqcn", "dcqcn_wire_equalized", "bop_qb"} for x in rows))


if __name__ == "__main__":
    unittest.main()
