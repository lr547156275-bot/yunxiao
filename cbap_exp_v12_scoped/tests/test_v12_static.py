#!/usr/bin/env python3
import csv,hashlib,os,re,subprocess,unittest
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."));REPO=os.path.abspath(os.path.join(ROOT,".."))
SRC=open(os.path.join(REPO,'simulation/src/point-to-point/model/rdma-hw.cc')).read();HDR=open(os.path.join(REPO,'simulation/src/point-to-point/model/rdma-hw.h')).read()
class Static(unittest.TestCase):
 def test_modes_and_identity(self):
  self.assertRegex(HDR,r'CC_MODE_CBAP_FULL\s*=\s*23')
  self.assertRegex(HDR,r'CC_MODE_CBAP_FULL_SCOPED\s*=\s*24')
  self.assertIn('CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION',HDR)
 def test_structural_rule(self):
  body=SRC[SRC.index('void RdmaHw::PlanScopedCbapBatch'):SRC.index('void RdmaHw::PlanCbapBatch')]
  self.assertIn('count >= 2 && aggregate > capacity',body)
  self.assertIn('std::ceil(1e-9 *',body)
  self.assertNotRegex(body,r'1\.1\s*\*|1\.3\s*\*|messageBytes')
  self.assertIn('latest.sampleTimeNs <= group.applicationReadyNs',body)
 def test_frozen_dispatch_and_bypass(self):
  self.assertIn('PlanCbapBatch(groupId);',SRC)
  self.assertIn('!scopedCbapHolding',SRC)
  self.assertIn('qp->cbap.enabled',SRC)
  self.assertIn('batch.decisionDelayNs == UINT64_C(5000)',SRC)
 def test_manifests(self):
  with open(os.path.join(ROOT,'configs','scope_manifest.csv')) as f:s=list(csv.DictReader(f))
  with open(os.path.join(ROOT,'configs','core_manifest.csv')) as f:c=list(csv.DictReader(f))
  self.assertEqual(len(s),18);self.assertEqual(len(c),170)
  self.assertEqual(len(set(x['run_id'] for x in s)),18);self.assertEqual(len(set(x['run_id'] for x in c)),170)
  self.assertEqual(sum(int(x['ablation'])==0 for x in c),161);self.assertEqual(sum(int(x['ablation'])==1 for x in c),9)
 def test_cases(self):
  self.assertEqual(len(next(os.walk(os.path.join(ROOT,'cases','scope')))[1]),6)
  self.assertEqual(len(next(os.walk(os.path.join(ROOT,'cases','core')))[1]),23)
  for family in ('scope','core'):
   for case in next(os.walk(os.path.join(ROOT,'cases',family)))[1]:
    d=os.path.join(ROOT,'cases',family,case)
    for n in ('topology.txt','flow.txt','rounds.txt','fixed_paths.txt','controlled_links.txt','controlled_paths.txt','group_schedule.txt','trace.txt','config.txt','scenario_meta.json'):
     self.assertTrue(os.path.isfile(os.path.join(d,n)),(family,case,n))
 def test_frozen_archive_unchanged(self):
  listing=os.path.join(ROOT,'preflight','cbap_v11_freeze.sha256')
  self.assertEqual(subprocess.call(['sha256sum','-c',listing],cwd=REPO,stdout=subprocess.DEVNULL),0)
if __name__=='__main__':unittest.main(verbosity=2)
