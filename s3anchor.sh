set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S3 CBAP-SBA: matrix cell vs the sanity-check cell (must be identical) ==="
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
        retx=sum(float(r['retx_bytes']) for r in fr))
m=load('m_cbapsba_s3_seed2')   # matrix cell, ran in parallel
g=load('g_cbapsba_s3_seed2')   # sanity check cell, ran solo
print('  %-10s %-16s %-16s %s' % ('metric','sanity(solo)','matrix(parallel)','identical'))
for k,f in (('n','%d'),('mean','%.6f'),('p99','%.6f'),('gp','%.6f'),
            ('qmean','%.3f'),('qpeak','%.0f'),('ecn','%.0f'),('pfc','%.0f'),('retx','%.0f')):
    ok = 'YES' if abs(g[k]-m[k])<1e-6 else 'NO  (delta %.6g)' % (m[k]-g[k])
    print('  %-10s %-16s %-16s %s' % (k, f%g[k], f%m[k], ok))
PY
echo
echo "=== eta trace identical too? ==="
if cmp -s m_cbapsba_s3_seed2_out/eta_feasibility.csv g_cbapsba_s3_seed2_out/eta_feasibility.csv; then
  echo "  eta_feasibility.csv byte-identical between solo and parallel runs"
else
  echo "  differs:"; diff m_cbapsba_s3_seed2_out/eta_feasibility.csv g_cbapsba_s3_seed2_out/eta_feasibility.csv | head -4
fi
