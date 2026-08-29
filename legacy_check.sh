set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
# Legacy arm: the frozen S3 CBAP-SBA config, unmodified, on the NEW binary.
# If the credit code is truly inert when disabled, every number must match the
# pg=3 matrix cell exactly.
name=qc_s3_legacy
sed "s|m_cbapsba_s3_seed2_out/|${name}_out/|g" m_cbapsba_s3_seed2.txt > ${name}.txt
mkdir -p ${name}_out
grep -c "CBAP_DELAY_CREDIT" ${name}.txt | sed 's/^/  delay-credit keys in config: /'
timeout --kill-after=60 14400 /work/simulation/build/scratch/third ${name}.txt > /work/matrix_logs/${name}.log 2>&1
echo "  exit=$?"
python3 - <<'PY'
import csv
def load(d):
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    last=max(float(r['finish_time']) for r in inc)
    q=[float(r['queue_bytes'] or 0) for r in ts if 1.9<=float(r['time'])<=last]
    return dict(n=len(inc), mean=sum(fct)/len(fct),
        p99=fct[int(len(fct)*0.99+0.999)-1],
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q),
        ecn=sum(float(r['ecn_marks_delta'] or 0) for r in ts),
        pfc=sum(float(r['pfc_event_delta'] or 0) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fs))
new=load('qc_s3_legacy_out'); ref=load('m_cbapsba_s3_seed2_out')
print('  %-10s %-18s %-18s %s' % ('metric','frozen(pg3)','legacy(new bin)','identical'))
allok=True
for k,f in (('n','%d'),('mean','%.9f'),('p99','%.9f'),('gp','%.9f'),
            ('qmean','%.6f'),('qpeak','%.0f'),('ecn','%.0f'),('pfc','%.0f'),('retx','%.0f')):
    ok = abs(new[k]-ref[k]) < 1e-9
    allok = allok and ok
    print('  %-10s %-18s %-18s %s' % (k, f%ref[k], f%new[k], 'YES' if ok else 'NO'))
print()
print('  LEGACY REPRODUCES FROZEN RESULT: %s' % ('YES' if allok else 'NO'))
PY
