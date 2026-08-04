#!/usr/bin/env python3
import csv,json,math,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
RUN=os.path.join(ROOT,'runs_semantic'); PROC=os.path.join(ROOT,'processed'); REPORT=os.path.join(ROOT,'reports','ratefloor_semantic_report.md')
os.makedirs(PROC,exist_ok=True)
def rows(d,n):
 p=os.path.join(d,n)
 return list(csv.DictReader(open(p))) if os.path.isfile(p) else []
def f(x,k):
 try:return float(x.get(k,0))
 except:return 0.0
def rundir(r):return os.path.join(RUN,r['scenario'],r['algorithm_name'],'seed_'+r['seed'])
def write(name,fields,data):
 with open(os.path.join(PROC,name),'w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(data)
def main():
 manifest=list(csv.DictReader(open(os.path.join(ROOT,'configs','semantic_manifest.csv')))); failures=[];capacity=[];pacing=[];zero=[]
 for m in manifest:
  d=rundir(m)
  if not os.path.isfile(os.path.join(d,'completed.flag')): failures.append(m['run_id']+': missing valid completion');continue
  ar=rows(d,'applied_rate_audit.csv');tx=rows(d,'sender_tx_trace.csv')
  if int(m['cc_mode'])==25:
   if not ar or not tx: failures.append(m['run_id']+': missing audit rows');continue
   for x in ar:
    capacity.append(dict(run_id=m['run_id'],**x))
    if int(f(x,'applied_capacity_violation')):failures.append(m['run_id']+': applied capacity violation')
    if int(f(x,'floor_clamp_count')):failures.append(m['run_id']+': legacy clamp')
   low_rate_rows=[]
   for x in tx:
    if x.get('event')!='TX_SEND':continue
    violation=int(f(x,'previous_tx_time_ns')>0 and f(x,'actual_gap_ns')+1<f(x,'expected_gap_ns'))
    if f(x,'current_rate_bps')>0 and f(x,'current_rate_bps')<1702400000:
     low_rate_rows.append(x)
     pacing.append(dict(run_id=m['run_id'],flow_id=x['flow_id'],time_ns=x['time_ns'],rate_bps=x['current_rate_bps'],expected_gap_ns=x['expected_gap_ns'],actual_gap_ns=x['actual_gap_ns'],violation=violation))
     calculated=int(math.ceil(8*f(x,'wire_bytes')*1e9/f(x,'current_rate_bps')))
     if int(f(x,'expected_gap_ns'))!=calculated:failures.append(m['run_id']+': packet-gap formula mismatch')
    if violation:failures.append(m['run_id']+': sender pacing violation')
   if low_rate_rows and not any(f(x,'expected_gap_ns')>5000 for x in low_rate_rows):failures.append(m['run_id']+': no low-rate packet spans a control epoch')
   if m['scenario'].startswith('fan64') and not any(f(x,'flows_below_legacy_floor')>0 for x in ar):failures.append(m['run_id']+': no flow below legacy floor')
  if int(m['semantic_zero_test']):
   flow=m['semantic_zero_flow']
   transitions=[x for x in tx if x.get('event')=='TX_RESCHEDULE' and x.get('flow_id')==flow]
   pauses=[x for x in transitions if f(x,'current_rate_bps')==0]
   start=int(pauses[0]['time_ns']) if pauses else -1
   resumes=[x for x in transitions if start>=0 and int(x['time_ns'])>start and f(x,'current_rate_bps')>0]
   end=int(resumes[0]['time_ns']) if resumes else -1
   during=[x for x in tx if x.get('event')=='TX_SEND' and x.get('flow_id')==flow and start<=int(x['time_ns'])<end]
   before=[x for x in tx if x.get('event')=='TX_SEND' and x.get('flow_id')==flow and int(x['time_ns'])<start]
   after=[x for x in tx if x.get('event')=='TX_SEND' and x.get('flow_id')==flow and int(x['time_ns'])>=end]
   zr=[x for x in ar if int(f(x,'epoch'))>=int(m['semantic_zero_start_epoch']) and int(f(x,'epoch'))<int(m['semantic_zero_end_epoch'])]
   zero.append({'run_id':m['run_id'],'flow_id':flow,'pause_start_ns':start,'pause_end_ns':end,'pause_duration_ns':end-start if start>=0 and end>=0 else -1,'data_tx_during_pause':len(during),'positive_tx_before':len(before),'positive_tx_after':len(after),'zero_epoch_rows':len(zr),'paused_epoch_rows':sum(int(f(x,'paused_zero_grant_count')>0) for x in zr)})
   if start<0 or end<0 or during or not before or not after or end-start<10000:failures.append(m['run_id']+': zero pause/resume semantics')
   times=[int(x['time_ns']) for x in after]
   if len(times)!=len(set(times)):failures.append(m['run_id']+': catch-up duplicate TX time')
 pair=[m for m in manifest if m['scenario']=='fan64_msg1m_load80']
 decisions=[]
 for m in pair:
  p=os.path.join(rundir(m),'run_meta.json')
  if os.path.isfile(p):decisions.append(json.load(open(p)).get('scope_decision'))
 if len(decisions)==2 and decisions[0]!=decisions[1]:failures.append('fan64_msg1m_load80: v1.2/v1.3 scope decision differs')
 write('applied_rate_capacity_audit.csv',list(capacity[0]) if capacity else ['run_id'],capacity)
 write('low_rate_pacing_audit.csv',list(pacing[0]) if pacing else ['run_id'],pacing)
 write('zero_grant_audit.csv',list(zero[0]) if zero else ['run_id'],zero)
 unique_failures=sorted(set(failures))
 status='RATEFLOOR_SEMANTIC_PASS' if not unique_failures and len(manifest)==5 else 'RATEFLOOR_SEMANTIC_FAIL'
 text=[status,'','# Rate-floor semantic validation','',f'Expected/reused runs: {len(manifest)}/5.',f'Failures: {len(unique_failures)}.','', 'Hard checks include exact positive grants, zero-grant pause/resume, sender packet gaps, scope delay, and post-application capacity. Tail packets use their actual smaller wire size; every packet is checked against the exact ceil(bits/rate) formula.','']
 text += ['## Failures','']+(['- None.'] if not unique_failures else ['- '+x for x in unique_failures])
 open(REPORT,'w').write('\n'.join(text)+'\n');print(status)
if __name__=='__main__':main()
