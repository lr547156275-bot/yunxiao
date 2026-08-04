#!/usr/bin/env python3
import csv,gzip,json,os
from collections import defaultdict
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'));RUNS=os.path.join(ROOT,'victim_calibration')
def read(p):
 if os.path.isfile(p):op=open
 elif os.path.isfile(p+'.gz'):p+='.gz';op=gzip.open
 else:return []
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def n(r,k):
 try:return float(r.get(k,0))
 except:return 0
def main():
 manifest=list(csv.DictReader(open(os.path.join(ROOT,'configs','victim_manifest.csv'))));rows=[]
 for e in manifest:
  d=os.path.join(RUNS,'victim_calibration',e['subcase'],e['algorithm_name'],'seed_1');result_path=os.path.join(d,'result.json')
  item=dict(e,valid=0,pfc_events=0,victim_goodput_gbps=0,victim_fct_us=0)
  if os.path.isfile(result_path) and os.path.isfile(os.path.join(d,'completed.flag')):
   result=json.load(open(result_path));flows=read(os.path.join(d,'flow_summary.csv'));victim=next((x for x in flows if x['flow_id']=='0'),{})
   item.update(valid=int(result.get('all_flows_completed',False)),pfc_events=result.get('pfc_event_rows',0),victim_goodput_gbps=n(victim,'flow_goodput')/1e9,victim_fct_us=n(victim,'fct')*1e6)
  rows.append(item)
 groups=defaultdict(dict)
 for r in rows:groups[r['subcase']][r['algorithm_name']]=r
 candidates=[]
 for sub,alg in groups.items():
  on=alg.get('dcqcn_pfc_on',{});off=alg.get('dcqcn_pfc_off',{});meta=json.load(open(os.path.join(ROOT,'victim_cases',sub,'scenario_meta.json')))
  throughput_ratio=n(on,'victim_goodput_gbps')/n(off,'victim_goodput_gbps') if n(off,'victim_goodput_gbps') else 0;fct_inflation=(n(on,'victim_fct_us')-n(off,'victim_fct_us'))/n(off,'victim_fct_us') if n(off,'victim_fct_us') else 0
  qualifies=bool(n(on,'valid') and n(off,'valid') and n(on,'pfc_events')>0 and (throughput_ratio<=.90 or fct_inflation>=.10) and (n(off,'victim_goodput_gbps')>n(on,'victim_goodput_gbps') or n(off,'victim_fct_us')<n(on,'victim_fct_us')) and meta['true_root_link_id']==2 and not meta['sa_sb_is_capacity_bottleneck'])
  candidates.append(dict(subcase=sub,contributor_count=meta['contributor_count'],access_rate_gbps=meta['contributor_access_rate_gbps'],message_mib=meta['contributor_message_mib'],pfc_on_events=n(on,'pfc_events'),throughput_ratio=throughput_ratio,fct_inflation=fct_inflation,qualifies=int(qualifies)))
 os.makedirs(os.path.join(ROOT,'processed'),exist_ok=True);fields=list(candidates[0]) if candidates else [];out=os.path.join(ROOT,'processed','victim_calibration_summary.csv')
 with open(out,'w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(sorted(candidates,key=lambda x:(x['contributor_count'],x['access_rate_gbps'],x['message_mib'])))
 selected=next((x for x in sorted(candidates,key=lambda x:(x['contributor_count'],x['access_rate_gbps'],x['message_mib'])) if x['qualifies']),None);os.makedirs(os.path.join(ROOT,'configs'),exist_ok=True)
 if selected:json.dump(selected,open(os.path.join(ROOT,'configs','selected_victim_scenario.json'),'w'),indent=2,sort_keys=True)
 verdict='SELECTED '+selected['subcase'] if selected else 'NO_VALID_VICTIM_PATHOLOGY';os.makedirs(os.path.join(ROOT,'reports'),exist_ok=True);open(os.path.join(ROOT,'reports','victim_calibration_report.md'),'w').write('# Victim pathology calibration\n\n%s\n'%verdict);print(verdict)
if __name__=='__main__':main()
