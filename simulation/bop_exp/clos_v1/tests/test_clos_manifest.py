#!/usr/bin/env python3
import collections
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import CONFIG, FORBIDDEN, read_csv, scenario_specs


class ManifestTest(unittest.TestCase):
    def test_exact_matrix(self):
        specs = scenario_specs()
        self.assertEqual(len([x for x in specs
                              if x["section"] == "clos_1to1"]), 12)
        self.assertEqual(len([x for x in specs
                              if x["section"] == "dlrm_like"]), 1)
        self.assertEqual(len([x for x in specs
                              if x["section"] == "clos_2to1"]), 3)
        rows = read_csv(os.path.join(CONFIG, "run_manifest.csv"))
        self.assertEqual(len(rows), 240)
        counts = collections.Counter(row["seed"] for row in rows)
        self.assertEqual(counts, {"1": 80, "2": 80, "3": 80})
        text = "\n".join(row["algorithm"] for row in rows).lower()
        self.assertFalse(any(name in text for name in FORBIDDEN))
        self.assertEqual(len(set(row["run_id"] for row in rows)), 240)


if __name__ == "__main__":
    unittest.main()

