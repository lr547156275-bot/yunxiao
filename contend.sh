set -u
cd /work/simulation/experiment/scheme1_sba/motivation
echo "=== Do both classes actually share link 84:1? Sum their rates during the collective ==="
python3 - <<'PY'
import csv
ts=list(csv.DictReader(open('m2_dcqcn_out/selected_link_timeseries.csv')))
win=[r for r in ts if 1.9<=float(r['time'])<=2.30]
tx=sum(float(r['tx_bytes_delta']) for r in win)
dur=float(win[-1]['time'])-float(win[0]['time'])
print('  link 84:1 carried %.3f Gbps during the collective' % (tx*8/dur/1e9))
print('  background 7.641 + incast 1.907 = %.3f Gbps  -> both on the same link' % (7.641+1.907))
PY
echo
echo "=== So where does the contention show? incast is STARVED, not the background ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$14} END{printf "  incast per-flow goodput = %.3f Mbps (of a 10 Gbps link, 64 flows)\n", s/n/1e6}' m2_dcqcn_out/flow_summary.csv
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11} END{printf "  incast mean FCT = %.3f ms for a 1 MiB message\n", s/n*1000}' m2_dcqcn_out/flow_summary.csv
python3 -c "print('  ideal FCT if incast had the whole link: %.3f ms' % (1048576*8/10e9*1000))"
echo
echo "=== CNP distribution: who absorbs the congestion signal? ==="
if [ -f m2_dcqcn_out/round_summary.csv ]; then
  head -1 m2_dcqcn_out/round_summary.csv | tr ',' '\n' | grep -n -i cnp | sed 's/^/  col /'
  python3 - <<'PY'
import csv
rows=list(csv.DictReader(open('m2_dcqcn_out/round_summary.csv')))
k=[c for c in rows[0] if 'cnp' in c.lower()]
if k:
    kk=k[0]
    bg=[float(r[kk]) for r in rows if r.get('flow_id')=='0' and r[kk] not in ('','nan')]
    inc=[float(r[kk]) for r in rows if r.get('flow_id') not in ('0',None) and r[kk] not in ('','nan')]
    print('  background CNPs: %s' % (sum(bg) if bg else 'n/a'))
    print('  incast CNPs    : %s across %d rows' % (sum(inc) if inc else 'n/a', len(inc)))
PY
fi
