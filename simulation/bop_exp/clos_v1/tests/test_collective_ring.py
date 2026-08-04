#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import ring_groups


class RingTest(unittest.TestCase):
    def test_steps_and_volume(self):
        for n in (32, 64):
            groups = ring_groups(n, 1 << 20, 2)
            self.assertEqual(len(groups), 4 * (n - 1))
            self.assertTrue(all(len(group["transmissions"]) == n
                                for group in groups))
            self.assertTrue(all(
                sum(amount for _src, _dst, amount in group["transmissions"])
                == 1 << 20 for group in groups))


if __name__ == "__main__":
    unittest.main()

