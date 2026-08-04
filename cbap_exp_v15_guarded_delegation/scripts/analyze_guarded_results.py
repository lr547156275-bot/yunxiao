#!/usr/bin/env python3
import csv,json,os,statistics
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
manifest=list(csv.DictReader(open(os.path.join(ROOT,"configs","validation_manifest.csv"))))
records=[]; suspicious=[]
for m in manifest:
 d=os.path.join(ROOT,"runs_validation",m["scenario"],m["algorithm_name"],"seed_1")
 p=os.path.join(d,"result.json")
 if not os.path.isfile(p): suspicious.append(m["run_id"]+": missing result.json"); continue
 r=json.load(open(p)); records.append({**m,**r})
 if not r.get("all_pending_flows_completed",False): suspicious.append(m["run_id"]+": pending incomplete")
 if int(r.get("envelope_capacity_violation_rows",0)): suspicious.append(m["run_id"]+": envelope violation")
fields=sorted(set().union(*(r.keys() for r in records))) if records else list(manifest[0])
os.makedirs(os.path.join(ROOT,"processed"),exist_ok=True)
with open(os.path.join(ROOT,"processed","summary_by_run.csv"),"w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(records)
by={(r["scenario"],r["algorithm_name"]):r for r in records}
paired=[]
for s in sorted(set(m["scenario"] for m in manifest)):
 base=by.get((s,"cbap_full_v13_ratefloor_fix"));
 for a in ("cbap_full_v14_stable_handoff","cbap_full_v15_guarded_delegation"):
  new=by.get((s,a))
  if not base or not new: continue
  row={"scenario":s,"algorithm":a}
  for k in ("group_rct_max_us","queue_max_bytes","queue_auc_byte_seconds","incumbent_remaining_bytes","all_work_makespan_seconds"):
   b=float(base.get(k,0) or 0); n=float(new.get(k,0) or 0); row[k+"__pct"]=(n-b)/b*100 if b else ""
  paired.append(row)
with open(os.path.join(ROOT,"processed","paired_v13_v14_v15.csv"),"w",newline="") as f:
 fields=list(paired[0]) if paired else ["scenario","algorithm"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(paired)
def aggregate_csv(target,source):
 """Merge detailed audits without retaining millions of rows in memory."""
 inputs=[]; fields=["scenario","algorithm"]
 for m in manifest:
  p=os.path.join(ROOT,"runs_validation",m["scenario"],m["algorithm_name"],"seed_1",source)
  if not os.path.isfile(p): continue
  with open(p,newline="") as f:
   header=csv.DictReader(f).fieldnames or []
  for name in header:
   if name not in fields: fields.append(name)
  inputs.append((m,p))
 with open(os.path.join(ROOT,"processed",target),"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader()
  for m,p in inputs:
   with open(p,newline="") as source_file:
    for r in csv.DictReader(source_file):
     r.update(scenario=m["scenario"],algorithm=m["algorithm_name"])
     w.writerow(r)

for target,source in (("envelope_link_audit.csv","envelope_link_audit.csv"),("envelope_flow_audit.csv","envelope_flow_audit.csv"),("controller_ownership_audit.csv","controller_ownership.csv"),("incumbent_progress_audit.csv","incumbent_summary.csv")):
 aggregate_csv(target,source)
for name in ("makespan_audit.csv","control_overhead_audit.csv"):
 with open(os.path.join(ROOT,"processed",name),"w",newline="") as f:
  fs=["scenario","algorithm","all_work_makespan_seconds","total_delivered_bytes"] if name.startswith("makespan") else ["scenario","algorithm","total_control_bytes"]
  w=csv.DictWriter(f,fieldnames=fs);w.writeheader()
  for r in records:w.writerow({k:r.get(k,"") for k in fs})
decision="INVALID_EXPERIMENT"
gates=[]
if len(records)==42:
 v15=[r for r in records if r["algorithm_name"]=="cbap_full_v15_guarded_delegation"]
 for r in v15:
  for k in ("capacity_violations","credit_violations","pacing_violations",
            "applied_capacity_violation_rows","envelope_capacity_violation_rows",
            "post_delegation_full_cbap_grant_count"):
   if float(r.get(k,0) or 0)!=0:gates.append(r["scenario"]+": "+k)
 if gates: decision="INVALID_GUARDED_IMPLEMENTATION"
 else:
  failures=[]
  def metric(s,a,k): return float(by[(s,a)].get(k,0) or 0)
  def at_most(s,k,factor,base="cbap_full_v13_ratefloor_fix"):
   b=metric(s,base,k); n=metric(s,"cbap_full_v15_guarded_delegation",k)
   return b>0 and n<=factor*b
  s="fan64_msg4m_load80"
  for k,factor in (("group_rct_max_us",.90),("queue_max_bytes",1.25),("queue_auc_byte_seconds",1.25),("all_work_makespan_seconds",1.05)):
   if not at_most(s,k,factor):failures.append(s+": "+k)
  if metric(s,"cbap_full_v15_guarded_delegation","incumbent_remaining_fraction")>.05:failures.append(s+": incumbent remaining")
  v14rem=metric(s,"cbap_full_v14_stable_handoff","incumbent_remaining_bytes")
  if v14rem and metric(s,"cbap_full_v15_guarded_delegation","incumbent_remaining_bytes")>.20*v14rem:failures.append(s+": v14 incumbent reduction")
  for s in ("fan64_msg256k_load80","fan64_msg1m_load80"):
   for k,factor in (("group_rct_max_us",1.03),("queue_max_bytes",1.20),("queue_auc_byte_seconds",1.20),("all_work_makespan_seconds",1.05)):
    if not at_most(s,k,factor):failures.append(s+": "+k)
  if not at_most("fan64_msg64k_load80","group_rct_max_us",1.03):failures.append("64KiB CCT")
  for k,f in (("group_rct_max_us",1.03),("queue_max_bytes",1.10),("queue_auc_byte_seconds",1.10)):
   if not at_most("fan32_msg1m_load80",k,f):failures.append("fan32: "+k)
  for s in ("fan64_msg1m_load95","fan64_msg4m_load95"):
   if metric(s,"cbap_full_v15_guarded_delegation","incumbent_remaining_fraction")>.10:failures.append(s+": incumbent starvation")
  v13grants=metric("fan64_msg4m_load80","cbap_full_v13_ratefloor_fix","full_cbap_grant_count")
  if v13grants and metric("fan64_msg4m_load80","cbap_full_v15_guarded_delegation","full_cbap_grant_count")>.70*v13grants:failures.append("control grant reduction")
  decision="GUARDED_DELEGATION_VALID" if not failures else ("GUARDED_DELEGATION_VALID_WITH_LIMITATIONS" if len(failures)<=2 else "GUARDED_DELEGATION_NOT_USEFUL")
  suspicious.extend("preregistered gate: "+x for x in failures)
with open(os.path.join(ROOT,"processed","suspicious_runs.csv"),"w",newline="") as f:
 w=csv.writer(f);w.writerow(["finding"]);w.writerows([[x] for x in suspicious])
with open(os.path.join(ROOT,"reports","final_guarded_analysis.md"),"w") as f:
 f.write("# CBAP-v1.5 preregistered analysis\n\nDecision: **%s**\n\nRuns: %d/42. This mechanism-level report does not claim a paper result.\n"%(decision,len(records)))
print(decision,"runs=%d/42"%len(records))
