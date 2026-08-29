set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S4 CBAP-SBA: matrix cell vs sanity-check cell (must match) ==="
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
    bg=[r for r in fr if r['src']=='65'][0]
    return dict(n=len(inc), mean=sum(fct)/len(fct), p99=fct[int(len(fct)*0.99+0.999)-1],
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q),
        ecn=sum(float(r['ecn_marks_delta']) for r in ts),
        pfc=sum(float(r['pfc_event_delta']) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fr),
        bgfct=float(bg['fct']), bggp=float(bg['flow_goodput'])/1e9)
m=load('m_cbapsba_s4_seed2'); g=load('g_cbapsba_s4_seed2')
print('  %-9s %-16s %-16s %s' % ('metric','sanity','matrix','same'))
for k,f in (('n','%d'),('mean','%.6f'),('p99','%.6f'),('gp','%.6f'),('qmean','%.3f'),
            ('qpeak','%.0f'),('ecn','%.0f'),('pfc','%.0f'),('retx','%.0f'),
            ('bgfct','%.6f'),('bggp','%.4f')):
    ok='YES' if abs(g[k]-m[k])<1e-6 else 'NO'
    print('  %-9s %-16s %-16s %s' % (k, f%g[k], f%m[k], ok))
print()
print('  bg slowdown = %.4f x (ideal 3.36842 s at the 9.5G cap)' % (m['bgfct']/3.36842))
PY
echo
echo "=== eta trace byte-identical? ==="
cmp -s m_cbapsba_s4_seed2_out/eta_feasibility.csv g_cbapsba_s4_seed2_out/eta_feasibility.csv \
  && echo "  YES" || echo "  differs"
