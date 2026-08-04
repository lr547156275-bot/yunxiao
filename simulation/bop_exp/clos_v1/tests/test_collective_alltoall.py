#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import alltoall_groups


class AllToAllTest(unittest.TestCase):
    def test_conservation(self):
        for n in (32, 64):
            groups = alltoall_groups(n, 1 << 20, 2)
            self.assertEqual(len(groups), 2)
            for group in groups:
                self.assertEqual(len(group["transmissions"]), n * (n - 1))
                per_source = {}
                for src, _dst, amount in group["transmissions"]:
                    per_source[src] = per_source.get(src, 0) + amount
                self.assertEqual(set(per_source.values()), {1 << 20})


if __name__ == "__main__":
    unittest.main()

