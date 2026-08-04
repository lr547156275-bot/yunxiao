#!/usr/bin/env python3
import csv,hashlib,json,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
for manifest,expected in (("semantic_manifest.csv",8),("validation_manifest.csv",42)):
 rows=list(csv.DictReader(open(os.path.join(ROOT,"configs",manifest))));assert len(rows)==expected
 for r in rows:
  case=os.path.join(ROOT,"cases",r["scenario"])
  for n in ("topology.txt","flow.txt","trace.txt","config.txt","rounds.txt","controlled_links.txt","controlled_paths.txt"):
   assert os.path.isfile(os.path.join(case,n)),(r["scenario"],n)
  assert r["git_commit"]

# S3 must exercise incumbent completion after delegation.  The invalid v1
# fixture used 8 MiB and completed before the newcomer release.  The corrected
# fixture reuses the already validated long-newcomer topology and changes only
# the synthetic incumbent work amount.
semantic=list(csv.DictReader(open(os.path.join(ROOT,"configs","semantic_manifest.csv"))))
s3=[r for r in semantic if r["semantic_case"]=="S3"]
assert len(s3)==1
assert s3[0]["scenario"]=="incumbent_completion_post_handoff"
s3_case=os.path.join(ROOT,"cases",s3[0]["scenario"])
s3_meta=json.load(open(os.path.join(s3_case,"scenario_meta.json")))
assert s3_meta["source_case"].endswith("fan64_msg4m_load80")
assert s3_meta["incumbent_size_bytes"]==268435456
assert s3_meta["message_bytes"]==4194304
assert s3_meta["pending_count"]==64
assert s3_meta["semantic_fixture_version"]==2
flow_lines=open(os.path.join(s3_case,"flow.txt")).read().splitlines()
round_lines=open(os.path.join(s3_case,"rounds.txt")).read().splitlines()
assert sum("268435456" in x for x in flow_lines)==1
assert sum("268435456" in x for x in round_lines)==1
assert not any("8388608" in x for x in flow_lines+round_lines)
print("PASS inputs and preregistered row counts")
