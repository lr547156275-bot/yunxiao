# CBAP-SBA before vs after the capacity-feasibility floor, all six scenarios.
# Both sides come from completed 30-cell matrices; nothing is re-simulated.
import csv, os
BASE = '/work/simulation/experiment/scheme1_sba'
NEW  = os.path.join(BASE, 'final_report', 'final_results.csv')
OLD  = os.path.join(BASE, 'final_report_pre_freeze', 'final_results.csv')
OUT  = os.path.join(BASE, 'paper_data')

def load(p):
    d = {}
    if not os.path.exists(p): return d
    for r in csv.DictReader(open(p)):
        d[(r['scenario_tag'], r['algorithm'])] = r
    return d

new, old = load(NEW), load(OLD)
if not old:
    print('pre-freeze results absent; skipping before/after'); raise SystemExit(0)

TAGS = ['s1','s2','s3','s6','s4','s5']
KEYS = ['fct_mean_ms','fct_p99_ms','cct_ms','incast_agg_gbps',
        'bg_retention_pct','bg_min_gbps','bg_slowdown',
        'queue_mean_bytes','queue_p99_bytes','queue_peak_bytes',
        'over_qmax_pct','ecn_marks','util_mean','pfc_events','retx_bytes_total']

def num(r, k):
    if r is None: return None
    v = r.get(k, '')
    if v in (None, ''): return None
    try: x = float(v)
    except ValueError: return None
    return None if x != x else x

p = os.path.join(OUT, 'p5_capacity_feasibility_before_after.csv')
with open(p, 'w') as fh:
    w = csv.writer(fh)
    w.writerow(['# CBAP-SBA only: effect of the capacity-feasibility floor eta_eff=max(eta_base,eta_feasible).'])
    w.writerow(['# before = pre-freeze binary 084da1fc (no floor); after = FINAL FREEZE 0156d0ba/0bacef18.'])
    w.writerow(['# Both are complete 30-cell matrices with identical scenarios, seed and ECN/PFC settings.'])
    w.writerow(['scenario','metric','before','after','delta_pct','direction'])
    for t in TAGS:
        o, n = old.get((t,'cbapsba')), new.get((t,'cbapsba'))
        for k in KEYS:
            a, b = num(o, k), num(n, k)
            if a is None or b is None: continue
            if a == 0:
                dp = '' if b == 0 else 'n/a (was 0)'
            else:
                dp = '%.2f' % ((b - a) / a * 100.0)
            if b == a: d = 'unchanged'
            elif b < a: d = 'decreased'
            else: d = 'increased'
            w.writerow([t, k, '%.6f' % a, '%.6f' % b, dp, d])
print('wrote p5_capacity_feasibility_before_after.csv')

# Speedup versus the ECN baselines, stated per scenario (no aggregate claim).
p2 = os.path.join(OUT, 'p6_speedup_vs_baselines.csv')
with open(p2, 'w') as fh:
    w = csv.writer(fh)
    w.writerow(['# Ratio of baseline p99 FCT to CBAP-SBA p99 FCT (>1 means CBAP-SBA faster).'])
    w.writerow(['# HPCC row is <1 in every scenario: CBAP-SBA is SLOWER than HPCC on FCT.'])
    w.writerow(['scenario','baseline','baseline_p99_ms','cbapsba_p99_ms','ratio','cbapsba_faster'])
    for t in TAGS:
        c = num(new.get((t,'cbapsba')), 'fct_p99_ms')
        if c is None: continue
        for a in ['dcqcn','dctcp','timely','hpcc']:
            b = num(new.get((t,a)), 'fct_p99_ms')
            if b is None: continue
            w.writerow([t, a.upper(), '%.6f' % b, '%.6f' % c, '%.4f' % (b/c),
                        'yes' if b/c > 1 else 'NO'])
print('wrote p6_speedup_vs_baselines.csv')
