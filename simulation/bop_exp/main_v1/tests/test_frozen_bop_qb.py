import csv
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIM = os.path.abspath(os.path.join(ROOT, "..", ".."))


class FrozenBopQbTest(unittest.TestCase):
    def test_frozen_config_and_forbidden_matrix(self):
        for root, _, files in os.walk(os.path.join(ROOT, "cases")):
            if "config.txt" in files:
                text = open(os.path.join(root, "config.txt")).read()
                self.assertIn("BOP_QB_QUEUE_FRACTION 0.50", text)
        manifest = open(os.path.join(ROOT, "config",
                                     "run_manifest.csv")).read()
        for forbidden in ("bop_qc", "bop_qb_max", "bop_qb_prt",
                          "bop_qb_oracle_q0"):
            self.assertNotIn("," + forbidden + ",", manifest)
        source = open(os.path.join(SIM, "src", "point-to-point", "model",
                                   "rdma-hw.h")).read()
        self.assertIn("CC_MODE_BOP_QB = 15", source)
        self.assertIn("BOP_QB_QUEUE_FRACTION", open(os.path.join(
            SIM, "scratch", "third.cc")).read())


if __name__ == "__main__":
    unittest.main()
