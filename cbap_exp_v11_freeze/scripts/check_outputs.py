#!/usr/bin/env python3
import argparse,csv,gzip,json,math,os,sys

def exists(path):
 for p in (path,path+".gz"):
  if os.path.isfile(p) and os.path.getsize(p)>0:return p
 return ""
def rows(path):
 p=exists(path)
 if not p:return []
 op=gzip.open if p.endswith(".gz") else open
 with op(p,"rt",newline="") as f:return list(csv.DictReader(f))
def fail(x): print("INVALID "+x,file=sys.stderr); raise SystemExit(1)
def main():
 p=argparse.ArgumentParser(); p.add_argument("run_dir"); p.add_argument("--allow-no-complete-flag",action="store_true"); a=p.parse_args()
 d=os.path.abspath(a.run_dir)
 for name in ("run_meta.json","exit_status.txt","result.json","flow_summary.csv","round_summary.csv","queue_summary.csv","rate_summary.csv"):
  if not exists(os.path.join(d,name)):fail("missing "+name)
 if not a.allow_no_complete_flag and not os.path.isfile(os.path.join(d,"completed.flag")):fail("missing completed.flag")
 if int(open(os.path.join(d,"exit_status.txt")).read().strip()):fail("nonzero exit")
 meta=json.load(open(os.path.join(d,"run_meta.json"))); result=json.load(open(os.path.join(d,"result.json")))
 if not result.get("all_flows_completed"):fail("incomplete")
 if result.get("log_truncated") or meta.get("log_truncated"):fail("truncated")
 if any(isinstance(v,float) and not math.isfinite(v) for v in result.values()):fail("nonfinite")
 if meta.get("cbap_version") in ("v1","v1.1"):
  for name in ("cbap_flow_state.csv","cbap_rate_transitions.csv","cbap_tx_events.csv","increase_policy_events.csv"):
   if not exists(os.path.join(d,name)):fail("missing "+name)
  fields=set(rows(os.path.join(d,"increase_policy_events.csv"))[0]) if rows(os.path.join(d,"increase_policy_events.csv")) else set()
  required={"current_rate_before_bps","target_rate_bps","fractional_candidate_bps","absolute_candidate_bps","selected_delta_bps","new_rate_bps","phase","stale_feedback"}
  # Empty is valid when a workload performs no increase, but a non-empty file must carry the schema.
  header=open(os.path.join(d,"increase_policy_events.csv")).readline().strip().split(',')
  if not required.issubset(header):fail("increase audit schema")
 print("VALID "+d)
if __name__=="__main__":main()
