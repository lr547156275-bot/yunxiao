import math
import unittest


def plan(byte_counts, max_rates, queue_bytes, capacity_bps,
         rho=1.0, background_bps=0):
    available = rho * capacity_bps - background_bps
    line = max(8.0 * size / rate
               for size, rate in zip(byte_counts, max_rates))
    link = 8.0 * (queue_bytes + sum(byte_counts)) / available
    star = max(line, link)
    rates = [min(rate, 8.0 * size / star)
             for size, rate in zip(byte_counts, max_rates)]
    return star, rates


def credits(byte_counts, q0, ecn_threshold, packet_bytes=1024):
    target = int(math.floor(0.5 * ecn_threshold))
    margin = len(byte_counts) * packet_bytes
    group = min(max(target - q0 - margin, 0), sum(byte_counts))
    raw = [group * size // sum(byte_counts) for size in byte_counts]
    remainder = group - sum(raw)
    for index in range(remainder):
        raw[index % len(raw)] += 1
    return target, margin, group, raw


class BopFormulaTest(unittest.TestCase):
    def test_shared_bop_plan(self):
        sizes = [16384, 65536, 245760]
        star, rates = plan(sizes, [1e11] * 3, 0, 1e11)
        self.assertAlmostEqual(sum(rates), 1e11)
        self.assertTrue(all(abs(8.0 * size / rate - star) < 1e-15
                            for size, rate in zip(sizes, rates)))

    def test_qb_credit_is_group_bounded_and_proportional(self):
        sizes = [16384] * 8 + [245760] * 8
        target, margin, group, per_flow = credits(
            sizes, 0, 400000)
        self.assertEqual(group, min(target - margin, sum(sizes)))
        self.assertEqual(group, sum(per_flow))
        self.assertLessEqual(group + margin, target)
        self.assertTrue(all(value <= size
                            for value, size in zip(per_flow, sizes)))


if __name__ == "__main__":
    unittest.main()
