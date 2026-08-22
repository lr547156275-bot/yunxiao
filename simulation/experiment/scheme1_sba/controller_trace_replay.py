# Trace replay for the signed-control (method C) queue controller.
#
# Two parts:
#   (1) open loop over the five measured audit traces -- invariants on real data
#   (2) closed loop -- the queue responds to the controller, which is the only
#       way YELLOW behaviour can be exercised (the measured traces contain no
#       boost, so they can never leave GREEN)
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from controller_ref import (Controller, C, H_GUARD_S, EPOCH_S, N_FLOWS,
                            SOFT_BYTES, HARD_BYTES, MAX_BOOST, MAX_DRAIN,
                            TOTAL_FLOOR, REARM_BYTES, GREEN, YELLOW, RED)

CELLS = [('S3 rho=0.90', 'au_s3_rho090'),
         ('S3 rho=0.9875', 'au_s3_rho09875'),
         ('S3 rho=0.55', 'au_s3_rho055'),
         ('S3 rho=0.75', 'au_s3_rho075'),
         ('S4 rho=0.90', 'au_s4_rho090')]

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


print('=== controller trace replay: signed control (method C) ===')
print('  soft=%.0f B (%.2f us)  hard=%.0f B (%.2f us)'
      % (SOFT_BYTES, SOFT_BYTES * 8 / C * 1e6, HARD_BYTES,
         HARD_BYTES * 8 / C * 1e6))
print('  MAX_BOOST=%.2fC  MAX_DRAIN=%.2fC  rearm=%.0f B  H_guard=%.0f us'
      % (MAX_BOOST / C, MAX_DRAIN / C, REARM_BYTES, H_GUARD_S * 1e6))
print('')

viol = dict(both=0, neg=0, floor=0, soft_margin=0, veto_boost=0)
total = 0
for label, cell in CELLS:
    path = cell + '_out/pfc_audit.csv'
    if not os.path.exists(path):
        print('  %-15s NO TRACE' % label)
        continue
    ctl = Controller()
    n = 0
    peak = 0.0
    zc = {GREEN: 0, YELLOW: 0, RED: 0}
    with open(path) as handle:
        for row in csv.DictReader(handle):
            t = int(row['time_ns'])
            if t < 2000000000 or t > 2090000000:
                continue
            q = float(row['cbap_egress_queue_bytes'])
            pfc_safe = (row['pfc_guard_state'] == 'SAFE')
            active = N_FLOWS if q > 0 else 0
            confirm = (ctl.pending_generation is not None and n % 35 == 34)
            d = ctl.step(q, active, pfc_safe, now_ns=float(t),
                         confirm=confirm)
            n += 1
            zc[d['zone']] += 1
            peak = max(peak, d['q_stop'])
            if d['boost_effective'] > 0 and d['drain_effective'] > 0:
                viol['both'] += 1
            if d['boost_effective'] < 0 or d['drain_effective'] < 0:
                viol['neg'] += 1
            if d['sumR'] < TOTAL_FLOOR - 1:
                viol['floor'] += 1
            if d['zone'] == YELLOW and d['q_stop'] < SOFT_BYTES:
                viol['soft_margin'] += 1
            if not pfc_safe and d['boost_effective'] > 0:
                viol['veto_boost'] += 1
    total += n
    print('  %-15s epochs=%-6d GREEN=%-6d YELLOW=%-5d RED=%-4d peak Q_stop=%.0f B'
          % (label, n, zc[GREEN], zc[YELLOW], zc[RED], peak))

print('')
check('open loop: covered a non-trivial number of epochs', total > 1000,
      '%d epochs' % total)
check('open loop: boost and drain never both non-zero', viol['both'] == 0,
      '%d' % viol['both'])
check('open loop: never negative', viol['neg'] == 0, '%d' % viol['neg'])
check('open loop: sumR never below the 6.5 G floor', viol['floor'] == 0,
      '%d' % viol['floor'])
check('open loop: YELLOW never entered via the margin alone',
      viol['soft_margin'] == 0, '%d' % viol['soft_margin'])
check('open loop: PFC veto always suppresses positive boost',
      viol['veto_boost'] == 0, '%d' % viol['veto_boost'])

# ---------------- closed loop -------------------------------------------
print('')
print('=== closed loop: sustained batch, queue responds ===')
ctl = Controller()
q = 56592.0
t_ns = 0.0
confirm_at = None
zones = []
qs_hist = []
cmds = []
first_yellow = None
BATCH_END_NS = 40000e3          # 40 ms of batch demand, then it stops
for i in range(12000):          # 60 ms
    # Strictly after the ETA: confirming in the same epoch the command was
    # issued would defeat the single-pending rule and make every epoch a
    # command-and-confirm cycle.
    confirm = (confirm_at is not None and t_ns > confirm_at)
    active = N_FLOWS if (i < 5 and t_ns < BATCH_END_NS) else 0
    d = ctl.step(q, active, True, now_ns=t_ns, confirm=confirm)
    if d['reason'] in ('new_absolute_target',
                       'lower_target_preempts_pending'):
        confirm_at = t_ns + H_GUARD_S * 1e9
        cmds.append((t_ns, d['commanded'], d['zone']))
    if confirm:
        confirm_at = None
    zones.append(d['zone'])
    qs_hist.append(q)
    if d['zone'] == YELLOW and first_yellow is None:
        first_yellow = t_ns / 1e9
    # The queue responds to the EFFECTIVE excess. After the batch ends there is
    # no offered load above C, so it drains.
    if t_ns < BATCH_END_NS:
        rate = d['boost_effective'] - d['drain_effective']
    else:
        rate = -MAX_DRAIN
    q = max(0.0, q + rate * EPOCH_S / 8.0)
    t_ns += EPOCH_S * 1e9

print('  first 8 commands:')
for (tt, u, z) in cmds[:8]:
    print('    t=%9.1f us  u=%+.4fC  %s' % (tt / 1e3, u / C, z))
print('  ... %d commands total over 60 ms' % len(cmds))
qpeak = max(qs_hist)
print('  Q peak = %.0f B (%.2f us) vs hard %.0f B  -> %.1f%% of hard'
      % (qpeak, qpeak * 8 / C * 1e6, HARD_BYTES, 100 * qpeak / HARD_BYTES))

check('closed loop: reaches YELLOW', YELLOW in zones,
      'first YELLOW at %.3f ms' % (first_yellow * 1e3 if first_yellow else -1))
check('closed loop: GREEN -> YELLOW transition present',
      any(zones[i] == GREEN and zones[i + 1] == YELLOW
          for i in range(len(zones) - 1)), 'yes')
check('closed loop: Q_peak < Q_hard', qpeak < HARD_BYTES,
      '%.0f < %.0f B (%.1f%%)' % (qpeak, HARD_BYTES,
                                  100 * qpeak / HARD_BYTES))
# The old defect: parked within 1% of hard and never came down.
check('closed loop: does NOT park near hard (old defect fixed)',
      qpeak < 0.95 * HARD_BYTES,
      'peak %.1f%% of hard (old design parked at 99.6%%)'
      % (100 * qpeak / HARD_BYTES))
mid = [qs_hist[i] for i in range(len(qs_hist))
       if 5e-3 <= i * EPOCH_S <= 35e-3]
check('closed loop: bounded inside YELLOW while the batch persists',
      bool(mid) and max(mid) < HARD_BYTES,
      'Q in [%.0f, %.0f] B over 5-35 ms' % (min(mid), max(mid)) if mid
      else 'no samples')
tail = zones[int(45e-3 / EPOCH_S):]
check('closed loop: returns to GREEN after the batch ends',
      bool(tail) and all(z == GREEN for z in tail[-100:]),
      'last 100 epochs all GREEN' if tail else 'no tail')
# Ping-pong means the target REVERSES DIRECTION repeatedly. Command rate is a
# different thing: a continuous law legitimately re-commands as the queue moves,
# and the single-pending rule already bounds how often that can take effect. An
# earlier version of this check asserted "gaps >= 300 us", which failed on
# monotone descent and would have hidden real oscillation behind a rate metric.
signs = []
for i in range(len(cmds) - 1):
    delta = cmds[i + 1][1] - cmds[i][1]
    signs.append(1 if delta > 0 else (-1 if delta < 0 else 0))
reversals = sum(1 for i in range(len(signs) - 1)
                if signs[i] * signs[i + 1] < 0)
check('closed loop: target is monotone, no direction ping-pong',
      reversals <= max(2, len(signs) // 20),
      '%d direction reversals in %d consecutive command pairs (%.1f%%)'
      % (reversals, max(1, len(signs) - 1),
         100.0 * reversals / max(1, len(signs) - 1)))
# Separately: an effective command must not take effect more than once per
# confirmation, which is what actually bounds actuation.
eff_gaps = [g for g in [cmds[i + 1][0] - cmds[i][0]
                        for i in range(len(cmds) - 1)]]
check('closed loop: command count stays bounded over 60 ms',
      len(cmds) < 2000,
      '%d commands, median gap %.1f us'
      % (len(cmds), sorted(eff_gaps)[len(eff_gaps) // 2] / 1e3
         if eff_gaps else -1))

# ---------------- RED / PFC drain --------------------------------------
print('')
print('=== RED and PFC veto actively drain ===')
cr = Controller()
cr.boost_effective = MAX_BOOST
d = cr.step(HARD_BYTES + 5000, 0, True, now_ns=0.0)
check('RED: boost=0, drain=MAX_DRAIN, sumR<C',
      d['zone'] == RED and d['boost_effective'] == 0
      and abs(d['drain_effective'] - MAX_DRAIN) < 1.0 and d['sumR'] < C,
      'drain=%.2fC sumR=%.3f G' % (d['drain_effective'] / C, d['sumR'] / 1e9))
cv = Controller()
cv.boost_effective = MAX_BOOST
dv = cv.step(56592.0, N_FLOWS, False, now_ns=0.0)
check('PFC veto: RED entered and drains',
      dv['zone'] == RED and dv['drain_effective'] > 0,
      'zone=%s drain=%.2fC reason=%s' % (dv['zone'],
                                         dv['drain_effective'] / C,
                                         dv['reason']))
check('RED fires on Q_safe before Q actually crosses hard',
      Controller().step(HARD_BYTES - 60000, N_FLOWS, True,
                        now_ns=0.0)['zone'] == RED,
      'Q=%.0f (below hard) + margin -> RED' % (HARD_BYTES - 60000))

print('')
fail = 0
for name, ok, detail in results:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d passed' % (len(results) - fail, len(results)))
sys.exit(1 if fail else 0)
