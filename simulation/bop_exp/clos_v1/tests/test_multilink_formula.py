#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import multilink_plan


class MultilinkFormulaTest(unittest.TestCase):
    def test_two_overlapping_links(self):
        flows = {0: 1000, 1: 2000, 2: 1000}
        paths = {0: [0], 1: [0, 1], 2: [1]}
        links = {
            0: {"capacity": 100_000, "ecn_threshold": 10000, "q0": 10},
            1: {"capacity": 80_000, "ecn_threshold": 10000, "q0": 20},
        }
        plan = multilink_plan(flows, paths, links,
                              {flow: 100_000 for flow in flows})
        expected = max(8 * 3010 / 100_000,
                       8 * 3020 / 80_000,
                       8 * 2000 / 100_000)
        self.assertAlmostEqual(plan["t_star"], expected)
        for link_id, state in plan["links"].items():
            rate = sum(plan["rates"][flow] for flow in flows
                       if link_id in paths[flow])
            self.assertLessEqual(rate, links[link_id]["capacity"])


if __name__ == "__main__":
    unittest.main()
