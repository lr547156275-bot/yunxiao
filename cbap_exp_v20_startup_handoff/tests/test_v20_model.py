#!/usr/bin/env python3
import math
import unittest


def startup_budget(capacity, q0, target, margin, blind_ns):
    return max(0, math.floor(capacity +
        8e9 * (target - q0 - margin) / blind_ns))


def classify(link_rows):
    risky = [row for row in link_rows if row["flows"] >= 2 and
             row["excess"] > row["margin"]]
    return 0 if not risky else (1 if len(risky) == 1 else 2)


class V20ModelTest(unittest.TestCase):
    def test_classifications(self):
        self.assertEqual(classify([dict(flows=1, excess=100, margin=10)]), 0)
        self.assertEqual(classify([dict(flows=2, excess=11, margin=10)]), 1)
        self.assertEqual(classify([dict(flows=2, excess=11, margin=10),
                                   dict(flows=3, excess=20, margin=10)]), 2)

    def test_queue_build_and_drain(self):
        cap, blind, margin = 100_000_000_000, 10_000, 16 * 1064
        self.assertGreater(startup_budget(cap, 0, 200_000, margin, blind), cap)
        self.assertLess(startup_budget(cap, 200_000, 100_000, margin, blind), cap)

    def test_predicted_queue_bound(self):
        cap, blind, q0, target, margin = (100_000_000_000, 10_000,
                                          20_000, 100_000, 16_000)
        rate = startup_budget(cap, q0, target, margin, blind)
        predicted = max(0, q0 + (rate-cap) * blind / 8e9)
        self.assertLessEqual(predicted, target + margin + 1)


if __name__ == "__main__":
    unittest.main()
