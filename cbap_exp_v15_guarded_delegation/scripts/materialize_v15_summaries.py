#!/usr/bin/env python3
"""Create the v1.5 lightweight per-run audit contract from raw CSVs."""
import csv,json,math,os,statistics,sys

def read(p):
 return list(csv.DictReader(open(p))) if os.path.isfile(p) else []
def num(r,k):
 try:return float(r.get(k,0) or 0)
 except:return 0.0
def write(p,fields,rows):
 with open(p,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main(d):
 meta=json.load(open(os.path.join(d,"run_meta.json")))
 scenario=json.load(open(os.path.join(d,"scenario_meta.json")))
 incumbents=set(map(int,scenario.get("incumbent_flow_ids",[])))
 raw=read(os.path.join(d,"incumbent_progress.csv"))
 if not raw and incumbents:
  sizes={}
  with open(os.path.join(d,"flow.txt")) as f:
   next(f)
   for i,line in enumerate(f):
    p=line.split()
    if p:sizes[i]=int(p[4])
  samples=read(os.path.join(d,"selected_flow_timeseries.csv"))
  last={}
  for r in samples:
   fid=int(r["flow_id"])
   if fid in incumbents:last[fid]=r
  raw=[]
  for fid in sorted(incumbents):
   r=last.get(fid,{})
   ack=int(num(r,"snd_una")); size=sizes.get(fid,int(num(r,"released_bytes")))
   raw.append({"time_ns":int(num(r,"time")*1e9),"flow_id":fid,"batch_id":0,
    "size_bytes":size,"sent_bytes":int(num(r,"snd_nxt")),"acked_bytes":ack,
    "remaining_bytes":max(size-ack,0),"current_rate_bps":int(num(r,"current_rate")),
    "target_rate_bps":0,"protection_floor_bps":0,"time_below_90_target_ns":0,
    "time_below_80_target_ns":0,"time_below_50_target_ns":0,"finished":int(ack>=size)})
 inc=[]
 flow_completed={int(r["flow_id"]):r for r in read(os.path.join(d,"flow_summary.csv"))}
 for r in raw:
  if int(r["flow_id"]) not in incumbents: continue
  size=num(r,"size_bytes"); ack=num(r,"acked_bytes"); elapsed=max(num(r,"time_ns")*1e-9,1e-12)
  done=flow_completed.get(int(r["flow_id"]),{})
  inc.append(dict(r,delivered_bytes=int(ack),remaining_fraction=(size-ack)/size if size else 0,
                  average_goodput_bps=ack*8/elapsed,
                  completion_time_seconds=num(done,"finish_time") if done else 0))
 fields=list(inc[0]) if inc else ["flow_id","delivered_bytes","remaining_bytes","remaining_fraction","average_goodput_bps"]
 write(os.path.join(d,"incumbent_summary.csv"),fields,inc)
 links=read(os.path.join(d,"envelope_link_audit.csv"))
 env=[]
 grouped={}
 for r in links:
  key=(r.get("batch_id"),r.get("link_id")); grouped.setdefault(key,[]).append(r)
 for (batch,link),rs in sorted(grouped.items()):
  env.append({"batch_id":batch,"link_id":link,"epoch_count":len(rs),
   "maximum_desired_rate_sum_bps":max(num(x,"desired_rate_sum_bps") for x in rs),
   "maximum_applied_rate_sum_bps":max(num(x,"applied_rate_sum_bps") for x in rs),
   "minimum_batch_budget_bps":min(num(x,"batch_budget_bps") for x in rs),
   "maximum_incumbent_reserve_bps":max(num(x,"incumbent_reserve_bps") for x in rs),
   "capacity_violation_count":sum(str(x.get("envelope_capacity_violation","0")).lower() in ("1","true") for x in rs),
   "stale_epoch_count":sum(str(x.get("stale_feedback","0")).lower() in ("1","true") for x in rs)})
 write(os.path.join(d,"envelope_summary.csv"),["batch_id","link_id","epoch_count","maximum_desired_rate_sum_bps","maximum_applied_rate_sum_bps","minimum_batch_budget_bps","maximum_incumbent_reserve_bps","capacity_violation_count","stale_epoch_count"],env)
 ownership=os.path.join(d,"controller_ownership.csv")
 if not os.path.isfile(ownership):
  write(ownership,["time_ns","epoch","batch_id","flow_id","phase","owner","cbap_rate_update","dcqcn_rate_update"],[])
 result_path=os.path.join(d,"result.json")
 result=json.load(open(result_path)) if os.path.isfile(result_path) else {}
 flows=read(os.path.join(d,"flow_summary.csv")); progress=raw
 delivered=sum(num(r,"acknowledged_bytes") for r in flows)
 delivered+=sum(num(r,"acked_bytes") for r in progress if int(r["flow_id"]) in incumbents and not any(int(f["flow_id"])==int(r["flow_id"]) for f in flows))
 finish=[num(r,"finish_time") for r in flows if num(r,"finish_time")>0]
 stop=max([num(r,"time_ns")*1e-9 for r in progress]+finish+[0])
 starts=[num(r,"start_time") for r in flows if num(r,"start_time")>=0]
 begin=min(starts) if starts else 0
 pending=set(map(int,scenario.get("pending_flow_ids",[])))
 newcomer=[r for r in flows if int(r["flow_id"]) in pending]
 fcts=[num(r,"fct")*1e6 for r in newcomer]
 newcomer_delivered=sum(num(r,"acknowledged_bytes") for r in newcomer)
 newcomer_span=max([num(r,"finish_time") for r in newcomer]+[begin])-begin
 newcomer_goodput=newcomer_delivered*8/max(newcomer_span,1e-12)
 incumbent_delivered=sum(num(r,"delivered_bytes") for r in inc)
 incumbent_goodput=sum(num(r,"average_goodput_bps") for r in inc)
 fairness=(newcomer_goodput+incumbent_goodput)**2/(2*(newcomer_goodput**2+incumbent_goodput**2)) if newcomer_goodput or incumbent_goodput else 0
 offered_fraction=float(scenario.get("incumbent_offered_load_percent",0) or 0)/100
 target_bps=float(scenario.get("capacity_bps",100000000000))*offered_fraction
 worst_drop=max(0.0,(target_bps-incumbent_goodput)/target_bps) if target_bps else 0
 result.update(metric_scope="newcomer_and_incumbent",total_delivered_bytes=int(delivered),
  all_work_makespan_seconds=max(stop-begin,0),incumbent_flow_count=len(incumbents),
  incumbent_remaining_bytes=sum(int(num(r,"remaining_bytes")) for r in inc),
  incumbent_remaining_fraction=max([num(r,"remaining_fraction") for r in inc]+[0]),
  envelope_capacity_violation_rows=sum(x["capacity_violation_count"] for x in env),
  algorithm=meta.get("algorithm"),scenario=meta.get("scenario"),
  newcomer_batch_cct_us=max(fcts) if fcts else 0,
  newcomer_median_fct_us=statistics.median(fcts) if fcts else 0,
  newcomer_max_fct_us=max(fcts) if fcts else 0,
  newcomer_completion_skew_us=(max(fcts)-min(fcts)) if fcts else 0,
  newcomer_delivered_bytes=int(newcomer_delivered),
  newcomer_remaining_bytes=sum(max(int(num(r,"size_bytes")-num(r,"acknowledged_bytes")),0) for r in newcomer),
  incumbent_delivered_bytes=int(incumbent_delivered),
  incumbent_average_goodput_bps=incumbent_goodput,
  incumbent_worst_throughput_drop_fraction=worst_drop,
  incumbent_time_below_90_target_ns=sum(int(num(r,"time_below_90_target_ns")) for r in inc),
  incumbent_time_below_80_target_ns=sum(int(num(r,"time_below_80_target_ns")) for r in inc),
  incumbent_time_below_50_target_ns=sum(int(num(r,"time_below_50_target_ns")) for r in inc),
  total_goodput_bps=delivered*8/max(stop-begin,1e-12),
  incumbent_newcomer_jain_fairness=fairness)
 flow_audit=read(os.path.join(d,"envelope_flow_audit.csv"))
 result.update(
  logical_envelope_update_count=len(links),
  logical_envelope_control_bytes=len(links)*64,
  simulator_internal_rate_write_count=max([int(num(x,"simulator_internal_rate_write_count")) for x in flow_audit]+[0]),
  post_delegation_full_cbap_grant_count=max([int(num(x,"post_delegation_full_cbap_grant_count")) for x in flow_audit]+[0]),
  positive_ai_suppressed=max([int(num(x,"positive_ai_suppressed")) for x in flow_audit]+[0]),
  decrease_applied=max([int(num(x,"decrease_applied")) for x in flow_audit]+[0]))
 overhead=read(os.path.join(d,"cbap_control_overhead.csv"))
 if overhead:
  result["full_cbap_grant_count"]=int(num(overhead[0],"grant_messages"))
  result["total_control_bytes"]=int(num(overhead[0],"total_control_bytes"))
 with open(result_path,"w") as f:json.dump(result,f,indent=2,sort_keys=True);f.write("\n")

if __name__=="__main__":main(os.path.abspath(sys.argv[1]))
