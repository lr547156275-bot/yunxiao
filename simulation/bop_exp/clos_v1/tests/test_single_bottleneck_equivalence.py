#!/usr/bin/env python3
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import multilink_plan


class SingleBottleneckEquivalenceTest(unittest.TestCase):
    def test_frozen_formula_equivalence(self):
        flows = {rank: 65536 for rank in range(16)}
        paths = {rank: [0] for rank in flows}
        links = {0: {"capacity": 100_000_000_000,
                     "ecn_threshold": 400_000, "q0": 0}}
        plan = multilink_plan(
            flows, paths, links,
            {rank: 100_000_000_000 for rank in flows})
        room = 200_000 - 16 * 1024
        old_group_credit = min(room, sum(flows.values()))
        self.assertEqual(sum(plan["credits"].values()), old_group_credit)
        old_star = 8.0 * sum(flows.values()) / 100_000_000_000
        self.assertAlmostEqual(plan["t_star"], old_star)
        old_rate = math.floor(8.0 * 65536 / old_star)
        self.assertTrue(all(rate == old_rate
                            for rate in plan["rates"].values()))


if __name__ == "__main__":
    unittest.main()

