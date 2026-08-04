#!/usr/bin/env python3
import argparse,csv,gzip,json,math,os,sys
def path(d,n):
 for p in (os.path.join(d,n),os.path.join(d,n)+".gz"):
  if os.path.isfile(p) and os.path.getsize(p)>0:return p
 return ""
def readrows(d,n):
 p=path(d,n)
 if not p:return []
 op=gzip.open if p.endswith('.gz') else open
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def fail(s):print("INVALID "+s,file=sys.stderr);raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('run_dir');p.add_argument('--allow-no-complete-flag',action='store_true');a=p.parse_args();d=os.path.abspath(a.run_dir)
 for n in ('manifest.json','run_meta.json','config.txt','command.txt','stdout.log','exit_status.txt','result.json','flow_summary.csv','queue_summary.csv','scope_summary.csv','rate_summary.csv','control_summary.csv'):
  if not path(d,n):fail('missing '+n)
 if not a.allow_no_complete_flag and not os.path.isfile(os.path.join(d,'completed.flag')):fail('missing completed.flag')
 if int(open(os.path.join(d,'exit_status.txt')).read().strip()):fail('nonzero exit')
 m=json.load(open(os.path.join(d,'run_meta.json')));r=json.load(open(os.path.join(d,'result.json')))
 if not r.get('all_flows_completed'):fail('incomplete flows')
 if m.get('log_truncated') or r.get('log_truncated'):fail('truncated')
 if any(isinstance(v,float) and not math.isfinite(v) for v in r.values()):fail('nonfinite result')
 if int(m['cc_mode'])==24:
  scope=readrows(d,'scope_summary.csv');links=readrows(d,'scope_link_summary.csv')
  if not scope:fail('missing scoped decision')
  for x in scope:
   if int(x['decision_delay_ns'])!=5000:fail('scope delay')
   enabled=int(x['enabled']);triggers=int(x['triggering_link_count'])
   if enabled!=(triggers>0):fail('trigger consistency')
  if any(int(x['pre_release_causal'])!=1 for x in links):fail('future scope telemetry')
  if all(int(x['enabled'])==0 for x in scope):
   if readrows(d,'cbap_admission.csv') or readrows(d,'cbap_rate_transitions.csv'):fail('CBAP state on bypass')
 print('VALID '+d)
if __name__=='__main__':main()
