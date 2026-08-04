#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from closlib import percentile


class MetricsTest(unittest.TestCase):
    def test_percentiles_and_units(self):
        values = [1, 2, 3, 4, 5]
        self.assertEqual(percentile(values, .95), 5)
        self.assertEqual(percentile(values, .50), 3)
        payload = 1 << 20
        duration_s = 100e-6
        self.assertAlmostEqual(payload * 8 / duration_s / 1e9,
                               83.88608)


if __name__ == "__main__":
    unittest.main()
