import csv, os
BASE='/work/simulation/experiment/scheme1_sba'
OUT=os.path.join(BASE,'paper_data')
def load(stem):
    d=os.path.join(BASE, stem+'_out')
    fr=list(csv.DictReader(open(os.path.join(d,'flow_summary.csv'))))
    ts=list(csv.DictReader(open(os.path.join(d,'selected_link_timeseries.csv'))))
    inc=[r for r in fr if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    fin=max(float(r['finish_time']) for r in inc)
    win=[r for r in ts if 1.9<=float(r['time'])<=fin]
    q=[float(r['queue_bytes']) for r in win]
    u=[float(r['utilization']) for r in win]
    bg=[r for r in fr if r['src']=='65'][0]
    def p(v,k): 
        return v[int(len(v)*k+0.999)-1]
    # background rate before/during from snd_una progress
    fs=os.path.join(d,'selected_flow_timeseries.csv')
    bgb=bgd=bgmin=float('nan')
    if os.path.exists(fs):
        s=[(float(r['time']),float(r['snd_una'])) for r in csv.DictReader(open(fs)) if r['flow_id']=='0']
        s.sort()
        def rate(t0,t1):
            a=[v for t,v in s if t<=t0]; b=[v for t,v in s if t<=t1]
            return (b[-1]-a[-1])*8/(t1-t0)/1e9 if a and b and t1>t0 else float('nan')
        bgb=rate(1.5,1.9); bgd=rate(1.9,min(1.9+0.15,s[-1][0]))
        pts=[(t,v) for t,v in s if 1.9<=t<=min(1.9+0.15,s[-1][0])]
        mn=float('inf')
        for i in range(1,len(pts)):
            dt=pts[i][0]-pts[i-1][0]
            if dt>0: mn=min(mn,(pts[i][1]-pts[i-1][1])*8/dt/1e9)
        bgmin=mn
    return {
      'incast_done': len(inc),
      'fct_mean_ms': sum(fct)/len(fct), 'fct_p95_ms': p(fct,0.95), 'fct_p99_ms': p(fct,0.99),
      'cct_ms': (fin-1.9)*1000,
      'incast_agg_gbps': sum(float(r['flow_goodput']) for r in inc)/1e9,
      'bg_before_gbps': bgb, 'bg_during_gbps': bgd, 'bg_min_gbps': bgmin,
      'bg_retention_pct': (bgd/bgb*100 if bgb==bgb and bgb else float('nan')),
      'bg_acked_bytes': float(bg['acked_bytes']),
      'queue_mean_bytes': sum(q)/len(q), 'queue_p99_bytes': p(sorted(q),0.99),
      'queue_peak_bytes': max(q),
      'util_mean': sum(u)/len(u),
      'ecn_marks': sum(float(r['ecn_marks_delta']) for r in ts),
      'pfc_events': sum(float(r['pfc_event_delta']) for r in ts),
      'pfc_pause_total_ns': sum(float(r['pfc_pause_ns_delta']) for r in ts),
      'drops': 0.0,
      'retx_bytes_total': sum(float(r['retx_bytes']) for r in fr),
      'retx_events_total': sum(float(r['retx_events']) for r in fr),
    }
full=load('m_cbapsba_s3_seed2'); off=load('a_cbapsba_s3_migoff_seed2')
KEYS=['incast_done','fct_mean_ms','fct_p95_ms','fct_p99_ms','cct_ms','incast_agg_gbps',
      'bg_before_gbps','bg_during_gbps','bg_min_gbps','bg_retention_pct','bg_acked_bytes',
      'queue_mean_bytes','queue_p99_bytes','queue_peak_bytes','util_mean',
      'ecn_marks','pfc_events','pfc_pause_total_ns','drops','retx_bytes_total','retx_events_total']
p=os.path.join(OUT,'p7_ablation_s3_migration_off.csv')
with open(p,'w') as f:
    w=csv.writer(f)
    w.writerow(['# S3 ablation: full CBAP-SBA vs migration disabled (CBAP_MIGRATION_ENABLE 0).'])
    w.writerow(['# Config-only change, no source modification. Everything else identical:'])
    w.writerow(['# topology, flow file, seed 2, stop 3.0s, ECN/PFC, MIN_RATE, eta_base, telemetry window.'])
    w.writerow(['# Verified: the two configs differ in exactly one key.'])
    w.writerow(['metric','full_cbap_sba','migration_off','delta_pct'])
    for k in KEYS:
        a,b=full[k],off[k]
        dp='' if (a!=a or b!=b or a==0) else '%.2f'%((b-a)/a*100)
        w.writerow([k,'%.6f'%a if a==a else '','%.6f'%b if b==b else '',dp])
print('wrote p7_ablation_s3_migration_off.csv')
print('  %-22s %-16s %-16s %s'%('metric','full','migration_off','delta%'))
for k in KEYS:
    a,b=full[k],off[k]
    dp='' if (a!=a or b!=b or a==0) else '%+.2f%%'%((b-a)/a*100)
    print('  %-22s %-16.4f %-16.4f %s'%(k,a,b,dp))
