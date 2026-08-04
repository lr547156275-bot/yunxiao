#!/usr/bin/env python3
import csv,json,os,sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
def rows(p): return list(csv.DictReader(open(p))) if os.path.isfile(p) else []
def truth(v): return str(v).lower() in ("1","true","yes")
manifest=list(csv.DictReader(open(os.path.join(ROOT,"configs","semantic_manifest.csv"))))
issues=[]; checked=[]
for m in manifest:
 d=os.path.join(ROOT,"runs_semantic",m["scenario"],m["algorithm_name"],"seed_1")
 result=os.path.join(d,"result.json")
 if not os.path.isfile(result): issues.append(m["run_id"]+": missing result.json"); continue
 r=json.load(open(result)); checked.append(m["run_id"])
 if not r.get("all_pending_flows_completed",r.get("all_flows_completed",False)): issues.append(m["run_id"]+": newcomer incomplete")
 if int(m["cc_mode"])!=27: continue
 link=rows(os.path.join(d,"envelope_link_audit.csv")); flow=rows(os.path.join(d,"envelope_flow_audit.csv"))
 hand=rows(os.path.join(d,"cbap_handoff_summary.csv")); own=rows(os.path.join(d,"controller_ownership.csv"))
 if not link or not flow:
  reason=hand[0].get("no_handoff_reason","unknown") if hand else "missing_handoff_summary"
  stable=hand[0].get("stable_epoch_count","unknown") if hand else "unknown"
  issues.append(m["run_id"]+": no delegated envelope audit (reason=%s, stable_epochs=%s)"%(reason,stable))
  continue
 if any(truth(x.get("envelope_capacity_violation")) for x in link): issues.append(m["run_id"]+": capacity violation")
 if any(float(x["batch_budget_bps"])+float(x["incumbent_reserve_bps"])>float(x["C_effective_bps"])+max(1,1e-9*float(x["C_effective_bps"])) for x in link): issues.append(m["run_id"]+": reserve budget violation")
 if any(float(x["applied_rate_bps"])>float(x["desired_rate_bps"])+1 for x in flow): issues.append(m["run_id"]+": applied exceeds desired")
 if any(x.get("desired_writer")!="DCQCN" or x.get("applied_writer")!="ENVELOPE_PROJECTOR" for x in flow): issues.append(m["run_id"]+": ownership conflict")
 if any(x.get("owner")=="CBAP" and int(x.get("phase",0))==8 for x in own): issues.append(m["run_id"]+": full CBAP wrote delegated flow")
 if sum(truth(x.get("handoff_occurred")) for x in hand)!=1: issues.append(m["run_id"]+": delegation count != 1")
 if m["semantic_case"]=="S2" and max(float(x["incumbent_reserve_bps"]) for x in link)<=0: issues.append(m["run_id"]+": incumbent reserve absent")
 if m["semantic_case"]=="S3":
  if sum(truth(x.get("handoff_occurred")) for x in hand)!=1:
   issues.append(m["run_id"]+": S3 did not delegate exactly once")
  else:
   execute_ns=int(float(hand[0]["handoff_execute_ns"]))
   summaries=rows(os.path.join(d,"incumbent_summary.csv"))
   completed=[x for x in summaries if truth(x.get("finished")) and float(x.get("completion_time_seconds",0) or 0)>0]
   if not completed:
    issues.append(m["run_id"]+": incumbent did not complete")
   else:
    incumbent_finish_ns=min(int(round(float(x["completion_time_seconds"])*1e9)) for x in completed)
    if incumbent_finish_ns<=execute_ns:
     issues.append(m["run_id"]+": incumbent completed before delegation")
    release_rows=[x for x in link if int(float(x["epoch_ns"]))>=incumbent_finish_ns]
    before_rows=[x for x in link if int(float(x["epoch_ns"]))<incumbent_finish_ns]
    if not before_rows or not release_rows:
     issues.append(m["run_id"]+": no pre/post incumbent-completion envelope window")
    elif max(float(x["incumbent_reserve_bps"]) for x in before_rows)<=min(float(x["incumbent_reserve_bps"]) for x in release_rows):
     issues.append(m["run_id"]+": reserve did not release after incumbent completion")
    elif max(float(x["batch_budget_bps"]) for x in release_rows)<=min(float(x["batch_budget_bps"]) for x in before_rows):
     issues.append(m["run_id"]+": batch budget did not expand after reserve release")
 if m["semantic_case"]=="S4" and len(set(x["link_id"] for x in link))<2: issues.append(m["run_id"]+": not multi-link")
 if m["semantic_case"]=="S5" and not any(truth(x["stale_feedback"]) for x in link): issues.append(m["run_id"]+": stale case produced no stale epoch")
 if m["semantic_case"]=="S6" and max(float(x["positive_ai_suppressed"]) for x in flow)<=0: issues.append(m["run_id"]+": anti-windup not exercised")
 if m["semantic_case"]=="S7" and any(float(x["incumbent_reserve_bps"])!=0 for x in link): issues.append(m["run_id"]+": no-incumbent reserve nonzero")
status="GUARDED_SEMANTIC_PASS" if len(checked)==8 and not issues else "GUARDED_SEMANTIC_FAIL"
os.makedirs(os.path.join(ROOT,"reports"),exist_ok=True)
with open(os.path.join(ROOT,"reports","guarded_semantic_report.md"),"w") as f:
 f.write(status+"\n\n# Guarded delegation semantic verification\n\n")
 f.write(f"Reused real runs: {len(checked)}/8. No missing result is imputed.\n\n")
 f.write("## Findings\n\n"+("- All preregistered hard checks passed.\n" if not issues else "".join("- "+x+"\n" for x in issues)))
print(status); print("checked=%d issues=%d"%(len(checked),len(issues)))
sys.exit(0 if status.endswith("PASS") else 1)
