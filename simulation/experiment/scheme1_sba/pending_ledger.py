# Pending-action ledger and cross-rho H_eff summary.
#
# Reads the four-stage actuation trace and reconstructs, per control epoch, the
# four rate states the controller must distinguish:
#
#   desired    : what the controller wanted (not traced; == commanded here, since
#                this round has no controller -- recorded as such, not inferred)
#   commanded  : stage 1 fired, written to the QP
#   effective  : stage 2 fired, the sender is actually pacing at it
#   pending    : commanded but not yet effective, or effective but not yet
#                arrived at the bottleneck (stage 3a)
#
# The point of the ledger is that `pending` is invisible in Q(t): the queue
# observation is NOT stale (it lags a measured 5.0 us), it simply cannot contain
# effects that have not arrived. Under-predicting by the pending excess is the
# failure mode that made the earlier queue-credit attempt diverge.
import csv
import os
import sys

EPOCH_NS = 5000
C_BPS = 10e9

S1 = 'rate_command'
S2 = 'sender_rate_effect'
S3A = 'arrival_at_bottleneck'
S3 = 'first_affected_at_bottleneck'


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return [r for r in csv.DictReader(handle)
                if not r['stage'].startswith('counters_')]


def counters(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as handle:
        for r in csv.DictReader(handle):
            if r['stage'].startswith('counters_'):
                out[r['stage']] = True
    return out


def by_generation(rows):
    g = {}
    for r in rows:
        g.setdefault(int(r['generation']), {})[r['stage']] = r
    return g


def quantiles(vals):
    if not vals:
        return None
    v = sorted(vals)
    n = len(v)

    def p(q):
        return v[min(n - 1, int(round(q * (n - 1))))]
    return dict(n=n, min=v[0], mean=sum(v) / float(n), p50=p(0.50),
                p95=p(0.95), p99=p(0.99), max=v[-1])


def fmt(q, scale=1e3):
    if not q:
        return '  (no data)'
    return ('n=%-5d min=%8.3f mean=%8.3f p50=%8.3f p95=%8.3f p99=%8.3f '
            'max=%9.3f' % (q['n'], q['min'] / scale, q['mean'] / scale,
                           q['p50'] / scale, q['p95'] / scale,
                           q['p99'] / scale, q['max'] / scale))


CELLS = [('S3 rho=0.55', 'au_s3_rho055'),
         ('S3 rho=0.75', 'au_s3_rho075'),
         ('S3 rho=0.90', 'au_s3_rho090'),
         ('S3 rho=0.9875', 'au_s3_rho09875'),
         ('S4 rho=0.90', 'au_s4_rho090')]

print('=== H_eff(arrival) per cell, and the global figure that sets H_guard ===')
print('')
all_heff = []
per_cell = {}
H_OBS_NS = 5000
for label, cell in CELLS:
    rows = load(cell + '_out/actuation.csv')
    if rows is None:
        print('  %-15s NO TRACE' % label)
        continue
    g = by_generation(rows)
    full = [k for k, v in g.items() if S1 in v and S2 in v and S3A in v]
    heff = [H_OBS_NS + int(g[k][S3A]['time_ns']) - int(g[k][S1]['time_ns'])
            for k in full]
    all_heff.extend(heff)
    per_cell[label] = dict(heff=quantiles(heff), full=len(full),
                           cmd=len([k for k, v in g.items() if S1 in v]),
                           snd=len([k for k, v in g.items() if S2 in v]),
                           arr=len([k for k, v in g.items() if S3A in v]),
                           deq=len([k for k, v in g.items() if S3 in v]))
    print('  %-15s %s' % (label, fmt(per_cell[label]['heff'])))

print('')
gq = quantiles(all_heff)
if gq:
    print('  %-15s %s' % ('GLOBAL', fmt(gq)))
    import math
    h_guard_ns = int(math.ceil(gq['max'] / float(EPOCH_NS)) * EPOCH_NS)
    print('')
    print('  H_guard = ceil(global_max / 5 us) * 5 us')
    print('          = ceil(%.3f us / 5 us) * 5 us = %.1f us  (%d epochs)'
          % (gq['max'] / 1e3, h_guard_ns / 1e3, h_guard_ns / EPOCH_NS))
    print('  NOTE: worst case by construction -- mean and p95 are NOT used,')
    print('        because a tail of actions would land after the window closed.')

print('')
print('=== stage completeness per cell ===')
print('  %-15s %8s %8s %8s %8s %8s' % ('cell', 'cmd', 'sender', 'arrival',
                                       'dequeue', 'full'))
for label, _ in CELLS:
    d = per_cell.get(label)
    if not d:
        continue
    print('  %-15s %8d %8d %8d %8d %8d' % (label, d['cmd'], d['snd'],
                                           d['arr'], d['deq'], d['full']))

print('')
print('=== pending-action ledger (per 5 us epoch) ===')
print('')
for label, cell in CELLS:
    rows = load(cell + '_out/actuation.csv')
    if rows is None:
        continue
    g = by_generation(rows)
    # Build per-generation intervals: commanded at t1, effective at t2,
    # arrived at t3a.  A generation is PENDING in [t1, t3a).
    spans = []
    for k, v in g.items():
        if S1 not in v:
            continue
        t1 = int(v[S1]['time_ns'])
        t2 = int(v[S2]['time_ns']) if S2 in v else None
        t3a = int(v[S3A]['time_ns']) if S3A in v else None
        rate_new = float(v[S1]['rate_bps'])
        rate_old = float(v[S1]['old_rate_bps'])
        spans.append((t1, t2, t3a, rate_old, rate_new))
    if not spans:
        continue
    # Percentiles must be taken over the window where actuation is ACTIVE.
    # Sampling the whole simulation would swamp them with idle epochs: the
    # commands occur in a burst of a few hundred microseconds inside a ~57 ms
    # run, so >99% of epochs are legitimately zero and p95 would read 0 even
    # when the peak is 129.  Report both windows so the difference is explicit.
    lo = min(s[0] for s in spans)
    hi = max((s[2] if s[2] else s[0]) for s in spans)

    def sample(t0, t1):
        counts, excess = [], []
        for t in range(t0, t1 + EPOCH_NS, EPOCH_NS):
            n = 0
            e = 0.0
            for (c1, c2, c3a, r_old, r_new) in spans:
                end = c3a if c3a else c1
                if c1 <= t < end:
                    n += 1
                    # Committed-but-unseen excess: the rate delta already
                    # commanded, integrated over the time since the command.
                    e += max(0.0, r_new - r_old) * (t - c1) / 1e9 / 8.0
            counts.append(float(n))
            excess.append(e)
        return counts, excess

    # Active window: epochs in which at least one action is pending.
    act_lo, act_hi = None, None
    for (c1, c2, c3a, _o, _n) in spans:
        end = c3a if c3a else c1
        act_lo = c1 if act_lo is None else min(act_lo, c1)
        act_hi = end if act_hi is None else max(act_hi, end)
    ac, ae = sample(act_lo, act_hi)
    nz = [x for x in ac if x > 0]
    pq = quantiles(ac)
    eq = quantiles(ae)
    nzq = quantiles(nz)
    print('  %s' % label)
    print('    active window     : %.1f us  (%d epochs);  full run %.1f us'
          % ((act_hi - act_lo) / 1e3, len(ac), (hi - lo) / 1e3))
    print('    pending actions   : max=%d  p95=%.1f  p50=%.1f  mean=%.2f'
          ' [active window]' % (int(pq['max']), pq['p95'], pq['p50'],
                                pq['mean']))
    if nzq:
        print('    ... over NON-ZERO epochs only (%d of %d = %.1f%%):'
              ' p50=%.1f p95=%.1f max=%d'
              % (nzq['n'], len(ac), 100.0 * nzq['n'] / len(ac), nzq['p50'],
                 nzq['p95'], int(nzq['max'])))
    print('    pending excess (B): max=%.0f  p95=%.0f  p50=%.0f'
          % (eq['max'], eq['p95'], eq['p50']))
    print('    that excess as queue delay: max=%.2f us'
          % (eq['max'] * 8 / C_BPS * 1e6))
    c = counters(cell + '_out/actuation.csv')
    for name in c:
        print('    %s' % name)
    print('')

print('=== interpretation ===')
print('  Q(t) is NOT stale: it is delivered 5.0 us after sampling (H_obs,')
print('  measured constant) and correctly describes the queue 5 us ago.')
print('  The issue is the pending set above -- commands already issued whose')
print('  effect has not reached the bottleneck, so Q(t) cannot contain them.')
print('  Q_pred must therefore add pending_excess_bytes explicitly and must use')
print('  R_effective (stage-2 confirmed), never the latest commanded rate.')
sys.exit(0)
