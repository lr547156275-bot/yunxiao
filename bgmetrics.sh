set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
import csv, os
# Recompute the background metrics the paper needs, straight from the raw data,
# for every completed cell. This proves the pipeline has what it needs rather
# than waiting for metrics.py at the end.
RELEASE = 1.9
def bg_metrics(stem, bgid='0'):
    p = '%s_out/selected_flow_timeseries.csv' % stem
    if not os.path.exists(p): return None
    s = []
    with open(p) as f:
        for r in csv.DictReader(f):
            if r.get('flow_id') == bgid:
                s.append((float(r['time']), float(r['acked_bytes'])))
    if len(s) < 3: return None
    s.sort()
    # instantaneous rate between consecutive samples
    def rate(t0, t1):
        a = [v for t, v in s if t <= t0]
        b = [v for t, v in s if t <= t1]
        if not a or not b or t1 <= t0: return float('nan')
        return (b[-1] - a[-1]) * 8 / (t1 - t0) / 1e9
    before = rate(RELEASE - 0.5, RELEASE)
    # find where the collective ends: use the last sample as bound
    end = s[-1][0]
    during = rate(RELEASE, min(RELEASE + 0.2, end))
    # minimum over a sliding 1ms window during the collective
    win, mn = [], float('inf')
    pts = [(t, v) for t, v in s if RELEASE <= t <= min(RELEASE + 0.2, end)]
    for i in range(1, len(pts)):
        dt = pts[i][0] - pts[i-1][0]
        if dt > 0:
            r = (pts[i][1] - pts[i-1][1]) * 8 / dt / 1e9
            mn = min(mn, r)
    return dict(before=before, during=during, mn=mn,
                retention=(during/before*100 if before else float('nan')))

for tag in ('s1','s2','s3','s6','s4'):
    print('--- %s ---' % tag)
    for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
        stem = 'm_%s_%s_seed2' % (a, tag)
        if not os.path.exists(stem + '_out/flow_summary.csv'): continue
        m = bg_metrics(stem)
        if m is None:
            print('   %-8s no flow timeseries yet' % a); continue
        print('   %-8s bg before=%6.3f during=%6.3f min=%6.3f retention=%6.2f%%'
              % (a, m['before'], m['during'], m['mn'], m['retention']))
PY
