#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import hierarchical_groups


class HierarchicalTest(unittest.TestCase):
    def test_barrier_stage_counts(self):
        for n in (32, 64):
            leaves = n // 8
            groups = hierarchical_groups(n, 1 << 20, 2)
            expected_per_iteration = 14 + 2 * (leaves - 1)
            self.assertEqual(len(groups), 2 * expected_per_iteration)
            self.assertTrue(all(group["transmissions"] for group in groups))
            self.assertEqual(groups[expected_per_iteration]["gap_ns"], 50000)
            first = groups[:expected_per_iteration]
            sent = {rank: 0 for rank in range(n)}
            for group in first:
                for src, _dst, amount in group["transmissions"]:
                    sent[src] += amount
            local = (1 << 20) // 8
            leaves = n // 8
            expected = (2 * (7 * local) +
                        2 * (leaves - 1) * local // leaves)
            self.assertEqual(set(sent.values()), {expected})


if __name__ == "__main__":
    unittest.main()
