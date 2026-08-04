#!/usr/bin/env python3
"""Recompute full-work metrics from immutable ns-3 run artifacts."""
import argparse,csv,gzip,hashlib,json,math,os,statistics,time

COLLECTOR_VERSION="cbap_full_work_collector_v2_audit_files"
DEFINITIONS_VERSION="cbap_full_work_metrics_v1"

def num(v,default=0.0):
 try: return float(v)
 except (TypeError,ValueError): return default
def integer(v,default=0):
 try: return int(float(v))
 except (TypeError,ValueError): return default
def truth(v): return str(v).strip().lower() in ("1","true","yes","y")
def finite(v): return isinstance(v,(int,float)) and math.isfinite(v)

def read_json(path):
 if not os.path.isfile(path): return {}
 with open(path,errors="replace") as f: return json.load(f)

def open_text(path):
 return gzip.open(path,"rt",newline="",errors="replace") if path.endswith(".gz") else open(path,newline="",errors="replace")

def read_rows(path):
 if not path or not os.path.isfile(path): return []
 with open_text(path) as f: return list(csv.DictReader(f))

def summarize_applied_audit(path):
 violations=0; maximum=0.0
 if not path or not os.path.isfile(path): return violations,maximum
 with open_text(path) as f:
  for row in csv.DictReader(f):
   if integer(row.get("applied_capacity_violation",0)) != 0:
    violations+=1
   maximum=max(maximum,num(row.get("applied_capacity_excess_bps"),0))
 return violations,maximum

def locate(run,names):
 for name in names:
  p=os.path.join(run,name)
  if os.path.isfile(p): return p
 return None

def sha256(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for block in iter(lambda:f.read(1<<20),b""): h.update(block)
 return h.hexdigest()

def parse_config(path):
 out={}
 if not path or not os.path.isfile(path): return out
 for line in open(path,errors="replace"):
  words=line.split()
  if words and not words[0].startswith("#"): out[words[0]]=" ".join(words[1:])
 return out

def parse_bps(value,default=100000000000.0):
 text=str(value or "").strip().lower()
 scales=(("gbps",1e9),("mbps",1e6),("kbps",1e3),("bps",1.0))
 for suffix,scale in scales:
  if text.endswith(suffix): return num(text[:-len(suffix)],default/scale)*scale
 return num(text,default)

def parse_ecn_threshold_bytes(config,capacity_bps):
 words=str(config.get("KMIN_MAP","")).split()
 if len(words)%2==1 and integer(words[0],-1)==(len(words)-1)//2: words=words[1:]
 for i in range(0,len(words)-1,2):
  if integer(words[i])==int(capacity_bps): return integer(words[i+1])*1000
 return None

def parse_flow_txt(path):
 out={}
 if not path or not os.path.isfile(path): return out
 lines=[x.split() for x in open(path,errors="replace") if x.split()]
 for fid,w in enumerate(lines[1:]):
  if len(w)>=6:
   out[fid]={"source":integer(w[0]),"destination":integer(w[1]),
             "planned_bytes":integer(w[4]),"input_start_time":num(w[5])}
 return out

def weighted_quantile(samples,q):
 # samples are (value, duration_seconds).
 good=sorted((v,w) for v,w in samples if finite(v) and finite(w) and w>0)
 total=sum(w for _,w in good)
 if not good or total<=0: return None
 target=q*total; seen=0.0
 for value,weight in good:
  seen+=weight
  if seen>=target: return value
 return good[-1][0]

def integrate_window(points,start,end,value_key):
 if end is None or start is None or end<=start or len(points)<2: return None
 area=0.0; covered=0.0
 for a,b in zip(points,points[1:]):
  ta,tb=a["time"],b["time"]
  lo=max(ta,start); hi=min(tb,end)
  if hi<=lo or tb<=ta: continue
  va=num(a.get(value_key)); vb=num(b.get(value_key))
  frac0=(lo-ta)/(tb-ta); frac1=(hi-ta)/(tb-ta)
  vlo=va+(vb-va)*frac0; vhi=va+(vb-va)*frac1
  area+=0.5*(vlo+vhi)*(hi-lo); covered+=hi-lo
 return area/covered if covered>0 else None

def duration_above(a,b,threshold):
 dt=b["time"]-a["time"]
 if dt<=0:return 0.0
 qa,qb=a["queue"],b["queue"]
 if qa>threshold and qb>threshold:return dt
 if qa<=threshold and qb<=threshold:return 0.0
 if qa==qb:return 0.0
 crossing=a["time"]+(threshold-qa)/(qb-qa)*dt
 return b["time"]-crossing if qb>threshold else crossing-a["time"]

def queue_and_utilization(run,capacity_bps,ecn_threshold,windows,suspicious,unresolved):
 p=locate(run,("selected_link_timeseries.csv","selected_link_timeseries.csv.gz",
               "queue_timeseries.csv","queue_timeseries.csv.gz"))
 result={"queue_peak_bytes":None,"queue_auc_byte_seconds":None,
         "queue_auc_byte_us":None,"queue_p95_time_weighted_bytes":None,
         "time_above_ecn_threshold_us":None,"time_above_pfc_threshold_us":None,
         "utilization_full_simulation":None,"utilization_active_window":None,
         "utilization_newcomer_window":None,"utilization_all_work_window":None,
         "utilization_sampled_full_simulation":None,
         "ecn_threshold_bytes":ecn_threshold,"pfc_threshold_bytes":None,
         "queue_timeseries_source":os.path.basename(p) if p else None}
 if not p:
  unresolved.append("missing_queue_timeseries"); return result
 rows=read_rows(p); by_link={}
 for r in rows:
  t=num(r.get("time",r.get("time_seconds",None)),None)
  if t is None and r.get("time_ns") is not None: t=num(r["time_ns"])*1e-9
  if t is None: continue
  link=str(r.get("link_id","single_bottleneck"))
  by_link.setdefault(link,[]).append({"time":t,"queue":num(r.get("queue_bytes")),
   "util":num(r.get("utilization"),None),"tx":num(r.get("tx_bytes_delta")),
   "ecn":num(r.get("ecn_marks_delta")),"pfc":num(r.get("pfc_event_delta"))})
 if not by_link:
  unresolved.append("empty_queue_timeseries"); return result
 auc=0.0; weighted=[]; peak=0.0; sampled_area=0.0; sampled_span=0.0;above_ecn=0.0
 tx_by_window={k:0.0 for k in windows}; link_window_counts={k:0 for k in windows}
 for link,pts in by_link.items():
  times=[x["time"] for x in pts]
  if any(b<a for a,b in zip(times,times[1:])): suspicious.append("non_monotonic_queue_time:"+link)
  if any(b==a for a,b in zip(times,times[1:])): suspicious.append("duplicate_queue_timestamp:"+link)
  dts=[b-a for a,b in zip(times,times[1:]) if b>a]
  if dts:
   med=statistics.median(dts)
   if med>0 and max(dts)>5*med: suspicious.append("queue_sampling_gap:"+link)
  peak=max(peak,max((x["queue"] for x in pts),default=0.0))
  for a,b in zip(pts,pts[1:]):
   dt=b["time"]-a["time"]
   if dt<=0: continue
   auc+=0.5*(a["queue"]+b["queue"])*dt
   weighted.append((a["queue"],dt))
   if ecn_threshold is not None: above_ecn+=duration_above(a,b,ecn_threshold)
   if a["util"] is not None and b["util"] is not None:
    sampled_area+=0.5*(a["util"]+b["util"])*dt; sampled_span+=dt
  for name,(start,end) in windows.items():
   if start is None or end is None or end<=start: continue
   link_window_counts[name]+=1
   # tx_bytes_delta is the bytes sent in the sample interval ending here.
   tx_by_window[name]+=sum(x["tx"] for x in pts if start < x["time"] <= end)
 result.update(queue_peak_bytes=peak,queue_auc_byte_seconds=auc,
               queue_auc_byte_us=auc*1e6,
               queue_p95_time_weighted_bytes=weighted_quantile(weighted,.95),
               time_above_ecn_threshold_us=(above_ecn*1e6 if ecn_threshold is not None else None),
               utilization_sampled_full_simulation=(sampled_area/sampled_span if sampled_span else None))
 for name,(start,end) in windows.items():
  key={"full":"utilization_full_simulation","active":"utilization_active_window",
       "newcomer":"utilization_newcomer_window","all_work":"utilization_all_work_window"}[name]
  links=link_window_counts[name]
  value=(tx_by_window[name]*8.0/(capacity_bps*(end-start)*links)) if links and end and start is not None and end>start else None
  result[key]=value
  if value is not None and value>1.000001: suspicious.append("utilization_above_one:%s=%.9g"%(name,value))
 # Threshold time cannot be reconstructed safely from dynamic-PFC state here.
 if ecn_threshold is None: unresolved.append("ecn_threshold_not_reconstructable")
 unresolved.append("dynamic_pfc_threshold_not_reliably_reconstructable")
 return result

def reconstruct_plan(run,scenario,flow_rows,round_rows,scope_rows,unresolved):
 flow_input=parse_flow_txt(locate(run,("flow.txt",)))
 summaries={integer(r.get("flow_id")):r for r in flow_rows}
 scope={integer(r.get("batch_id")):r for r in scope_rows}
 rounds_by={}
 for r in round_rows: rounds_by.setdefault(integer(r.get("flow_id")),[]).append(r)
 plans={}; evidence={}
 plan_path=locate(run,("flow_plan.csv",))
 for r in read_rows(plan_path):
  fid=integer(r.get("flow_id")); key=(integer(r.get("round_id")),integer(r.get("group_id")))
  p=plans.setdefault(fid,{"flow_id":fid,"planned_bytes":0,"group_ids":set(),"round_ids":set()})
  if key not in evidence.setdefault(fid,set()):
   p["planned_bytes"]+=integer(r.get("round_bytes")); evidence[fid].add(key)
  p["group_ids"].add(integer(r.get("group_id"))); p["round_ids"].add(integer(r.get("round_id")))
 if not plans:
  for fid,rs in rounds_by.items():
   p=plans.setdefault(fid,{"flow_id":fid,"planned_bytes":0,"group_ids":set(),"round_ids":set()})
   for r in rs:
    p["planned_bytes"]+=integer(r.get("round_bytes"));p["group_ids"].add(integer(r.get("round_group_id")));p["round_ids"].add(integer(r.get("round_id")))
 for fid,r in summaries.items():
  if fid not in plans:
   plans[fid]={"flow_id":fid,"planned_bytes":integer(r.get("total_size_bytes")),"group_ids":set(),"round_ids":set()}
 for fid,r in flow_input.items():
  if fid not in plans: plans[fid]={"flow_id":fid,"planned_bytes":r["planned_bytes"],"group_ids":set(),"round_ids":set()}
 incumbent=set(integer(x) for x in scenario.get("incumbent_flow_ids",[]))
 newcomer=set(integer(x) for x in scenario.get("pending_flow_ids",[]))
 overlap=incumbent&newcomer
 if overlap: raise ValueError("incumbent/newcomer overlap: %s"%sorted(overlap))
 known=set(plans); missing_roles=known-(incumbent|newcomer)
 for fid in missing_roles:
  groups=plans[fid]["group_ids"]
  if scenario.get("incumbent_offered_load_percent",0) and 0 in groups: incumbent.add(fid)
  else: newcomer.add(fid)
 if (incumbent|newcomer)!=known: raise ValueError("roles do not cover planned flows")
 out=[]
 for fid in sorted(plans):
  p=plans[fid]; sr=summaries.get(fid,{}); inp=flow_input.get(fid,{})
  rs=rounds_by.get(fid,[]); gids=sorted(p["group_ids"]); rids=sorted(p["round_ids"])
  gid=gids[0] if len(gids)==1 else None; rid=rids[0] if len(rids)==1 else None
  app=num(sr.get("start_time"),None)
  if app is None and gid in scope: app=num(scope[gid].get("application_ready_ns"))*1e-9
  if app is None and fid in newcomer and scenario.get("common_release_ns") is not None: app=num(scenario["common_release_ns"])*1e-9
  if app is None: app=num(inp.get("input_start_time"),None)
  releases=[num(r.get("release_time"),None) for r in rs if num(r.get("release_time"),None) is not None]
  network=min(releases) if releases else (num(scope[gid].get("decision_complete_ns"))*1e-9 if gid in scope else app)
  out.append({"flow_id":fid,"role":"incumbent" if fid in incumbent else "newcomer",
   "group_id":gid,"round_id":rid,"source":integer(sr.get("src",inp.get("source",-1)),-1),
   "destination":integer(sr.get("dst",inp.get("destination",-1)),-1),
   "planned_bytes":integer(p["planned_bytes"]),"application_ready_time":app,
   "network_release_time":network,"evidence_source":"flow_plan.csv" if plan_path else "round_summary.csv"})
 return out

def observation_end_seconds(run,config,inc_rows,queue_path):
 stop=num(config.get("SIMULATOR_STOP_TIME"),0)
 if stop>0: return stop
 vals=[num(r.get("time_ns"))*1e-9 for r in inc_rows if r.get("time_ns")]
 if queue_path:
  for r in read_rows(queue_path): vals.append(num(r.get("time",r.get("time_seconds",0))))
 return max(vals+[0.0])

def collect(run_dir,output_dir):
 run=os.path.abspath(run_dir); out=os.path.abspath(output_dir)
 os.makedirs(out,exist_ok=True)
 suspicious=[]; unresolved=[]
 scenario=read_json(os.path.join(run,"scenario_meta.json")); meta=read_json(os.path.join(run,"run_meta.json"))
 old_result=read_json(os.path.join(run,"result.json"))
 flow_rows=read_rows(locate(run,("flow_summary.csv",)))
 round_rows=read_rows(locate(run,("round_summary.csv",)))
 inc_rows=read_rows(locate(run,("incumbent_summary.csv",)))
 rate_rows=read_rows(locate(run,("rate_summary.csv",)))
 scope_rows=read_rows(locate(run,("scope_summary.csv",)))
 config_path=locate(run,("config.txt",)); config=parse_config(config_path)
 plan=reconstruct_plan(run,scenario,flow_rows,round_rows,scope_rows,unresolved)
 summaries={integer(r.get("flow_id")):r for r in flow_rows}
 inc={integer(r.get("flow_id")):r for r in inc_rows}
 rates={integer(r.get("flow_id")):r for r in rate_rows}
 rounds={}
 for r in round_rows: rounds.setdefault(integer(r.get("flow_id")),[]).append(r)
 qpath=locate(run,("selected_link_timeseries.csv","selected_link_timeseries.csv.gz","queue_timeseries.csv","queue_timeseries.csv.gz"))
 obs_end=observation_end_seconds(run,config,inc_rows,qpath)
 ledger=[]
 for p in plan:
  fid=p["flow_id"]; planned=p["planned_bytes"]; sr=summaries.get(fid,{}); ir=inc.get(fid,{}); rr=rounds.get(fid,[]); rate=rates.get(fid,{})
  delivered_candidates=[]; evidence=[]
  if sr:
   delivered_candidates.append(integer(sr.get("acked_bytes"))); evidence.append("flow_summary")
  if ir:
   delivered_candidates.extend([integer(ir.get("delivered_bytes")),integer(ir.get("acked_bytes"))]); evidence.append("incumbent_summary")
  if rate and rate.get("final_sample_remaining_bytes") not in (None,""):
   delivered_candidates.append(max(planned-integer(rate.get("final_sample_remaining_bytes")),0)); evidence.append("rate_summary_remaining")
  round_complete=bool(rr) and all(num(x.get("ack_completion_time"))>0 for x in rr)
  if round_complete: delivered_candidates.append(planned); evidence.append("round_ack_completion")
  delivered=max(delivered_candidates+[0])
  if delivered>planned:
   suspicious.append("delivered_exceeds_planned:flow_%d:%d>%d"%(fid,delivered,planned)); delivered=planned
  completed_claim=(truth(sr.get("completed")) or truth(ir.get("finished")) or round_complete)
  completed=bool(completed_claim and delivered>=planned)
  finish_candidates=[]
  if truth(sr.get("completed")) and num(sr.get("finish_time"))>0: finish_candidates.append(num(sr["finish_time"]))
  if truth(ir.get("finished")) and num(ir.get("completion_time_seconds"))>0: finish_candidates.append(num(ir["completion_time_seconds"]))
  if round_complete: finish_candidates.extend(num(x.get("ack_completion_time")) for x in rr)
  finish=max(finish_candidates) if completed and finish_candidates else None
  if completed and finish is None: unresolved.append("completed_without_finish_time:flow_%d"%fid)
  remaining=max(planned-delivered,0); app=p["application_ready_time"]
  fct=(finish-app) if finish is not None and app is not None else None
  reason="" if completed else ("missing_completion_record" if delivered>=planned else "unfinished_at_observation_end")
  ledger.append(dict(p,delivered_bytes_final=delivered,acked_bytes_final=delivered,
   remaining_bytes_final=remaining,completed=completed,completion_time_absolute=finish,
   fct_from_application_ready=fct,completion_evidence="+".join(sorted(set(evidence))),
   censored=not completed,observation_end_time=obs_end,unresolved_reason=reason))
 newcomers=[x for x in ledger if x["role"]=="newcomer"]; incumbents=[x for x in ledger if x["role"]=="incumbent"]
 all_new=bool(newcomers) and all(x["completed"] for x in newcomers); all_inc=all(x["completed"] for x in incumbents)
 all_complete=bool(ledger) and all(x["completed"] for x in ledger)
 new_ready=min((x["application_ready_time"] for x in newcomers if x["application_ready_time"] is not None),default=None)
 new_finishes=[x["completion_time_absolute"] for x in newcomers if x["completion_time_absolute"] is not None]
 all_ready=min((x["application_ready_time"] for x in ledger if x["application_ready_time"] is not None),default=0.0)
 all_finishes=[x["completion_time_absolute"] for x in ledger if x["completion_time_absolute"] is not None]
 last_finish=max(all_finishes) if all_complete and len(all_finishes)==len(ledger) else None
 active_end=last_finish if all_complete else obs_end
 newcomer_end=max(new_finishes) if all_new and len(new_finishes)==len(newcomers) else obs_end
 windows={"full":(0.0,obs_end),"active":(all_ready,active_end),"newcomer":(new_ready,newcomer_end),"all_work":(all_ready,active_end)}
 capacity=num(scenario.get("capacity_bps"),parse_bps(config.get("DATA_RATE")))
 ecn_threshold=parse_ecn_threshold_bytes(config,capacity)
 network=queue_and_utilization(run,capacity,ecn_threshold,windows,suspicious,unresolved)
 total_plan=sum(x["planned_bytes"] for x in ledger); total_del=sum(x["delivered_bytes_final"] for x in ledger); total_rem=sum(x["remaining_bytes_final"] for x in ledger)
 if total_plan!=total_del+total_rem: raise ValueError("application-byte conservation failure")
 control=read_rows(locate(run,("control_summary.csv",)))
 cr=control[0] if control else {}
 logical_count=integer(cr.get("summary_messages"))+integer(cr.get("grant_messages"))
 logical_bytes=integer(cr.get("total_control_bytes"))
 monitor=integer(old_result.get("monitoring_only_summary_count",0)); internal=integer(old_result.get("simulator_internal_rate_write_count",0))
 applied_path=locate(run,("applied_rate_audit.csv",
                          "applied_rate_audit.csv.gz"))
 applied_violations,applied_max_excess=summarize_applied_audit(applied_path)
 tx_rows=read_rows(locate(run,("sender_tx_trace.csv","sender_tx_trace.csv.gz")))
 pacing_violations=sum(1 for row in tx_rows
  if row.get("event")=="TX_SEND" and num(row.get("previous_tx_time_ns"),0)>0
  and num(row.get("actual_gap_ns"),0)+1<num(row.get("expected_gap_ns"),0))
 duration=max(obs_end-all_ready,0.0)
 new_fcts=[x["fct_from_application_ready"] for x in newcomers if x["fct_from_application_ready"] is not None]
 inc_finish=[x["completion_time_absolute"] for x in incumbents if x["completion_time_absolute"] is not None]
 inc_planned=sum(x["planned_bytes"] for x in incumbents); inc_del=sum(x["delivered_bytes_final"] for x in incumbents)
 result={
  "collector_version":COLLECTOR_VERSION,"metric_definitions_version":DEFINITIONS_VERSION,
  "source_run":run,"scenario":scenario.get("scenario",meta.get("scenario",old_result.get("scenario"))),
  "algorithm":meta.get("algorithm_name",meta.get("algorithm",old_result.get("algorithm"))),"seed":meta.get("seed",old_result.get("seed")),
  "newcomer_planned_bytes":sum(x["planned_bytes"] for x in newcomers),"newcomer_delivered_bytes":sum(x["delivered_bytes_final"] for x in newcomers),
  "newcomer_remaining_bytes":sum(x["remaining_bytes_final"] for x in newcomers),"newcomer_total_count":len(newcomers),
  "newcomer_completed_count":sum(x["completed"] for x in newcomers),"all_newcomers_completed":all_new,
  "newcomer_cct_us":((max(new_finishes)-new_ready)*1e6 if all_new and new_ready is not None and len(new_finishes)==len(newcomers) else None),
  "newcomer_median_fct_us":(statistics.median(new_fcts)*1e6 if all_new and len(new_fcts)==len(newcomers) else None),
  "newcomer_max_fct_us":(max(new_fcts)*1e6 if all_new and len(new_fcts)==len(newcomers) else None),
  "newcomer_completion_skew_us":((max(new_finishes)-min(new_finishes))*1e6 if all_new and new_finishes else None),
  "incumbent_planned_bytes":inc_planned,"incumbent_delivered_bytes":inc_del,
  "incumbent_remaining_bytes":sum(x["remaining_bytes_final"] for x in incumbents),
  "incumbent_remaining_fraction":((inc_planned-inc_del)/inc_planned if inc_planned else 0.0),
  "incumbent_total_count":len(incumbents),"incumbent_completed_count":sum(x["completed"] for x in incumbents),
  "all_incumbents_completed":all_inc,"incumbent_completion_time_us":(max(inc_finish)*1e6 if all_inc and inc_finish else None),
  "incumbent_average_goodput_gbps":(inc_del*8.0/max((max(inc_finish) if all_inc and inc_finish else obs_end)-min((x["application_ready_time"] for x in incumbents if x["application_ready_time"] is not None),default=0.0),1e-30)/1e9 if incumbents else 0.0),
  "total_planned_bytes":total_plan,"total_delivered_bytes":total_del,"total_remaining_bytes":total_rem,
  "total_flow_count":len(ledger),"completed_flow_count":sum(x["completed"] for x in ledger),"all_flows_completed":all_complete,
  "last_completed_flow_time_absolute":last_finish,"all_work_makespan_us":((last_finish-all_ready)*1e6 if all_complete and last_finish is not None else None),
  "censored_makespan_lower_bound_us":((obs_end-all_ready)*1e6 if not all_complete else None),
  "observation_horizon_us":obs_end*1e6,"total_goodput_gbps":(total_del*8.0/max(duration,1e-30)/1e9),
  "logical_control_message_count":logical_count,"logical_control_bytes":logical_bytes,
  "monitoring_only_message_count":monitor,"simulator_internal_rate_write_count":internal,
  "control_messages_per_second":logical_count/max(duration,1e-30),"control_bandwidth_bps":logical_bytes*8.0/max(duration,1e-30),
  "control_bytes_over_data_bytes":logical_bytes/max(total_del,1),"byte_conservation_valid":total_plan==total_del+total_rem,
  "capacity_violation_count":integer(old_result.get("capacity_violations",0)),
  "applied_capacity_violation_count":applied_violations,
  "applied_capacity_max_excess_bps":applied_max_excess,
  "credit_violation_count":integer(old_result.get("credit_violations",0)),"pacing_violation_count":pacing_violations,
  "scope_decision_count":len(scope_rows),"unresolved_fields":sorted(set(unresolved)),"suspicious_findings":sorted(set(suspicious))}
 result.update(network)
 ledger_fields=["flow_id","role","group_id","round_id","source","destination","planned_bytes","application_ready_time","network_release_time","evidence_source","delivered_bytes_final","acked_bytes_final","remaining_bytes_final","completed","completion_time_absolute","fct_from_application_ready","completion_evidence","censored","observation_end_time","unresolved_reason"]
 with open(os.path.join(out,"flow_outcome_ledger.csv"),"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=ledger_fields);w.writeheader();w.writerows(ledger)
 with open(os.path.join(out,"result_full_work.json"),"w") as f: json.dump(result,f,indent=2,sort_keys=True);f.write("\n")
 inputs=[]
 for name in ("flow_plan.csv","flow_summary.csv","round_summary.csv","incumbent_summary.csv","rate_summary.csv","scenario_meta.json","run_meta.json","rounds.txt","group_schedule.txt","config.txt","control_summary.csv","applied_rate_audit.csv","applied_rate_audit.csv.gz","sender_tx_trace.csv","sender_tx_trace.csv.gz",os.path.basename(qpath) if qpath else ""):
  p=os.path.join(run,name) if name else None
  if p and os.path.isfile(p) and p not in inputs: inputs.append(p)
 provenance={"source_run":run,"input_file_hashes":{os.path.basename(p):sha256(p) for p in inputs},
  "collector_version":COLLECTOR_VERSION,"metric_definitions_version":DEFINITIONS_VERSION,
  "unresolved_fields":result["unresolved_fields"],"suspicious_findings":result["suspicious_findings"],
  "generated_time_unix":time.time(),"original_files_modified":False}
 with open(os.path.join(out,"metric_provenance.json"),"w") as f: json.dump(provenance,f,indent=2,sort_keys=True);f.write("\n")
 return result,ledger,provenance

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--run-dir",required=True);ap.add_argument("--output-dir",required=True);a=ap.parse_args()
 result,ledger,_=collect(a.run_dir,a.output_dir)
 print("FULL_WORK_METRICS_OK flows=%d completed=%d unresolved=%d suspicious=%d"%(len(ledger),result["completed_flow_count"],len(result["unresolved_fields"]),len(result["suspicious_findings"])))

if __name__=="__main__": main()
