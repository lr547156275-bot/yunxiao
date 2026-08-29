set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S1: why did FCT improve 4.68x if nothing was ECN-marked? ==="
python3 - <<'PY'
import csv
d='m_dcqcn_s1_seed2_out'
fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
bg=[r for r in fs if r['src']=='65'][0]
print('  incast aggregate goodput = %.3f Gbps  (pg0 run: 1.904)' % (sum(float(r['flow_goodput']) for r in inc)/1e9))
print('  background goodput       = %.3f Gbps  (pg0 run: 7.636 min)' % (float(bg['flow_goodput'])/1e9))
# The mechanism: pg decides the QUEUE, and queues are served separately.
print()
print('  MECHANISM: pg selects the egress queue (switch-node.cc:181).')
print('  pg0 run: background in queue 0, incast in queue 3 -> two separate queues,')
print('           served by the scheduler; the incast queue alone had to absorb')
print('           the burst while queue 0 kept draining background at line rate.')
print('  pg3 run: both classes share queue 3 -> one FIFO, so the 16 incast flows')
print('           and the background flow interleave and share the 10G port.')
PY
echo "=== confirm both classes are now in the same queue: per-queue occupancy ==="
head -1 m_dcqcn_s1_seed2_out/selected_link_timeseries.csv | tr ',' '\n' | nl | grep -iE "queue|qidx" | sed 's/^/  /'
