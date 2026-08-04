#!/usr/bin/env python3
import unittest
def enabled(pending_count, independent_aggregate_bps, admit_bps, capacity_bps=100_000_000_000):
 tolerance=max(1,1e-9*capacity_bps)
 return pending_count>=2 and independent_aggregate_bps>admit_bps+tolerance
class ScopeModel(unittest.TestCase):
 def test_single_pending_bypass(self):self.assertFalse(enabled(1,100e9,50e9))
 def test_shared_overload_enable(self):self.assertTrue(enabled(2,200e9,150e9))
 def test_low_demand_bypass(self):self.assertFalse(enabled(2,20e9,95e9))
 def test_distinct_links_bypass(self):
  self.assertTrue(all(not enabled(1,100e9,95e9) for _ in range(8)))
 def test_numerical_tolerance_only(self):
  self.assertFalse(enabled(2,100_000_000_050,100_000_000_000))
  self.assertTrue(enabled(2,100_000_000_101,100_000_000_000))
if __name__=='__main__':unittest.main(verbosity=2)
