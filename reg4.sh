set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv
def load(stem, bg='65'):
    with open('%s_out/flow_summary.csv' % stem) as f: fr=list(csv.DictReader(f))
    with open('%s_out/selected_link_timeseries.csv' % stem) as f: ts=list(csv.DictReader(f))
    inc=[r for r in fr if r['src']!=bg and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    fin=max(float(r['finish_time']) for r in inc)
    win=[r for r in ts if 1.9<=float(r['time'])<=fin]
    q=[float(r['queue_bytes']) for r in win]
    u=[float(r['utilization']) for r in win]
    return dict(n=len(inc), mean=sum(fct)/len(fct),
        p95=fct[int(len(fct)*0.95+0.999)-1], p99=fct[int(len(fct)*0.99+0.999)-1],
        cct=(fin-1.9)*1000,
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q), util=sum(u)/len(u),
        ecn=sum(float(r['ecn_marks_delta']) for r in ts),
        pfc=sum(float(r['pfc_event_delta']) for r in ts),
        pause=sum(float(r['pfc_pause_ns_delta']) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fr),
        bg=float([r for r in fr if r['src']==bg][0]['acked_bytes'])/1e9)
for tag in ('s3','s4'):
    g=load('g_cbapsba_%s_seed2'%tag); f=load('f_cbapsba_%s_seed2'%tag); m=load('m_cbapsba_%s_seed2'%tag)
    print('===== %s =====' % tag.upper())
    print('  %-14s %-14s %-14s %-14s %s' % ('metric','frozen base','feasible v1','FINAL','vs base'))
    for k,fm in (('n','%d'),('mean','%.3f'),('p95','%.3f'),('p99','%.3f'),('cct','%.3f'),
                 ('gp','%.3f'),('qmean','%.0f'),('qpeak','%.0f'),('util','%.4f'),
                 ('ecn','%.0f'),('pfc','%.0f'),('pause','%.0f'),('retx','%.0f'),('bg','%.3f')):
        d = '' if m[k]==0 else '%+.1f%%' % ((g[k]-m[k])/m[k]*100)
        print('  %-14s %-14s %-14s %-14s %s' % (k, fm%m[k], fm%f[k], fm%g[k], d))
    same = all(abs(g[k]-f[k])<1e-6 for k in ('mean','p95','p99','gp','qmean','qpeak','ecn','pfc','pause','retx','bg'))
    print('  FINAL == feasible v1 (no regression): %s' % ('YES' if same else 'NO'))
    print()
PY
