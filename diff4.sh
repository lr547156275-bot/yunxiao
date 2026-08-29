set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== which COLUMNS differ between the two sba_events.csv ? ==="
python3 - <<'PY'
import csv
def load(p):
    with open(p) as f: return list(csv.DictReader(f))
a = load('f_cbapsba_s3_seed2_out/sba_events.csv')
b = load('m_cbapsba_s3_seed2_out/sba_events.csv')
print('  rows: f=%d m=%d' % (len(a), len(b)))
cols = a[0].keys()
for c in cols:
    diff = sum(1 for x, y in zip(a, b) if x[c] != y[c])
    if diff:
        print('  %-22s differs in %d rows' % (c, diff))
        # show first 3 examples
        n = 0
        for x, y in zip(a, b):
            if x[c] != y[c] and n < 3:
                print('      flow=%s batch=%s   feasible=%s   baseline=%s'
                      % (x.get('flow_id'), x.get('batch_id'), x[c], y[c]))
                n += 1
PY
