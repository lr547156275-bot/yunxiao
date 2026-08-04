#!/usr/bin/env python3
import csv,gzip,json,math,os,statistics
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."));RUN=os.path.join(ROOT,'runs_core')
def rows(d,n):
 p=os.path.join(d,n);p=p if os.path.isfile(p) else p+'.gz'
 if not os.path.isfile(p):return []
 op=gzip.open if p.endswith('.gz') else open
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def fnum(x,*keys):
 for k in keys:
  try:return float(x[k])
  except:pass
 return 0.0
def measured_pre(d,load):
 samples=rows(d,'selected_link_timeseries.csv')
 vals=[]
 for x in samples:
  t=fnum(x,'time_ns','time')
  if t<1 and 'time' in x:t*=1e9
  if 2000000<=t<3000000:vals.append(fnum(x,'utilization'))
 return 100*statistics.mean(vals) if vals else (0.0 if load==0 else float('nan'))
def fct_us(x):
 if x.get('fct_us','')!='':return float(x['fct_us'])
 return float(x.get('fct',0))*1e6
def pause_duration_us(events):
 starts={};total=0
 for x in events:
  key=(x.get('node_id'),x.get('if_index'),x.get('q_index'));t=int(x.get('time_ns',0));event=x.get('event_type','').lower()
  if 'pause' in event and 'resume' not in event:starts[key]=t
  elif ('resume' in event or 'end' in event) and key in starts:total+=max(0,t-starts.pop(key))
 return total/1000.0
def main():
 out=[];invalid=[]
 for m in csv.DictReader(open(os.path.join(ROOT,'configs','core_manifest.csv'))):
  d=os.path.join(RUN,m['scenario'],m['algorithm_name'],'seed_1')
  if not os.path.isfile(os.path.join(d,'completed.flag')):invalid.append((m['run_id'],'missing_or_invalid'));continue
  r=json.load(open(os.path.join(d,'result.json')));meta=json.load(open(os.path.join(d,'run_meta.json')))
  util=measured_pre(d,int(m['incumbent_load_percent']));ok=math.isfinite(util) and abs(util-int(m['incumbent_load_percent']))<=2
  if not ok:invalid.append((m['run_id'],'pre_release_utilization_outside_2pp'))
  scope=rows(d,'scope_summary.csv');admit=rows(d,'cbap_admission.csv');control=rows(d,'control_summary.csv')
  flow=rows(d,'flow_summary.csv');case=json.load(open(os.path.join(d,'scenario_meta.json')));pending=set(case.get('pending_flow_ids',[]))
  fcts=[fct_us(x) for x in flow if int(x.get('flow_id',-1)) in pending]
  incumbents=[x for x in flow if int(x.get('flow_id',-1)) in set(case.get('incumbent_flow_ids',[]))]
  offered=int(m['incumbent_load_percent'])*1e9
  worst_drop=max([max(0.0,1-fnum(x,'flow_goodput','average_goodput')/offered) for x in incumbents],default=0.0) if offered else 0.0
  cbap_state=rows(d,'cbap_flow_state.csv');pfc=rows(d,'pfc_events.csv');total_packets=max(1,sum(int(x.get('total_size_bytes',x.get('size_bytes',0))) for x in flow)//1000)
  link_scope=rows(d,'scope_link_summary.csv');triggering=';'.join(x['link_id'] for x in link_scope if int(x.get('enabled_on_link',0)))
  out.append({"run_id":m['run_id'],"scenario":m['scenario'],"algorithm":m['algorithm_name'],"scope_decision":('ENABLE' if any(int(x['enabled']) for x in scope) else 'BYPASS') if int(m['cc_mode'])==24 else 'NOT_APPLICABLE',"scope_reason":scope[-1]['reason'] if scope else 'NOT_APPLICABLE',"triggering_links":triggering,"batch_size":m['fan_in'],"message_bytes":m['message_bytes'],"incumbent_offered_load_percent":m['incumbent_load_percent'],"measured_pre_release_utilization_percent":util,"new_batch_cct_us":max(fcts) if fcts else r.get('group_rct_max_us',0),"median_flow_fct_us":statistics.median(fcts) if fcts else r.get('flow_fct_mean_us',0),"max_flow_fct_us":max(fcts) if fcts else r.get('flow_fct_max_us',0),"completion_skew_us":(max(fcts)-min(fcts)) if fcts else 0,"peak_queue_bytes":r.get('queue_max_bytes',0),"queue_auc_byte_seconds":r.get('queue_auc_byte_seconds',0),"ecn_count":r.get('ecn_marks',0),"ecn_ratio":float(r.get('ecn_marks',0))/total_packets,"pfc_count":r.get('pfc_event_rows',0),"pfc_duration_us":pause_duration_us(pfc),"bottleneck_utilization":r.get('mean_utilization',0),"incumbent_worst_throughput_drop":worst_drop,"bytes_before_first_fresh_feedback":sum(int(x.get('bytes_sent_before_fresh_feedback',0)) for x in cbap_state),"admission_aggregate_rate_bps":sum(int(x.get('admit_rate_bps',0)) for x in admit),"control_message_count":sum(int(x.get('summary_messages',0))+int(x.get('grant_messages',0)) for x in control),"control_bytes":sum(int(x.get('total_control_bytes',0)) for x in control),"capacity_violation":r.get('capacity_violations',0),"credit_violation":r.get('credit_violations',0),"pacing_violation":r.get('pacing_violations',0),"valid":ok})
 os.makedirs(os.path.join(ROOT,'processed'),exist_ok=True)
 fields=list(out[0]) if out else ['run_id']
 with open(os.path.join(ROOT,'processed','core_results.csv'),'w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
 with open(os.path.join(ROOT,'processed','invalid_core_runs.csv'),'w',newline='') as f:w=csv.writer(f);w.writerow(('run_id','reason'));w.writerows(invalid)
 text=['# Core comparison analysis','','This report computes the deterministic parameter scan without treating repeats as random seeds.','', 'Valid runs: %d/170.'%(len(out)-len(invalid)),'Invalid runs: %d.'%len(invalid),'','No research conclusion is inferred by this script.']
 open(os.path.join(ROOT,'reports','core_comparison_report.md'),'w').write('\n'.join(text)+'\n')
 print('core_checked=%d invalid=%d'%(len(out),len(invalid)))
if __name__=='__main__':main()
