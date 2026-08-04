#!/usr/bin/env python3
import csv,math,os,re,unittest
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'../..'))
def text(path):
 with open(os.path.join(ROOT,path)) as f:return f.read()

class RateFloorStatic(unittest.TestCase):
 def test_legacy_floor_value(self):
  self.assertEqual(int(math.ceil(8*1064*1e9/5000.0)),1702400000)
  self.assertGreater(64*1702400000,95_000_000_000)
 def test_modes_coexist(self):
  h=text('simulation/src/point-to-point/model/rdma-hw.h')
  self.assertRegex(h,r'CC_MODE_CBAP_FULL_SCOPED\s*=\s*24')
  self.assertRegex(h,r'CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX\s*=\s*25')
 def test_exact_grant_branch_preserves_legacy(self):
  c=text('simulation/src/point-to-point/model/rdma-hw.cc')
  self.assertIn('if (exact)\n\t\tnewRate = requestedRate;',c)
  self.assertIn('newRate = std::max(minimum,',c)
  self.assertIn('CBAP_RATE_FLOOR_EXACT_GRANT_PACING',c)
 def test_ceil_gap_and_no_catchup(self):
  c=text('simulation/src/point-to-point/model/rdma-hw.cc')
  self.assertIn('std::ceil(gap)',c)
  self.assertIn('Time next = Simulator::Now();',c)
  self.assertIn('lastTxTimeNs',c)
 def test_zero_pause_blocks_egress(self):
  hw=text('simulation/src/point-to-point/model/rdma-hw.cc');dev=text('simulation/src/point-to-point/model/qbb-net-device.cc')
  self.assertIn('Simulator::GetMaximumSimulationTime()',hw)
  self.assertIn('zeroGrantPaused',dev)
  self.assertIn('InvalidateAndRescheduleRdma()',hw)
 def test_applied_audit_not_planner_only(self):
  c=text('simulation/src/point-to-point/model/rdma-hw.cc')
  self.assertIn('row.appliedRateSumBps += applied',c)
  self.assertIn('row.appliedCapacityViolation = row.appliedCapacityExcessBps >',c)
  self.assertIn('1e-9L * row.capacityBps',c)
  self.assertIn('if (!admissionActive)',c)
  self.assertIn('plannerCapacityBps =',c)
 def test_manifest_counts_and_identity(self):
  with open(os.path.join(ROOT,'cbap_exp_v13_ratefloor_fix/configs/semantic_manifest.csv')) as f: semantic=list(csv.DictReader(f))
  with open(os.path.join(ROOT,'cbap_exp_v13_ratefloor_fix/configs/reduced_manifest.csv')) as f: reduced=list(csv.DictReader(f))
  self.assertEqual(len(semantic),5);self.assertEqual(len(reduced),25)
  self.assertEqual({r['cc_mode'] for r in semantic if r['algorithm_name'].endswith('v12_scoped')},{'24'})
  self.assertEqual({r['cc_mode'] for r in semantic if 'v13' in r['algorithm_name']},{'25'})
 def test_frozen_algorithms_present(self):
  h=text('simulation/src/point-to-point/model/rdma-hw.h')
  self.assertRegex(h,r'CC_MODE_BOP_QB\s*=\s*15')
  c=text('simulation/scratch/third.cc')
  self.assertIn('cc_mode == 1',c)  # DCQCN configuration path
  self.assertIn('cc_mode == 3',c)  # HPCC-INT configuration path
  self.assertIn('cc_mode == 8',c)  # DCTCP configuration path

if __name__=='__main__':unittest.main(verbosity=2)
