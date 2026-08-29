set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv
def load(stem):
    with open('%s_out/flow_summary.csv' % stem) as f: fr=list(csv.DictReader(f))
    with open('%s_out/selected_link_timeseries.csv' % stem) as f: ts=list(csv.DictReader(f))
    inc=[r for r in fr if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    fin=max(float(r['finish_time']) for r in inc)
    win=[r for r in ts if 1.9<=float(r['time'])<=fin]
    q=[float(r['queue_bytes']) for r in win]
    return dict(n=len(inc), mean=sum(fct)/len(fct), p99=fct[int(len(fct)*0.99+0.999)-1],
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q),
        ecn=sum(float(r['ecn_marks_delta']) for r in ts),
        pfc=sum(float(r['pfc_event_delta']) for r in ts),
        pause=sum(float(r['pfc_pause_ns_delta']) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fr),
        bg=float([r for r in fr if r['src']=='65'][0]['acked_bytes'])/1e9)
g=load('g_cbapsba_s3_seed2')   # new build, trace on
f=load('f_cbapsba_s3_seed2')   # previous feasibility build
m=load('m_cbapsba_s3_seed2')   # frozen baseline
print('  %-18s %-14s %-14s %-14s' % ('metric','frozen base','feasible v1','FINAL(trace)'))
for k,fmt in (('n','%d'),('mean','%.3f'),('p99','%.3f'),('gp','%.3f'),
              ('qmean','%.0f'),('qpeak','%.0f'),('ecn','%.0f'),
              ('pfc','%.0f'),('pause','%.0f'),('retx','%.0f'),('bg','%.3f')):
    print('  %-18s %-14s %-14s %-14s' % (k, fmt%m[k], fmt%f[k], fmt%g[k]))
print()
same = all(abs(g[k]-f[k])<1e-6 for k in ('mean','p99','gp','qmean','qpeak','ecn','pfc','pause','retx','bg'))
print('  FINAL vs feasible v1 bit-identical on all metrics: %s' % ('YES' if same else 'NO'))
PY
