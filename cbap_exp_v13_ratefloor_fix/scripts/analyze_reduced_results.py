#!/usr/bin/env python3
import csv,json,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'));RUN=os.path.join(ROOT,'runs_reduced');PROC=os.path.join(ROOT,'processed')
os.makedirs(PROC,exist_ok=True)
def rr(m):return os.path.join(RUN,m['scenario'],m['algorithm_name'],'seed_'+m['seed'])
def main():
 manifest=list(csv.DictReader(open(os.path.join(ROOT,'configs','reduced_manifest.csv'))));out=[];bad=[]
 for m in manifest:
  d=rr(m)
  if not os.path.isfile(os.path.join(d,'completed.flag')):bad.append((m['run_id'],'missing_or_invalid'));continue
  r=json.load(open(os.path.join(d,'result.json')));a=[]
  p=os.path.join(d,'applied_rate_audit.csv')
  if os.path.isfile(p):a=list(csv.DictReader(open(p)))
  tx=[];tp=os.path.join(d,'sender_tx_trace.csv')
  if os.path.isfile(tp):tx=list(csv.DictReader(open(tp)))
  pacing=sum(int(float(x.get('previous_tx_time_ns',0)))>0 and float(x.get('actual_gap_ns',0))+1<float(x.get('expected_gap_ns',0)) for x in tx if x.get('event')=='TX_SEND')
  row=dict(run_id=m['run_id'],scenario=m['scenario'],algorithm=m['algorithm_name'],seed=m['seed'],scope_decision=json.load(open(os.path.join(d,'run_meta.json'))).get('scope_decision','NOT_APPLICABLE'),cct_us=r.get('group_rct_max_us',0),peak_queue_bytes=r.get('queue_max_bytes',0),queue_auc_byte_seconds=r.get('queue_auc_byte_seconds',0),capacity_violation=r.get('capacity_violations',0),credit_violation=r.get('credit_violations',0),pacing_violation=pacing,applied_capacity_violation=sum(int(float(x.get('applied_capacity_violation',0))) for x in a),floor_clamp_count=sum(int(float(x.get('floor_clamp_count',0))) for x in a))
  out.append(row)
  if int(m['cc_mode'])==25 and (row['capacity_violation'] or row['credit_violation'] or row['pacing_violation'] or row['applied_capacity_violation'] or row['floor_clamp_count']):bad.append((m['run_id'],'v13 correctness violation'))
 by={(x['scenario'],x['algorithm']):x for x in out}
 for scenario in sorted(set(x['scenario'] for x in out)):
  a=by.get((scenario,'cbap_full_v12_scoped'));b=by.get((scenario,'cbap_full_v13_ratefloor_fix'))
  if not a or not b:continue
  cct=(float(b['cct_us'])-float(a['cct_us']))/max(float(a['cct_us']),1e-12)*100
  peak=(float(b['peak_queue_bytes'])-float(a['peak_queue_bytes']))/max(float(a['peak_queue_bytes']),1)*100
  auc=(float(b['queue_auc_byte_seconds'])-float(a['queue_auc_byte_seconds']))/max(float(a['queue_auc_byte_seconds']),1e-12)*100
  if scenario.startswith('fan32') and (cct>3 or peak>10 or auc>10):bad.append((scenario,'fan32 regression threshold'))
  if scenario.startswith('fan32') and a['scope_decision']!=b['scope_decision']:bad.append((scenario,'scope decision changed'))
  if scenario=='fan64_msg4m_load80' and cct>5:bad.append((scenario,'fan64 4MiB CCT regression threshold'))
  if scenario=='fan64_msg4m_load80' and (peak>=0 or auc>=0):bad.append((scenario,'peak queue or queue AUC did not improve'))
 fields=list(out[0]) if out else ['run_id']
 with open(os.path.join(PROC,'reduced_results.csv'),'w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
 with open(os.path.join(PROC,'invalid_reduced_runs.csv'),'w',newline='') as f:w=csv.writer(f);w.writerow(('run_id','reason'));w.writerows(bad)
 report=['# Reduced validation report','',f'Valid input runs: {len(out)}/25.',f'Failed checks: {len(bad)}.','','This is a deterministic correctness matrix; it does not establish a research conclusion.']
 open(os.path.join(ROOT,'reports','reduced_validation_report.md'),'w').write('\n'.join(report)+'\n')
 print('reduced_checked=%d invalid=%d'%(len(out),len(bad)))
if __name__=='__main__':main()
