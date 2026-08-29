# -*- coding: utf-8 -*-
# Hard filters + Pareto frontier over pareto_results.csv.
#
# Hard filters (item 5): PFC = drop = retrans = 0; background goodput retention
# >= 99 % of the best arm; queueing delay must not be SUSTAINED beyond the
# transmission-delay budget.  A brief overshoot is reported with its maximum and
# duration and is NEVER silently counted as a pass.
import csv
import os
import sys

B = '/work/simulation/experiment/scheme1_sba'
SRC = os.path.join(B, 'pareto_results.csv')
OUT = os.path.join(B, 'pareto_frontier.csv')
C = 10e9
# Transmission-delay budget: one Q_abs worth of queue at line rate.
QDELAY_BUDGET_US = 1048575 * 8 / C * 1e6      # 838.86 us
SUSTAINED_US = 100.0                          # longer than this is "sustained"


def f(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return None


rows = list(csv.DictReader(open(SRC)))
if not rows:
    print('empty results')
    sys.exit(1)

bg_best = max([f(r, 'bg_acked_mb') or 0 for r in rows] or [0])
print('=== hard filters ===')
print('  bg reference (best acked) = %.1f MB' % bg_best)
print('  q-delay budget            = %.2f us (Q_abs at line rate)' % QDELAY_BUDGET_US)
print('  "sustained" threshold     = %.0f us contiguous above Q_high' % SUSTAINED_US)
print('')
hdr = ('%-24s %8s %8s %6s %9s %10s %9s %9s  %s'
       % ('cell', 'PFC', 'drop', 'retx', 'bg_ret%', 'qdly_max', 'over_us',
          'longest', 'verdict'))
print(hdr)
print('-' * len(hdr))
for r in rows:
    pfc = int(f(r, 'pfc') or 0)
    dr = int(f(r, 'drops') or 0)
    rx = int(f(r, 'retx') or 0)
    ret = 100.0 * (f(r, 'bg_acked_mb') or 0) / bg_best if bg_best else 0.0
    qmax = f(r, 'qdelay_max_us') or 0.0
    ov = f(r, 'over_qhigh_us') or 0.0
    lg = f(r, 'over_qhigh_longest_us') or 0.0
    fails = []
    if pfc or dr or rx:
        fails.append('PFC/drop/retx')
    if ret < 99.0:
        fails.append('bg_retention<99%%')
    if lg > SUSTAINED_US:
        fails.append('q-delay SUSTAINED %.0fus' % lg)
    if qmax > QDELAY_BUDGET_US:
        fails.append('qdelay_max>%.0fus' % QDELAY_BUDGET_US)
    r['_pass'] = '1' if not fails else '0'
    r['_fail_reason'] = ';'.join(fails)
    # transient overshoot is reported explicitly, never absorbed
    note = ''
    if lg > 0 and lg <= SUSTAINED_US:
        note = ' [transient overshoot max=%.1fus dur=%.0fus]' % (qmax, lg)
    print('%-24s %8d %8d %6d %9.2f %10.2f %9.0f %9.0f  %s%s'
          % (r['cell'], pfc, dr, rx, ret, qmax, ov, lg,
             'PASS' if not fails else 'FAIL:' + r['_fail_reason'], note))

ok = [r for r in rows if r['_pass'] == '1']
print('')
print('passed hard filters: %d of %d' % (len(ok), len(rows)))

# ---- Pareto frontier: minimise BCT and queue p99 simultaneously ----------
def frontier(cands, xk, yk, xlow=True, ylow=True):
    out = []
    for a in cands:
        ax, ay = f(a, xk), f(a, yk)
        if ax is None or ay is None:
            continue
        dominated = False
        for b in cands:
            if b is a:
                continue
            bx, by = f(b, xk), f(b, yk)
            if bx is None or by is None:
                continue
            bx_better = (bx <= ax) if xlow else (bx >= ax)
            by_better = (by <= ay) if ylow else (by >= ay)
            strict = (bx != ax) or (by != ay)
            if bx_better and by_better and strict:
                dominated = True
                break
        if not dominated:
            out.append(a)
    return out


for xk, yk, xl, yl, lbl in (
        ('bct_ms', 'q_p99_b', True, True, 'BCT vs queue p99'),
        ('bct_ms', 'q_max_b', True, True, 'BCT vs queue max'),
        ('batch_goodput_gbps', 'q_p99_b', False, True, 'goodput vs queue p99')):
    fr = frontier(ok, xk, yk, xl, yl)
    print('')
    print('=== Pareto frontier: %s (among hard-filter PASS) ===' % lbl)
    for r in sorted(fr, key=lambda z: f(z, xk) or 0):
        print('  %-24s %s=%.4f  %s=%.0f  util=%s'
              % (r['cell'], xk, f(r, xk), yk, f(r, yk),
                 ('%.6f' % f(r, 'utilisation')) if f(r, 'utilisation') else 'NA'))
    for r in rows:
        r['on_frontier_' + xk + '_' + yk] = '1' if r in fr else '0'

with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('')
print('wrote %s' % OUT)

# ---- empirical check: is the MAX_BOOST dimension inert? -----------------
tw = {r['cell']: r for r in rows}
a, b = tw.get('cap0995_rho090'), tw.get('cap0995_rho090_b040')
if a and b:
    same = all(abs((f(a, k) or 0) - (f(b, k) or 0)) < 1e-9
               for k in ('bct_ms', 'batch_goodput_gbps', 'q_max_b',
                         'utilisation'))
    print('')
    print('=== MAX_BOOST inertness (0.30 vs 0.40, same cap/rho) ===')
    print('  BCT      %.6f vs %.6f' % (f(a, 'bct_ms'), f(b, 'bct_ms')))
    print('  goodput  %.6f vs %.6f' % (f(a, 'batch_goodput_gbps'),
                                       f(b, 'batch_goodput_gbps')))
    print('  q_max    %.0f vs %.0f' % (f(a, 'q_max_b'), f(b, 'q_max_b')))
    print('  verdict  %s' % ('INERT (identical) -- boost is forced to 0 under '
                             'steadyCapEnable, rdma-hw.cc:938'
                             if same else 'NOT inert, values differ'))
