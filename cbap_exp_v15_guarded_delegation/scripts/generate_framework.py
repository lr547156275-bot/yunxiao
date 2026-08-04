#!/usr/bin/env python3
"""Generate immutable v1.5 inputs/manifests; never invokes ns-3."""
import csv, hashlib, json, os, shutil, subprocess

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
REPO=os.path.abspath(os.path.join(ROOT,".."))
V14=os.path.join(REPO,"cbap_exp_v14_stable_handoff","cases")
SOURCES={
 "fan32_msg1m_load80":"fan32_msg1m_load80",
 "fan64_msg64k_load80":"fan64_msg64k_load80",
 "fan64_msg256k_load80":"fan64_msg256k_load80",
 "fan64_msg1m_load80":"fan64_msg1m_load80",
 "fan64_msg4m_load80":"fan64_msg4m_load80",
 "fan64_msg1m_load95":"fan64_msg1m_load95",
 "fan64_msg4m_load95":"fan64_msg4m_load80",
 "incumbent_completion_post_handoff":"fan64_msg4m_load80",
 "cap_bound_anti_windup":"fan64_msg1m_load95",
 "stale_feedback":"fan64_msg1m_load80",
}

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def copy_case(name,source):
 src=os.path.join(V14,source); dst=os.path.join(ROOT,"cases",name)
 if not os.path.isdir(src): raise SystemExit("missing validated case "+src)
 os.makedirs(dst,exist_ok=True)
 for x in os.listdir(src):
  a=os.path.join(src,x); b=os.path.join(dst,x)
  if os.path.isfile(a): shutil.copy2(a,b)
 if name=="fan64_msg4m_load95":
  p=os.path.join(dst,"topology.txt"); t=open(p).read()
  if t.count("0 66 80Gbps 0.001ms 0\n")!=1: raise SystemExit("load transform mismatch")
  open(p,"w").write(t.replace("0 66 80Gbps 0.001ms 0\n","0 66 95Gbps 0.001ms 0\n"))
 if name=="incumbent_completion_post_handoff":
  for fn in ("flow.txt","rounds.txt"):
   p=os.path.join(dst,fn); t=open(p).read()
   if t.count("536870912")!=1: raise SystemExit("incumbent size transform mismatch")
   # The original 8 MiB S3 fixture completed before the newcomer release and
   # therefore could not exercise post-delegation reserve release.  A 256 MiB
   # incumbent cannot finish before the guarded handoff window at the fixed
   # 80 Gbit/s offered load, while the verified 64 x 4 MiB newcomer workload
   # remains active long enough to observe the reserve transition.  This is a
   # deterministic semantic fixture correction, not a parameter search.
   open(p,"w").write(t.replace("536870912","268435456"))
 meta_path=os.path.join(dst,"scenario_meta.json")
 meta=json.load(open(meta_path)); meta.update(scenario=name,generated_only=True,
  source_case="cbap_exp_v14_stable_handoff/cases/"+source,
  v15_input_generation="deterministic_no_search")
 if name=="fan64_msg4m_load95": meta["incumbent_offered_load_percent"]=95
 if name=="incumbent_completion_post_handoff":
  meta.update(incumbent_size_bytes=268435456,
              semantic_fixture_version=2,
              semantic_intent="incumbent_completes_after_guarded_delegation",
              supersedes_invalid_fixture="incumbent_completion_8MiB")
 with open(meta_path,"w") as f: json.dump(meta,f,indent=2,sort_keys=True); f.write("\n")
 hashes={x:sha(os.path.join(dst,x)) for x in sorted(os.listdir(dst))
         if os.path.isfile(os.path.join(dst,x)) and not x.endswith("hashes.json")}
 with open(os.path.join(dst,"v15_input_hashes.json"),"w") as f:
  json.dump(hashes,f,indent=2,sort_keys=True); f.write("\n")

def copy_parking(name):
 src=os.path.join(REPO,"cbap_exp_v12_scoped","cases","scope","synchronous_parking_lot")
 dst=os.path.join(ROOT,"cases",name); os.makedirs(dst,exist_ok=True)
 for x in os.listdir(src):
  a=os.path.join(src,x)
  if os.path.isfile(a): shutil.copy2(a,os.path.join(dst,x))
 p=os.path.join(dst,"scenario_meta.json"); meta=json.load(open(p))
 meta.update(scenario=name,generated_only=True,pending_flow_ids=[0,1,2],
             incumbent_flow_ids=[],source_case="v12 verified synchronous parking lot")
 with open(p,"w") as f: json.dump(meta,f,indent=2,sort_keys=True); f.write("\n")
 hashes={x:sha(os.path.join(dst,x)) for x in sorted(os.listdir(dst))
         if os.path.isfile(os.path.join(dst,x)) and not x.endswith("hashes.json")}
 with open(os.path.join(dst,"v15_input_hashes.json"),"w") as f:
  json.dump(hashes,f,indent=2,sort_keys=True); f.write("\n")

def row(scenario,algo,mode,version,run_class,semantic="measure"):
 scoped=mode in (25,26,27)
 return dict(run_id=f"{scenario}__{algo}__seed1",scenario=scenario,
  algorithm_name=algo,cbap_version=version,cc_mode=mode,
  scope_policy="SHARED_BATCH_OVERSUBSCRIPTION" if scoped else "ALWAYS",
  rate_floor_policy=1 if scoped else 0,delegation_policy="GUARDED" if mode==27 else "NONE",
  envelope_policy="PATH_MIN_PROPORTIONAL" if mode==27 else "NONE",
  base_cc="DCQCN" if mode in (21,26,27) else "N/A",control_epoch_ns=5000,
  stable_epochs_required=2,seed=1,run_class=run_class,semantic_case=semantic,
  git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip())

def write(path,rows):
 os.makedirs(os.path.dirname(path),exist_ok=True)
 with open(path,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main():
 for n,s in SOURCES.items(): copy_case(n,s)
 copy_parking("multi_bottleneck_parking_lot")
 copy_parking("no_incumbent")
 semantic=[
  row("fan64_msg4m_load80","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S1"),
  row("fan64_msg1m_load95","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S2"),
  row("incumbent_completion_post_handoff","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S3"),
  row("multi_bottleneck_parking_lot","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S4"),
  row("stale_feedback","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S5"),
  row("cap_bound_anti_windup","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S6"),
  row("no_incumbent","cbap_full_v15_guarded_delegation",27,"v1.5","semantic","S7"),
  row("fan64_msg1m_load80","cbap_full_v13_ratefloor_fix",25,"v1.3","semantic","S8"),
 ]
 write(os.path.join(ROOT,"configs","semantic_manifest.csv"),semantic)
 cases=["fan32_msg1m_load80","fan64_msg64k_load80","fan64_msg256k_load80",
        "fan64_msg1m_load80","fan64_msg4m_load80","fan64_msg1m_load95","fan64_msg4m_load95"]
 algos=[("dcqcn",1,"baseline"),("hpcc_int",3,"baseline"),("cbap_init_only",21,"v1"),
        ("cbap_full_v13_ratefloor_fix",25,"v1.3"),("cbap_full_v14_stable_handoff",26,"v1.4"),
        ("cbap_full_v15_guarded_delegation",27,"v1.5")]
 validation=[row(c,a,m,v,"validation") for c in cases for a,m,v in algos]
 write(os.path.join(ROOT,"configs","validation_manifest.csv"),validation)
 print(f"GENERATED semantic={len(semantic)} validation={len(validation)}")

if __name__=="__main__": main()
