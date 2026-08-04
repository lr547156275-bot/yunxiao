#!/usr/bin/env python3
import argparse,csv,gzip,json,math,os,sys

def locate(d,n):
    for p in (os.path.join(d,n),os.path.join(d,n)+'.gz'):
        if os.path.isfile(p) and os.path.getsize(p)>0:return p
    return ''
def rows(d,n):
    p=locate(d,n)
    if not p:return []
    op=gzip.open if p.endswith('.gz') else open
    with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def fail(x): print('INVALID '+x,file=sys.stderr);raise SystemExit(1)
def num(x,k):
    try:return float(x.get(k,0))
    except:return float('nan')

def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir');p.add_argument('--allow-no-complete-flag',action='store_true');a=p.parse_args();d=os.path.abspath(a.run_dir)
    required=('manifest.json','run_meta.json','config.txt','command.txt','stdout.log','exit_status.txt','result.json','flow_summary.csv','queue_summary.csv','rate_summary.csv','scope_summary.csv','control_summary.csv','applied_rate_audit.csv','sender_tx_trace.csv')
    for n in required:
        if not locate(d,n):fail('missing '+n)
    if not a.allow_no_complete_flag and not os.path.isfile(os.path.join(d,'completed.flag')):fail('missing completed.flag')
    if int(open(os.path.join(d,'exit_status.txt')).read().strip()):fail('nonzero exit')
    m=json.load(open(os.path.join(d,'manifest.json')));meta=json.load(open(os.path.join(d,'run_meta.json')));r=json.load(open(os.path.join(d,'result.json')))
    if not r.get('all_flows_completed'):fail('incomplete flows')
    if meta.get('log_truncated') or r.get('log_truncated'):fail('truncated log')
    if any(isinstance(v,float) and not math.isfinite(v) for v in r.values()):fail('nonfinite result')
    mode=int(m['cc_mode'])
    if mode in (24,25):
        scope=rows(d,'scope_summary.csv')
        if not scope:fail('missing scope decision')
        if any(int(x.get('decision_delay_ns',-1))!=5000 for x in scope):fail('scope delay changed')
    if mode==24 and m.get('rate_floor_policy')!='ONE_PACKET_PER_EPOCH_LEGACY':fail('v12 floor identity')
    if mode==25:
        if m.get('rate_floor_policy')!='EXACT_GRANT_PACING':fail('v13 floor identity')
        audit=rows(d,'applied_rate_audit.csv')
        if not audit:fail('missing applied audit')
        if any(int(num(x,'applied_capacity_violation')) for x in audit):fail('applied capacity violation')
        if any(int(num(x,'floor_clamp_count')) for x in audit):fail('legacy floor clamp in v13')
        tx=rows(d,'sender_tx_trace.csv')
        if not tx:fail('missing TX events')
        if any(num(x,'previous_tx_time_ns')>0 and num(x,'actual_gap_ns')+1<num(x,'expected_gap_ns') for x in tx if x.get('event')=='TX_SEND'):fail('pacing violation')
        if int(r.get('capacity_violations',0)):fail('planner capacity violation')
        if int(r.get('credit_violations',0)):fail('credit violation')
        state=rows(d,'cbap_flow_state.csv')
        if state and any(int(num(x,'ordinary_rate_updates_during_admission')) for x in state):fail('ordinary update during Admission Hold')
        transitions=rows(d,'cbap_rate_transitions.csv');seen=set()
        for x in transitions:
            if num(x,'new_rate_bps')>=num(x,'old_rate_bps'):continue
            key=(x.get('epoch'),x.get('flow_id'))
            if key in seen:fail('multiple sender reductions in one epoch')
            seen.add(key)
    print('VALID '+d)
if __name__=='__main__':main()
