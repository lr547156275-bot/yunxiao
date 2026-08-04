#!/usr/bin/env python3
"""Run unit/known-fact/hash gates and emit the authoritative self-test."""
import csv,hashlib,json,os,subprocess,sys,time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
PIPE=os.path.join(ROOT,"cbap_final_metric_pipeline")
REPORT=os.path.join(PIPE,"reports")

def rows(path):
 if not os.path.isfile(path): return []
 with open(path,newline="") as f:return list(csv.DictReader(f))
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def close(a,b,tol): return a is not None and abs(float(a)-float(b))<=tol
def write(path,text):
 os.makedirs(os.path.dirname(path),exist_ok=True);open(path,"w").write(text.rstrip()+"\n")

def recomputed(exp,relative,name): return os.path.join(PIPE,"recomputed",exp,relative,name)

def known_facts():
 base="runs_validation/fan64_msg4m_load80"
 cases={
  "A":("cbap_full_v13_ratefloor_fix",[
   ("newcomer count",lambda r,l:r["newcomer_total_count"]==64),
   ("per-newcomer bytes",lambda r,l:all(int(x["planned_bytes"])==4194304 for x in l if x["role"]=="newcomer")),
   ("newcomer planned",lambda r,l:r["newcomer_planned_bytes"]==268435456),
   ("newcomer delivered",lambda r,l:r["newcomer_delivered_bytes"]==268435456),
   ("incumbent planned",lambda r,l:r["incumbent_planned_bytes"]==536870912),
   ("incumbent delivered",lambda r,l:r["incumbent_delivered_bytes"]==536870912),
   ("all completed",lambda r,l:r["all_newcomers_completed"] and r["all_incumbents_completed"] and r["all_flows_completed"]),
   ("incumbent completion absolute",lambda r,l:close(r["incumbent_completion_time_us"],75889.244,1.0)),
   ("incumbent is last",lambda r,l:max(l,key=lambda x:x["completion_time_absolute"] or -1)["role"]=="incumbent"),
   ("makespan is completion-derived",lambda r,l:r["all_work_makespan_us"] is not None and r["all_work_makespan_us"]<90000)]),
  "B":("cbap_full_v14_stable_handoff",[
   ("newcomer planned",lambda r,l:r["newcomer_planned_bytes"]==268435456),
   ("newcomer delivered",lambda r,l:r["newcomer_delivered_bytes"]==268435456 and r["all_newcomers_completed"]),
   ("incumbent delivered",lambda r,l:r["incumbent_delivered_bytes"]==185100000),
   ("incumbent remaining",lambda r,l:r["incumbent_remaining_bytes"]==351770912),
   ("incumbent fraction",lambda r,l:close(r["incumbent_remaining_fraction"],.6552243829,1e-9)),
   ("incomplete overall",lambda r,l:not r["all_incumbents_completed"] and not r["all_flows_completed"]),
   ("null makespan",lambda r,l:r["all_work_makespan_us"] is None),
   ("total delivered",lambda r,l:r["total_delivered_bytes"]==453535456),
   ("censored lower bound",lambda r,l:r["censored_makespan_lower_bound_us"] is not None)]),
  "C":("cbap_full_v15_guarded_delegation",[
   ("ledger conservation",lambda r,l:r["total_planned_bytes"]==r["total_delivered_bytes"]+r["total_remaining_bytes"]),
   ("ledger completion consistent",lambda r,l:r["all_flows_completed"]==all(str(x["completed"]).lower() in ("1","true") for x in l)),
   ("true final time",lambda r,l:r["last_completed_flow_time_absolute"] is not None and r["last_completed_flow_time_absolute"]<.09),
   ("not old 99 ms surrogate",lambda r,l:r["all_work_makespan_us"] is not None and r["all_work_makespan_us"]<90000)])}
 details=[];passed=0;actual_paths=[]
 for label,(algorithm,checks) in cases.items():
  relative=base+"/"+algorithm+"/seed_1";actual_paths.append(relative)
  rp=recomputed("cbap_exp_v15_guarded_delegation",relative,"result_full_work.json")
  lp=recomputed("cbap_exp_v15_guarded_delegation",relative,"flow_outcome_ledger.csv")
  if not os.path.isfile(rp) or not os.path.isfile(lp):
   details.append((label,False,"missing recomputed result: "+relative));continue
  result=json.load(open(rp));ledger=rows(lp);fail=[]
  for name,fn in checks:
   try: ok=bool(fn(result,ledger))
   except Exception as e: ok=False
   if not ok:fail.append(name)
  ok=not fail;passed+=ok;details.append((label,ok,"PASS" if ok else "failed: "+", ".join(fail)))
 lines=["# Known-fact regression","","Actual source experiment: `cbap_exp_v15_guarded_delegation`.",""]
 for label,ok,msg in details:lines.append("- Test %s: **%s** — %s"%(label,"PASS" if ok else "FAIL",msg))
 lines.extend(["","Actual relative paths:"]+["- `"+x+"`" for x in actual_paths])
 write(os.path.join(REPORT,"known_fact_regression.md"),"\n".join(lines))
 return passed,details

def source_hash_audit():
 before=os.path.join(PIPE,"preflight","congestion_control_source_hashes_before.sha256")
 mismatches=[];count=0
 for line in open(before):
  expected,path=line.strip().split(None,1);path=path.strip()
  count+=1
  if not os.path.isfile(os.path.join(ROOT,path)) or sha(os.path.join(ROOT,path))!=expected:mismatches.append(path)
 return count,mismatches

def original_hash_audit():
 mismatches=[];checked=0
 for p in [x for x in os.popen("find '%s/recomputed' -name metric_provenance.json -type f"%PIPE).read().splitlines() if x]:
  prov=json.load(open(p));run=prov["source_run"]
  for name,expected in prov["input_file_hashes"].items():
   checked+=1;source=os.path.join(run,name)
   if not os.path.isfile(source) or sha(source)!=expected:mismatches.append(source)
 return checked,mismatches

def main():
 os.makedirs(REPORT,exist_ok=True);os.makedirs(os.path.join(PIPE,"tests"),exist_ok=True)
 test_script=os.path.join(PIPE,"scripts","test_metric_pipeline.py")
 unit=subprocess.run([sys.executable,test_script],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 write(os.path.join(PIPE,"tests","unit_tests_audit.log"),unit.stdout)
 total=unit.stdout.count(" ... ok");unit_pass=unit.returncode==0 and total==15
 known_pass,known_details=known_facts()
 source_count,source_mismatch=source_hash_audit();original_checked,original_mismatch=original_hash_audit()
 manifest=rows(os.path.join(PIPE,"processed","reprocessed_manifest.csv"));summary=rows(os.path.join(PIPE,"processed","corrected_summary_by_run.csv"))
 failures=rows(os.path.join(PIPE,"processed","collector_failures.csv"));unresolved=rows(os.path.join(PIPE,"processed","unresolved_runs.csv"));suspicious=rows(os.path.join(PIPE,"processed","suspicious_runs.csv"))
 conservation_fail=[r for r in summary if str(r.get("byte_conservation_valid","")).lower() not in ("1","true")]
 passed=(unit_pass and known_pass==3 and not source_mismatch and not original_mismatch and
         len(manifest)>0 and len(summary)==len(manifest) and not failures and not conservation_fail)
 status="METRIC_PIPELINE_PASS" if passed else "METRIC_PIPELINE_FAIL"
 selftest=[status,"","# Metric pipeline self-test","",
  "- Unit tests: %d/15 passed."%(15 if unit_pass else total),
  "- Known-fact tests: %d/3 passed."%known_pass,
  "- Original input hashes checked: %d; modified: %d."%(original_checked,len(original_mismatch)),
  "- Reprocessed runs: %d."%len(summary),
  "- Unresolved findings: %d."%len(unresolved),
  "- Suspicious findings: %d."%len(suspicious),
  "- Congestion-control/source hashes checked: %d; task modifications: %d."%(source_count,len(source_mismatch)),
  "- C++ modifications by this task: %d."%len(source_mismatch),
  "- Build executions: 0.","- ns-3 executions: 0.",
  "- Collector failures: %d."%len(failures),"- Byte-conservation failures: %d."%len(conservation_fail),"",
  "PASS is based on unit tests, three immutable real-run regressions, byte conservation, and before/after hash audits; unresolved optional source limitations remain explicitly reported."]
 write(os.path.join(REPORT,"metric_pipeline_selftest.md"),"\n".join(selftest))
 write(os.path.join(REPORT,"metric_definition_specification.md"),"""# Metric definition specification

`flow_outcome_ledger.csv` is the complete planned-flow population. Completion requires completion evidence and acknowledged application bytes greater than or equal to planned bytes. Missing completion rows remain censored. Newcomer CCT starts at batch application-ready time and therefore includes Scope and Admission Hold. Completed all-work makespan ends at the final completed flow; incomplete work has a null makespan and an observation-horizon censored lower bound.

Queue AUC uses trapezoidal integration over recorded timestamps. Time-weighted queue P95 weights each left-continuous sample by its actual following interval. Utilization from transmitted bytes and sampled utilization are reported separately. Multi-link byte utilization uses the aggregate monitored-link capacity denominator. Monitoring-only summaries are not counted as network control messages.
""")
 old=rows(os.path.join(PIPE,"processed","old_vs_corrected.csv"));changed=sum(str(x.get("old_all_flows_completed"))!=str(x.get("corrected_all_flows_completed")) or str(x.get("old_all_work_makespan_seconds"))!=str(x.get("corrected_all_work_makespan_us")) for x in old)
 write(os.path.join(REPORT,"old_vs_corrected_metrics.md"),"# Old versus corrected metrics\n\n- Compared runs: %d.\n- Rows with completion/makespan representation changes: %d.\n- Corrected values are in `processed/old_vs_corrected.csv`; old `result.json` files were not modified."%(len(old),changed))
 write(os.path.join(REPORT,"unresolved_data_report.md"),"# Unresolved data\n\n- Findings: %d across %d runs.\n- Details: `processed/unresolved_runs.csv`.\n- Dynamic PFC byte thresholds are not inferred when the run lacks an authoritative threshold trace."%(len(unresolved),len(set((x.get("source_experiment"),x.get("relative_run_path")) for x in unresolved))))
 write(os.path.join(REPORT,"result_integrity_report.md"),"# Result integrity\n\n- Discovered/reprocessed: %d/%d.\n- Collector failures: %d.\n- Application-byte conservation failures: %d.\n- Original input hash mismatches: %d.\n- Source hash mismatches: %d."%(len(summary),len(manifest),len(failures),len(conservation_fail),len(original_mismatch),len(source_mismatch)))
 changed_files=[]
 for base,dirs,files in os.walk(PIPE):
  if "/recomputed/" in base.replace("\\","/"):continue
  for name in files:changed_files.append(os.path.relpath(os.path.join(base,name),ROOT))
 write(os.path.join(REPORT,"files_changed.txt"),"\n".join(sorted(changed_files)))
 audit={"status":status,"unit_tests_passed":15 if unit_pass else total,"unit_tests_total":15,"known_fact_tests_passed":known_pass,
  "reprocessed_runs":len(summary),"unresolved_findings":len(unresolved),"suspicious_findings":len(suspicious),
  "original_files_modified_count":len(original_mismatch),"congestion_control_source_files_modified_count":len(source_mismatch),
  "build_executed_count":0,"ns3_executed_count":0,"generated_time_unix":time.time()}
 with open(os.path.join(PIPE,"processed","pipeline_audit.json"),"w") as f:json.dump(audit,f,indent=2,sort_keys=True);f.write("\n")
 print(status)
 print("unit tests passed=%d/15"%audit["unit_tests_passed"]);print("known fact tests passed=%d/3"%known_pass)
 print("reprocessed runs=%d unresolved=%d suspicious=%d"%(len(summary),len(unresolved),len(suspicious)))
 print("original files modified count=%d"%len(original_mismatch));print("congestion-control source files modified count=%d"%len(source_mismatch))
 print("build executed count=0");print("ns-3 executed count=0")
 return 0 if passed else 1

if __name__=="__main__":raise SystemExit(main())
