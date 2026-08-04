#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import fixed_path, topology_model


class ClosTopologyTest(unittest.TestCase):
    def test_counts_and_paths(self):
        for name, spines, physical, controlled in (
                ("clos_1to1_64h", 8, 128, 256),
                ("clos_2to1_64h", 4, 96, 192)):
            model = topology_model(name)
            self.assertEqual(len(model["spines"]), spines)
            self.assertEqual(len(model["physical"]), physical)
            self.assertEqual(len(model["controlled_links"]), controlled)
            self.assertEqual(len(fixed_path(
                model, 0, 63, model["spines"][0])), 4)
            self.assertEqual(len(fixed_path(
                model, 0, 7, model["spines"][0])), 2)


if __name__ == "__main__":
    unittest.main()
