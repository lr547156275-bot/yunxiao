#!/usr/bin/env python3
import csv,hashlib,json,os,re,unittest

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
V11=os.path.join(ROOT,'cbap_exp_v11_freeze')
def text(path):
 with open(path) as stream:return stream.read()
SNAP=text(os.path.join(V11,'preflight','source_snapshot_path.txt')).strip()
def section(value,start,end):return value.split(start,1)[1].split(end,1)[0]

class Formula(unittest.TestCase):
 def test_legacy_and_adaptive(self):
  for rate in (100000000,1000000000,12920000000,50000000000,95000000000):
   frac=int(1.10*rate);absolute=rate+2000000000
   self.assertEqual(min(frac,absolute),rate+min(int(.10*rate),2000000000))
   self.assertEqual(max(frac,absolute),rate+max(int(.10*rate),2000000000))
 def test_source_has_both_policies_and_frozen_mode(self):
  h=text(os.path.join(ROOT,'simulation/src/point-to-point/model/rdma-hw.h'))
  c=text(os.path.join(ROOT,'simulation/src/point-to-point/model/rdma-hw.cc'))
  self.assertRegex(h,r'CC_MODE_BOP_QB\s*=\s*15')
  self.assertIn('CBAP_INCREASE_LEGACY_V1 = 0',h);self.assertIn('CBAP_INCREASE_ADAPTIVE_V11 = 1',h)
  self.assertIn('1.10L * current',c);self.assertIn('std::max(fractionalCandidate, absoluteCandidate)',c);self.assertIn('std::min(fractionalCandidate, absoluteCandidate)',c)
 def test_seed1_packet_trace_is_bounded(self):
  prepare=text(os.path.join(V11,'scripts','prepare_run.py'))
  self.assertIn('"CBAP_PACKET_TRACE_FILE":"cbap_packet_trace.csv"',prepare)
  self.assertIn('"CBAP_PACKET_TRACE_MAX_MB":128',prepare)
 def test_protected_functions_are_unchanged(self):
  before=text(os.path.join(SNAP,'simulation/src/point-to-point/model/rdma-hw.cc'));after=text(os.path.join(ROOT,'simulation/src/point-to-point/model/rdma-hw.cc'))
  for start,end in (('bool RdmaHw::HasCompletePostReleaseFeedback','bool RdmaHw::HasPostReleaseEmergencyEvidence'),('bool RdmaHw::HasPostReleaseEmergencyEvidence','void RdmaHw::UpdateCbapTrackingRateIntegral'),('void RdmaHw::PktSent','void RdmaHw::UpdateNextAvail'),('std::map<uint32_t, uint64_t> RdmaHw::ComputeCbapProgressiveFill','void RdmaHw::PlanCbapBatch')):
   self.assertEqual(section(before,start,end),section(after,start,end),start)
 def test_old_v1_tree_not_modified(self):
  prior={line.split('\t')[0]:(line.split('\t')[1],line.split('\t')[2].strip()) for line in text(os.path.join(V11,'preflight','cbap_v1_file_index.tsv')).splitlines()}
  current={}
  base=os.path.join(ROOT,'cbap_exp_v1_fix')
  for root,_,files in os.walk(base):
   for name in files:
    p=os.path.join(root,name);current[os.path.relpath(p,base)]=(str(os.path.getsize(p)),str(os.stat(p).st_mtime))
  self.assertEqual(set(prior),set(current));self.assertTrue(all(prior[k][0]==current[k][0] for k in prior))

class Manifests(unittest.TestCase):
 def rows(self,name):
  with open(os.path.join(V11,'configs',name)) as stream:return list(csv.DictReader(stream))
 def test_counts(self):
  self.assertEqual(11,len(self.rows('semantic_manifest.csv')));self.assertEqual(63,len(self.rows('freeze_manifest.csv')));self.assertEqual(54,len(self.rows('victim_manifest.csv')))
 def test_identity(self):
  for r in self.rows('freeze_manifest.csv')+self.rows('semantic_manifest.csv'):
   if r['algorithm_name'].endswith('_v11'):self.assertEqual(('v1.1','adaptive_max'),(r['cbap_version'],r['increase_policy']))
   if r['algorithm_name'].endswith('_v1'):self.assertEqual(('v1','legacy_min'),(r['cbap_version'],r['increase_policy']))
   self.assertEqual('0.10',r['increase_fraction']);self.assertEqual('2000000000',r['increase_absolute_bps'])
 def test_victim_topologies_not_upstream_capacity_bottleneck(self):
  for r in self.rows('victim_manifest.csv')[::3]:
   d=os.path.join(V11,'victim_cases',r['subcase'])
   with open(os.path.join(d,'scenario_meta.json')) as stream:meta=json.load(stream)
   offered=meta['contributor_count']*meta['contributor_access_rate_gbps']*1000000000+100000000000
   self.assertGreater(meta['sa_sb_capacity_bps'],offered);self.assertFalse(meta['sa_sb_is_capacity_bottleneck'])
   paths=text(os.path.join(d,'controlled_paths.txt')).splitlines();self.assertIn('0 2 1 3',paths)

if __name__=='__main__':unittest.main()
