#!/usr/bin/env python3
"""Offline reprocessing for immutable v13/v14/v15 completed runs."""
import csv,glob,json,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from collect_full_work_metrics import collect

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
PIPE=os.path.join(ROOT,"cbap_final_metric_pipeline")
EXPERIMENTS=("cbap_exp_v13_ratefloor_fix","cbap_exp_v14_stable_handoff","cbap_exp_v15_guarded_delegation")

def write_csv(path,rows,preferred=None):
 os.makedirs(os.path.dirname(path),exist_ok=True)
 fields=list(preferred or [])
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 if not fields: fields=["source_run"]
 with open(path,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

def discover():
 out=[]
 for exp in EXPERIMENTS:
  base=os.path.join(ROOT,exp)
  for flag in glob.glob(os.path.join(base,"runs*","**","completed.flag"),recursive=True):
   run=os.path.dirname(flag);out.append((exp,run,os.path.relpath(run,base)))
 return sorted(out,key=lambda x:(x[0],x[2]))

def main():
 summaries=[];flows=[];unresolved=[];suspicious=[];failures=[];old_compare=[]
 discovered=discover()
 for index,(exp,run,relative) in enumerate(discovered,1):
  out=os.path.join(PIPE,"recomputed",exp,relative)
  try:
   result,ledger,prov=collect(run,out)
  except Exception as e:
   failures.append({"source_experiment":exp,"relative_run_path":relative,"source_run":run,"error":repr(e)})
   continue
  row={"source_experiment":exp,"relative_run_path":relative,**result};summaries.append(row)
  for x in ledger: flows.append({"source_experiment":exp,"relative_run_path":relative,"scenario":result.get("scenario"),"algorithm":result.get("algorithm"),**x})
  for finding in result.get("unresolved_fields",[]): unresolved.append({"source_experiment":exp,"relative_run_path":relative,"finding":finding})
  for finding in result.get("suspicious_findings",[]): suspicious.append({"source_experiment":exp,"relative_run_path":relative,"finding":finding})
  old_path=os.path.join(run,"result.json")
  old=json.load(open(old_path)) if os.path.isfile(old_path) else {}
  old_compare.append({"source_experiment":exp,"relative_run_path":relative,"scenario":result.get("scenario"),"algorithm":result.get("algorithm"),
   "old_all_flows_completed":old.get("all_flows_completed"),"corrected_all_flows_completed":result.get("all_flows_completed"),
   "old_all_work_makespan_seconds":old.get("all_work_makespan_seconds"),"corrected_all_work_makespan_us":result.get("all_work_makespan_us"),
   "old_total_delivered_bytes":old.get("total_delivered_bytes"),"corrected_total_delivered_bytes":result.get("total_delivered_bytes"),
   "old_queue_auc_byte_seconds":old.get("queue_auc_byte_seconds"),"corrected_queue_auc_byte_seconds":result.get("queue_auc_byte_seconds")})
  if index%20==0: print("REPROCESSED %d/%d"%(index,len(discovered)))
 processed=os.path.join(PIPE,"processed")
 write_csv(os.path.join(processed,"corrected_summary_by_run.csv"),summaries,["source_experiment","relative_run_path","scenario","algorithm","seed"])
 write_csv(os.path.join(processed,"corrected_flow_outcomes.csv"),flows,["source_experiment","relative_run_path","scenario","algorithm","flow_id","role"])
 groups={
  "corrected_completion_metrics.csv":["newcomer_","incumbent_","total_","all_","completed_","last_completed_","censored_","observation_"],
  "corrected_queue_metrics.csv":["queue_","time_above_"],
  "corrected_utilization_metrics.csv":["utilization_"],
  "corrected_control_metrics.csv":["logical_control_","monitoring_only_","simulator_internal_","control_"]}
 identity=("source_experiment","relative_run_path","scenario","algorithm","seed")
 for filename,prefixes in groups.items():
  subset=[]
  for r in summaries:
   subset.append({k:v for k,v in r.items() if k in identity or any(k.startswith(p) for p in prefixes)})
  write_csv(os.path.join(processed,filename),subset,list(identity))
 write_csv(os.path.join(processed,"unresolved_runs.csv"),unresolved,["source_experiment","relative_run_path","finding"])
 write_csv(os.path.join(processed,"suspicious_runs.csv"),suspicious,["source_experiment","relative_run_path","finding"])
 write_csv(os.path.join(processed,"collector_failures.csv"),failures,["source_experiment","relative_run_path","source_run","error"])
 write_csv(os.path.join(processed,"old_vs_corrected.csv"),old_compare)
 manifest=[{"source_experiment":e,"relative_run_path":r,"source_run":p,"reprocessed":not any(x["source_run"]==p for x in failures)} for e,p,r in discovered]
 write_csv(os.path.join(processed,"reprocessed_manifest.csv"),manifest)
 print("REPROCESS_COMPLETE discovered=%d succeeded=%d failures=%d unresolved=%d suspicious=%d"%(len(discovered),len(summaries),len(failures),len(unresolved),len(suspicious)))
 return 0 if len(summaries)==len(discovered) else 1

if __name__=="__main__": raise SystemExit(main())
