#!/usr/bin/env python3
import csv,gzip,json,math,os,sys
from collections import defaultdict
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))

def read(path):
 if os.path.isfile(path): op=open;p=path
 elif os.path.isfile(path+'.gz'):op=gzip.open;p=path+'.gz'
 else:return []
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def n(r,k):
 try:return float(r.get(k,0))
 except:return 0
def write(name,rows,fields):
 os.makedirs(os.path.join(ROOT,'processed'),exist_ok=True)
 with open(os.path.join(ROOT,'processed',name),'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
 manifest=list(csv.DictReader(open(os.path.join(ROOT,'configs','semantic_manifest.csv'))))
 failures=[]; semantic=[]; pacing=[]; admission=[]; credit=[]; decreases=[]; increases=[]; e2={}
 for exp in manifest:
  d=os.path.join(ROOT,'runs_semantic',exp['scenario'],exp['subcase'],exp['algorithm_name'],'seed_'+exp['seed'])
  if not os.path.isfile(os.path.join(d,'completed.flag')):
   failures.append(exp['run_id']+' missing_valid_run');continue
  states=read(os.path.join(d,'cbap_flow_state.csv')); tx=read(os.path.join(d,'cbap_tx_events.csv'))
  transitions=read(os.path.join(d,'cbap_rate_transitions.csv')); inc=read(os.path.join(d,'increase_policy_events.csv'))
  if not states or not tx:failures.append(exp['run_id']+' missing_semantic_rows')
  for state in states:
   why=[];release=n(state,'network_release_ns');complete=n(state,'first_complete_fresh_feedback_ns');exit_ns=n(state,'admission_exit_ns')
   if int(n(state,'ordinary_rate_updates_during_admission'))!=0:why.append('ordinary_admission_update')
   if complete<=release:why.append('feedback_not_post_release')
   if exit_ns<complete:why.append('exit_before_feedback')
   if n(state,'first_post_release_sample_ns')<=release:why.append('sample_not_post_release')
   if int(n(state,'pacing_violations')):why.append('pacing_violation')
   flowtx=[x for x in tx if x['flow_id']==state['flow_id'] and x['event']=='TX_SEND']
   track=[x for x in flowtx if int(n(x,'phase')) in (3,4)]
   if any(int(n(x,'credit_gate_active')) for x in track):why.append('credit_gate_in_tracking')
   if exp['algorithm_name'].startswith('cbap_full') and exit_ns and n(state,'credit_gate_exit_ns')!=exit_ns:why.append('credit_exit_mismatch')
   adm=[x for x in flowtx if int(n(x,'phase'))==2]
   if int(n(state,'emergency_rate_updates_during_admission'))==0 and any(abs(n(x,'current_rate_bps')-n(state,'initial_admit_rate_bps'))>1 for x in adm):why.append('admission_grant_overwritten')
   direct=sum(n(x,'previous_tx_time_ns')>0 and n(x,'actual_gap_ns')+1<n(x,'expected_gap_ns') for x in flowtx)
   if direct:why.append('direct_gap_violation')
   semantic.append({'run_id':exp['run_id'],'algorithm':exp['algorithm_name'],'flow_id':state['flow_id'],'valid':int(not why),'reason':';'.join(why)})
   pacing.append({'run_id':exp['run_id'],'flow_id':state['flow_id'],'pacing_violations':int(n(state,'pacing_violations')),'direct_gap_violations':direct,'valid':int(not direct and not n(state,'pacing_violations'))})
   credit.append({'run_id':exp['run_id'],'flow_id':state['flow_id'],'credit_gate_enter_ns':n(state,'credit_gate_enter_ns'),'credit_gate_exit_ns':n(state,'credit_gate_exit_ns'),'admission_exit_ns':exit_ns,'tracking_actual_rate_bps':n(state,'tracking_actual_rate_bps'),'tracking_current_rate_bps':n(state,'tracking_current_rate_bps'),'tracking_base_rate_bps':n(state,'tracking_base_rate_bps'),'valid':int(not any(x in why for x in ('credit_gate_in_tracking','credit_exit_mismatch')))})
   failures.extend(exp['run_id']+' flow='+state['flow_id']+' '+x for x in why)
  bykey=defaultdict(int)
  for row in transitions:
   if n(row,'new_rate_bps')<n(row,'old_rate_bps'):bykey[(row['epoch'],row['flow_id'])]+=1
  bad=sum(v>1 for v in bykey.values());decreases.append({'run_id':exp['run_id'],'decrease_decisions':sum(bykey.values()),'multi_decrease_epoch_violations':bad,'valid':int(bad==0)})
  if bad:failures.append(exp['run_id']+' multi_decrease_epoch')
  for row in inc:
   old=n(row,'current_rate_before_bps');target=n(row,'target_rate_bps');maximum=n(row,'max_rate_bps');new=n(row,'new_rate_bps');delta=n(row,'selected_delta_bps')
   frac=math.floor(1.10*old+1e-7);absolute=old+2e9;policy=exp['increase_policy'];cap=min(frac-old,2e9) if policy=='legacy_min' else max(frac-old,2e9)
   why=[]
   if abs(n(row,'fractional_candidate_bps')-frac)>1:why.append('fraction_candidate')
   if abs(n(row,'absolute_candidate_bps')-absolute)>1:why.append('absolute_candidate')
   if delta>cap+1:why.append('delta_policy_bound')
   if new>target+1 or new>maximum+1 or new<old:why.append('rate_bound')
   if int(n(row,'phase'))!=3:why.append('increase_outside_tracking')
   if int(n(row,'stable_epoch_count'))<2:why.append('insufficient_stable_epochs')
   if int(n(row,'stale_feedback')):why.append('stale_increase')
   if target*100<=old*105:why.append('threshold_not_met')
   item=dict(row);item.update(run_id=exp['run_id'],expected_policy=policy,valid=int(not why),audit_reason=';'.join(why));increases.append(item)
   failures.extend(exp['run_id']+' increase '+x for x in why)
  if exp['scenario']=='e2_batch_incast':
   meta=json.load(open(os.path.join(d,'scenario_meta.json')));ids=set(map(str,meta['new_flow_ids']));sel=[x for x in states if x['flow_id'] in ids]
   e2[exp['algorithm_name']]={'actual':sum(n(x,'actual_admission_mean_rate_bps') for x in sel),'planned':sum(n(x,'initial_admit_rate_bps') for x in sel),'bytes':sum(n(x,'bytes_sent_before_fresh_feedback') for x in sel)}
   admission.append(dict(algorithm=exp['algorithm_name'],actual_aggregate_bps=e2[exp['algorithm_name']]['actual'],planned_aggregate_bps=e2[exp['algorithm_name']]['planned'],bytes_before_feedback=e2[exp['algorithm_name']]['bytes']))
 independent=e2.get('independent_min_grant',{});batch=e2.get('cbap_rateonly_v1',{})
 if not independent or not batch or independent['actual']<=batch['actual']*1.05:failures.append('E2 independent_and_batch_not_distinct')
 source=open(os.path.join(os.path.dirname(ROOT),'simulation/src/point-to-point/model/rdma-hw.h')).read()
 if not __import__('re').search(r'CC_MODE_BOP_QB\s*=\s*15',source):failures.append('BOP_QB_mode15_changed')
 write('semantic_regression.csv',semantic,['run_id','algorithm','flow_id','valid','reason'])
 write('pacing_audit.csv',pacing,['run_id','flow_id','pacing_violations','direct_gap_violations','valid'])
 write('admission_audit.csv',admission,['algorithm','actual_aggregate_bps','planned_aggregate_bps','bytes_before_feedback'])
 write('credit_scope_audit.csv',credit,['run_id','flow_id','credit_gate_enter_ns','credit_gate_exit_ns','admission_exit_ns','tracking_actual_rate_bps','tracking_current_rate_bps','tracking_base_rate_bps','valid'])
 write('multibottleneck_decrease_audit.csv',decreases,['run_id','decrease_decisions','multi_decrease_epoch_violations','valid'])
 fields=list(increases[0]) if increases else ['run_id','scenario','algorithm','cbap_version','expected_policy','valid','audit_reason']
 write('increase_policy_audit.csv',increases,fields)
 verdict='SEMANTIC_PASS' if not failures else 'SEMANTIC_FAIL';os.makedirs(os.path.join(ROOT,'reports'),exist_ok=True)
 lines=[verdict,'','# CBAP-v1.1 semantic regression','', '- Expected runs: 11','- Hard failures: %d'%len(failures),'','## Failures','']+[('- '+x) for x in failures]
 if not failures:lines.append('- None')
 open(os.path.join(ROOT,'reports','semantic_regression_report.md'),'w').write('\n'.join(lines)+'\n')
 print(verdict);raise SystemExit(0 if not failures else 1)
if __name__=='__main__':main()
