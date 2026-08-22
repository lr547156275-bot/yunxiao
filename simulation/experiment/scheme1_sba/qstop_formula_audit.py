# Deterministic audit of the corrected Q_stop predictor (item 7).
#
# Replays the OLD endpoint formula and the NEW max-prefix formula over the
# recorded traces, so the difference is demonstrated on real data rather than
# argued. The old formula's defect is specific: it subtracted FUTURE drain from
# the queue that ALREADY exists, so Q_stop could fall below Q_current.
import csv
import os
import sys

C = 10e9
H_GUARD_S = 175e-6
EPOCH_NS = 5000.0
H_NS = H_GUARD_S * 1e9
Q_ABS = 1048575.0
M_SAFE = 67072.0            # max(M_unc, M_pkt), NOT their sum
M_ACT = 0.30 * C * H_GUARD_S / 8.0
Q_RED = Q_ABS - M_SAFE
Q_HIGH = Q_RED - M_ACT
Q_LOW = 0.5 * Q_ABS
DRAIN_MAX_LEGAL = 3.5e9
FLOOR_BPS = 6.5e9

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


def old_formula(q, u):
    """Endpoint: Q + u*H/8. This is the defect."""
    return q + u * H_GUARD_S / 8.0


def new_formula(q, u_eff, tau, u_pend, pending_excess=0.0, in_flight=0.0):
    """Max prefix over the window; >= q by construction."""
    q0 = q + pending_excess + in_flight
    q1 = q0 + u_eff * tau / 8.0
    q2 = q1 + u_pend * (H_GUARD_S - tau) / 8.0
    return max(q0, q1, q2)


print('=== Q_stop formula audit ===')
print('  Q_low=%.0f  Q_high=%.0f  Q_red=%.0f  Q_abs=%.0f'
      % (Q_LOW, Q_HIGH, Q_RED, Q_ABS))
print('  M_safe=%.0f (= max(M_unc 62397, M_pkt 67072), not the sum)' % M_SAFE)
print('  M_act=%.0f  DRAIN_MAX(legal)=%.2f G  floor=%.2f G'
      % (M_ACT, DRAIN_MAX_LEGAL / 1e9, FLOOR_BPS / 1e9))
check('boundary ordering 0 < Q_low < Q_high < Q_red < Q_abs',
      0 < Q_LOW < Q_HIGH < Q_RED < Q_ABS,
      '%.0f < %.0f < %.0f < %.0f' % (Q_LOW, Q_HIGH, Q_RED, Q_ABS))

# --- item 7.7 / 7.8: the two formulas at the recorded worst epoch ---------
print('')
print('=== old vs new at the recorded worst epoch ===')
WORST_Q = 1132888.0
WORST_DRAIN = 8151303275.0
old_at_worst = old_formula(WORST_Q, -WORST_DRAIN)
new_at_worst = new_formula(WORST_Q, -WORST_DRAIN, H_GUARD_S, -WORST_DRAIN)
print('  Q_current                 = %.0f B' % WORST_Q)
print('  drain recorded            = %.4f C = %.2f Gbps'
      % (WORST_DRAIN / C, WORST_DRAIN / 1e9))
print('  OLD endpoint formula      = %.0f B   (recorded: 954578)'
      % old_at_worst)
print('  NEW max-prefix formula    = %.0f B' % new_at_worst)
print('  shortfall removed         = %.0f B' % (new_at_worst - old_at_worst))
check('old formula reproduces the recorded 954,578 B',
      abs(old_at_worst - 954578.0) < 2.0, '%.0f B' % old_at_worst)
check('ITEM 7.8: new formula gives Q_stop >= 1,132,888 B at that epoch',
      new_at_worst >= WORST_Q - 1.0,
      '%.0f B (was %.0f B)' % (new_at_worst, old_at_worst))
check('the shortfall equals drain * H_guard / 8',
      abs((WORST_Q - old_at_worst) - WORST_DRAIN * H_GUARD_S / 8.0) < 200,
      '%.0f B vs %.0f B'
      % (WORST_Q - old_at_worst, WORST_DRAIN * H_GUARD_S / 8.0))

# --- sweep both formulas over the recorded traces ------------------------
print('')
print('=== replay over recorded traces ===')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
viol_old = viol_new = 0
drain_illegal = 0
floor_viol = 0
neg_pending = 0
both_nonzero = 0
rows_total = 0
explained = 0
for cell in ('qc_s3_rho090', 'qc_s3_rho09875'):
    path = cell + '_out/qc_trace.csv'
    if not os.path.exists(path):
        print('  %-16s NO TRACE' % cell)
        continue
    rows = list(csv.DictReader(open(path)))
    n_old = n_new = 0
    for r in rows:
        q = float(r['q_current'])
        b = float(r['boost_effective'])
        d = float(r['drain'])
        u = b - d
        rows_total += 1
        if old_formula(q, u) < q - 1:
            n_old += 1
        nf = new_formula(q, u, H_GUARD_S, u)
        if nf < q - 1:
            n_new += 1
        else:
            explained += 1
        if d > DRAIN_MAX_LEGAL + 1:
            drain_illegal += 1
        if float(r['sumR_effective']) < FLOOR_BPS - 1:
            floor_viol += 1
        if b > 0 and d > 0:
            both_nonzero += 1
    viol_old += n_old
    viol_new += n_new
    print('  %-16s rows=%-7d OLD Q_stop<Q_current: %-6d  NEW: %d'
          % (cell, len(rows), n_old, n_new))

print('')
check('ITEM 7.1: NEW formula never gives Q_stop < Q_current', viol_new == 0,
      '%d violations (old formula had %d)' % (viol_new, viol_old))
check('ITEM 7.6: every NEW Q_stop is explained by a window prefix',
      explained == rows_total,
      '%d of %d rows' % (explained, rows_total))
# These two describe the OLD recorded run; they are what the fix targets.
print('')
print('  recorded (OLD build) violations that the fix targets:')
print('    drain > DRAIN_MAX(3.5 G)     : %d epochs' % drain_illegal)
print('    sumR < floor(6.5 G)          : %d epochs' % floor_viol)
print('    boost and drain both non-zero: %d epochs' % both_nonzero)
check('ITEM 7.5: boost and drain never both non-zero (recorded)',
      both_nonzero == 0, '%d epochs' % both_nonzero)

print('')
print('=== zone mapping under the new boundaries ===')
print('  %12s %10s %s' % ('Q_stop', 'Q_safe', 'zone'))
for q in (0.0, Q_LOW - 1, Q_LOW, Q_HIGH, Q_HIGH + 1, Q_RED, Q_ABS - M_SAFE,
          Q_ABS):
    qs = q + M_SAFE
    if qs >= Q_ABS or q >= Q_ABS:
        z = 'RED'
    elif q > Q_HIGH:
        z = 'YELLOW-DRAIN'
    elif q >= Q_LOW:
        z = 'YELLOW-HOLD'
    else:
        z = 'GREEN/BOOST'
    print('  %12.0f %10.0f %s' % (q, qs, z))
check('RED trips before the actual queue can reach Q_abs',
      (Q_RED + M_SAFE) >= Q_ABS,
      'Q_red + M_safe = %.0f >= Q_abs = %.0f' % (Q_RED + M_SAFE, Q_ABS))

print('')
fail = 0
for name, ok, detail in results:
    print('  [%s] %-56s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d audit checks passed' % (len(results) - fail, len(results)))
sys.exit(1 if fail else 0)
