#!/usr/bin/env python3
"""Analyze the completed 63-run freeze matrix at run/seed granularity."""
import csv,gzip,json,math,os,statistics
from collections import defaultdict
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."));RUNS=os.path.join(ROOT,'runs_formal')
def read(p):
 if os.path.isfile(p):op=open
 elif os.path.isfile(p+'.gz'):p+='.gz';op=gzip.open
 else:return []
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def n(r,k):
 try:return float(r.get(k,0))
 except:return 0
def avg(x):return statistics.mean(x) if x else 0
def pct(a,b):return (a-b)/b*100 if b else 0
def write(path,rows,fields=None):
 os.makedirs(os.path.dirname(path),exist_ok=True);fields=fields or (list(rows[0]) if rows else [])
 with open(path,'w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def path(e):return os.path.join(RUNS,e['scenario'],e['subcase'],e['algorithm_name'],'seed_'+e['seed'])
def simultaneous_fairness(d):
 rows=read(os.path.join(d,'selected_flow_timeseries.csv'));bytime=defaultdict(dict)
 for r in rows:bytime[n(r,'time')][r['flow_id']]=r
 samples=[];previous={}
 for t,flows in sorted(bytime.items()):
  active=[f for f,r in flows.items() if n(r,'released_bytes')>n(r,'snd_una')]
  if len(active)<3:previous={f:n(r,'snd_nxt') for f,r in flows.items()};continue
  rates=[]
  for f in active:
   if f in previous:rates.append(max(n(flows[f],'snd_nxt')-previous[f],0))
  previous={f:n(r,'snd_nxt') for f,r in flows.items()}
  if len(rates)==len(active) and sum(x*x for x in rates)>0:samples.append(sum(rates)**2/(len(rates)*sum(x*x for x in rates)))
 return avg(samples)
def convergence(d):
 rows=[r for r in read(os.path.join(d,'selected_flow_timeseries.csv')) if r['flow_id']=='2']
 states=read(os.path.join(d,'cbap_flow_state.csv'));s=next((x for x in states if x['flow_id']=='2'),{})
 release=n(s,'network_release_ns');over=read(os.path.join(d,'cbap_control_overhead.csv'));delay=n(over[0],'control_delay_ns') if over else 0
 rtt=max(n(s,'estimated_first_feedback_ns')-release-delay,1);out={}
 for threshold in (25,35,40,45,47.5):
  hit=next((n(x,'time')*1e9 for x in rows if n(x,'time')*1e9>=release and n(x,'current_rate')>=threshold*1e9),0);out['reach_%sg_rtt'%str(threshold).replace('.','p')]=(hit-release)/rtt if hit else 0
 for mult in (2,4,6,8):
  target=(release+mult*rtt)/1e9;chosen=min(rows,key=lambda x:abs(n(x,'time')-target)) if rows else {};out['rate_%drtt_gbps'%mult]=n(chosen,'current_rate')/1e9
 return out
def main():
 m=list(csv.DictReader(open(os.path.join(ROOT,'configs','freeze_manifest.csv'))));records=[];invalid=[]
 for e in m:
  d=path(e);problems=[]
  for f in ('completed.flag','result.json','run_meta.json','flow_summary.csv'):
   if not os.path.isfile(os.path.join(d,f)):problems.append('missing_'+f)
  if problems:invalid.append(dict(run_id=e['run_id'],reason=';'.join(problems)));continue
  result=json.load(open(os.path.join(d,'result.json')));meta=json.load(open(os.path.join(d,'run_meta.json')))
  if not result.get('all_flows_completed') or result.get('log_truncated'):invalid.append(dict(run_id=e['run_id'],reason='invalid_result'));continue
  item=dict(result,run_id=e['run_id'],scenario=e['scenario'],subcase=e['subcase'],algorithm=e['algorithm_name'],seed=int(e['seed']),cbap_version=e['cbap_version'],increase_policy=e['increase_policy'])
  flows=read(os.path.join(d,'flow_summary.csv'));g={r['flow_id']:n(r,'flow_goodput')/1e9 for r in flows}
  item.update(flow0_goodput_gbps=g.get('0',0),flow1_goodput_gbps=g.get('1',0),flow2_goodput_gbps=g.get('2',0),simultaneous_active_jain=simultaneous_fairness(d) if e['scenario']=='e4_parking_lot' else 0)
  if e['scenario']=='e4_parking_lot' and e['subcase']=='staggered' and e['algorithm_name'].startswith('cbap_'):item.update(convergence(d))
  states=read(os.path.join(d,'cbap_flow_state.csv'));item['pacing_violations']=sum(n(x,'pacing_violations') for x in states);item['capacity_violations']=result.get('capacity_violations',0);item['credit_violations']=result.get('credit_violations',0)
  records.append(item)
 processed=os.path.join(ROOT,'processed');write(os.path.join(processed,'summary_by_run.csv'),records);write(os.path.join(processed,'invalid_runs.csv'),invalid,['run_id','reason'])
 groups=defaultdict(list)
 for r in records:groups[(r['scenario'],r['subcase'],r['algorithm'])].append(r)
 metrics=('group_rct_mean_us','group_rct_max_us','queue_max_bytes','queue_auc_byte_seconds','mean_utilization','payload_goodput_gbps','completion_skew_us','simultaneous_active_jain','rate_4rtt_gbps','rate_6rtt_gbps')
 summary=[]
 for key,rows in sorted(groups.items()):
  item=dict(scenario=key[0],subcase=key[1],algorithm=key[2],seed_count=len(rows),deterministic_repetition=int(len({tuple(n(x,k) for k in metrics) for x in rows})==1))
  for k in metrics:
   v=[n(x,k) for x in rows];item[k+'_mean']=avg(v);item[k+'_median']=statistics.median(v);item[k+'_min']=min(v);item[k+'_max']=max(v)
  summary.append(item)
 write(os.path.join(processed,'summary_by_scenario.csv'),summary)
 by={(r['scenario'],r['subcase'],r['algorithm'],r['seed']):r for r in records};paired=[]
 for sc,sub in sorted(set((r['scenario'],r['subcase']) for r in records)):
  for base in ('dcqcn','hpcc_int','cbap_full_v1'):
   for k in metrics:
    diffs=[pct(n(by[(sc,sub,'cbap_full_v11',s)],k),n(by[(sc,sub,base,s)],k)) for s in (1,2,3) if (sc,sub,'cbap_full_v11',s) in by and (sc,sub,base,s) in by]
    if diffs:paired.append(dict(scenario=sc,subcase=sub,baseline=base,metric=k,mean=avg(diffs),median=statistics.median(diffs),minimum=min(diffs),maximum=max(diffs)))
 write(os.path.join(processed,'paired_comparisons.csv'),paired)
 report=['# CBAP-v1.1 freeze validation','','- Expected runs: 63','- Valid runs: %d'%len(records),'- Invalid runs: %d'%len(invalid),'- Statistical unit: scenario + algorithm + seed.','- No packets/epochs are treated as independent samples.','','Threshold evaluation is recorded in the processed CSVs; this script does not issue a paper FREEZE/CONTINUE/STOP conclusion.']
 os.makedirs(os.path.join(ROOT,'reports'),exist_ok=True);open(os.path.join(ROOT,'reports','freeze_validation_report.md'),'w').write('\n'.join(report)+'\n');print('expected=63 valid=%d invalid=%d'%(len(records),len(invalid)))
if __name__=='__main__':main()
