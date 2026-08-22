# Unit tests for the queue-bounded controller: PERSISTENT ABSOLUTE BOOST TARGET
# with a SINGLE PENDING TRANSITION (method D).
#
# This file is the executable specification. It mirrors the C++ decision function
# exactly; a disagreement between the two is itself a finding.
#
# The earlier version of this file modelled `boost` as a one-shot pulse whose
# effect was integrated over one H_guard window and then implicitly expired. That
# was WRONG and produced a false conclusion (that YELLOW was unreachable without
# lowering SOFT_FRACTION). A persistent absolute target accumulates queue for as
# long as it is held:
#
#   3 Gbps excess -> 375 B/us fill
#   (524288 - 56592) / 375e6 = 1.247 ms to reach soft
#   minus the 175 us brake latency -> YELLOW must engage at ~1.072 ms
#   which is 1.22% of the 87.9 ms collective: ample.
#
# Contract:
#   sumR_target = C + boost_target - drain_target,  both >= 0, never both > 0
#
#   boost is an ABSOLUTE target, not an increment. Once a command is confirmed at
#   the bottleneck it becomes boost_effective and PERSISTS until a new absolute
#   target replaces it. It does NOT expire with H_guard and does NOT revert to C.
#
#   "At most one pending generation" forbids overlapping UNCONFIRMED commands
#   only. It places no limit on how long an already-effective boost is held.
#
#   Q_stop = Q_current + net backlog accrued until the earliest moment a brake
#            command could take effect (from effective rate + the single pending
#            target). Drives the SOFT/pressure decision.
#   Q_safe = Q_stop + packetization_margin. Used ONLY for hard/PFC safety.
#            The margin is applied once, never accumulated.
import sys

C = 10e9
H_GUARD_S = 175e-6
EPOCH_S = 5e-6
MIN_RATE = 100e6
N_FLOWS = 64
ON_WIRE = 1048
APP_HARD_DELAY_S = 838.86e-6
SOFT_FRACTION = 0.5           # NOT changed; method D reaches YELLOW with it
MAX_BOOST = 0.30 * C

HARD_BYTES = APP_HARD_DELAY_S * C / 8.0
SOFT_BYTES = SOFT_FRACTION * HARD_BYTES
TOTAL_FLOOR = N_FLOWS * MIN_RATE + MIN_RATE     # 6.5 G

GREEN, YELLOW, RED = 'GREEN', 'YELLOW', 'RED'


class Controller(object):
    """Persistent absolute boost target with a single pending transition."""

    def __init__(self):
        self.boost_effective = 0.0     # confirmed, persists until replaced
        self.boost_commanded = None    # the pending absolute target, or None
        self.pending_generation = None
        self.generation = 0
        self.drain_target = 0.0
        self.last_reason = ''

    # --- prediction ------------------------------------------------------
    def q_stop(self, q_current):
        """Net backlog until the earliest moment a brake could take effect.

        Uses the EFFECTIVE rate plus the single pending target (if any), since
        both will be in force during the brake latency. Never the desired rate.
        """
        excess_eff = self.boost_effective - self.drain_target
        if self.boost_commanded is not None:
            # The pending target will also be in force for part of the window;
            # take the worse of the two so the brake is never under-estimated.
            excess_pending = self.boost_commanded - self.drain_target
            excess = max(excess_eff, excess_pending)
        else:
            excess = excess_eff
        return max(0.0, q_current + excess * H_GUARD_S / 8.0)

    def q_safe(self, q_current, active_senders, ledger_counted_burst=0.0):
        """Q_stop plus the packetization margin, applied ONCE."""
        margin = max(0.0, active_senders * ON_WIRE - ledger_counted_burst)
        return self.q_stop(q_current) + margin, margin

    # --- one control epoch ----------------------------------------------
    def step(self, q_current, active_senders, pfc_safe,
             ledger_counted_burst=0.0, confirm_pending=False):
        """Recomputing every epoch does NOT mean commanding every epoch."""
        if confirm_pending and self.boost_commanded is not None:
            # Confirmed at the bottleneck: becomes effective and PERSISTS.
            self.boost_effective = self.boost_commanded
            self.boost_commanded = None
            self.pending_generation = None

        qs = self.q_stop(q_current)
        qsafe, margin = self.q_safe(q_current, active_senders,
                                    ledger_counted_burst)

        # SOFT/pressure uses Q_stop. Q_safe is only for hard/PFC safety.
        if qsafe >= HARD_BYTES or qs >= HARD_BYTES:
            zone = RED
        elif qs >= SOFT_BYTES:
            zone = YELLOW
        else:
            zone = GREEN

        desired = self._desired_boost(zone, qs, pfc_safe)
        reason = ''
        self.drain_target = 0.0

        if zone == RED:
            # Preempts: clears any pending boost and drains actively.
            self.boost_effective = 0.0
            self.boost_commanded = None
            self.pending_generation = None
            self.drain_target = min(C - TOTAL_FLOOR,
                                    max(1.0, (qs - SOFT_BYTES) * 8.0
                                        / H_GUARD_S))
            reason = 'red_clamp'
        elif not pfc_safe:
            # PFC veto: independent safety veto, forbids positive boost only.
            self.boost_effective = 0.0
            self.boost_commanded = None
            self.pending_generation = None
            reason = 'pfc_veto'
        elif self.boost_commanded is not None:
            # A pending transition exists: update prediction only, do not
            # issue another command. NOT a no-op on state -- just no command.
            reason = 'pending_inflight'
        elif abs(desired - self.boost_effective) < 1.0:
            reason = 'noop_target_unchanged'
        else:
            # Desired target changed and nothing pending: issue the new
            # ABSOLUTE target (never target += boost).
            self.generation += 1
            self.boost_commanded = desired
            self.pending_generation = self.generation
            reason = 'new_absolute_target'

        self.last_reason = reason
        return dict(zone=zone, q_stop=qs, q_safe=qsafe, margin=margin,
                    boost_desired=desired,
                    boost_commanded=self.boost_commanded,
                    boost_effective=self.boost_effective,
                    drain=self.drain_target,
                    pending_generation=self.pending_generation,
                    reason=reason,
                    sumR_effective=C + self.boost_effective
                    - self.drain_target)

    def _desired_boost(self, zone, qs, pfc_safe):
        if zone == RED or not pfc_safe:
            return 0.0
        if zone == GREEN:
            return MAX_BOOST
        span = HARD_BYTES - SOFT_BYTES
        remaining = max(0.0, HARD_BYTES - qs) / span if span > 0 else 0.0
        return MAX_BOOST * (remaining ** 2)


results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


print('=== controller state machine: persistent absolute boost (method D) ===')
print('  C=%.1f G  H_guard=%.0f us  MAX_BOOST=%.2f C  SOFT_FRACTION=%.2f'
      % (C / 1e9, H_GUARD_S * 1e6, MAX_BOOST / C, SOFT_FRACTION))
print('  soft=%.0f B (%.2f us)   hard=%.0f B (%.2f us)   floor=%.1f G'
      % (SOFT_BYTES, SOFT_BYTES * 8 / C * 1e6, HARD_BYTES,
         HARD_BYTES * 8 / C * 1e6, TOTAL_FLOOR / 1e9))
print('')

# --- reachability: the arithmetic that motivates method D ----------------
fill = MAX_BOOST / 8.0
t_soft = (SOFT_BYTES - 56592.0) / fill
t_yellow = t_soft - H_GUARD_S
check('persistent 0.30C reaches soft in ~1.247 ms',
      abs(t_soft * 1e3 - 1.247) < 0.01,
      '%.3f ms at %.0f B/us fill' % (t_soft * 1e3, fill / 1e6))
check('YELLOW must engage ~1.072 ms (soft minus brake latency)',
      abs(t_yellow * 1e3 - 1.072) < 0.01, '%.3f ms' % (t_yellow * 1e3))
check('time-to-YELLOW is a small fraction of the 87.9 ms collective',
      t_yellow / 87.9173e-3 < 0.02,
      '%.2f%% of BCT' % (100 * t_yellow / 87.9173e-3))

# --- GREEN issues an absolute target, then holds it ----------------------
c = Controller()
r1 = c.step(q_current=56592.0, active_senders=N_FLOWS, pfc_safe=True)
check('GREEN issues a new ABSOLUTE target (not an increment)',
      r1['reason'] == 'new_absolute_target'
      and r1['boost_commanded'] == MAX_BOOST,
      'commanded=%.2f C gen=%s' % (r1['boost_commanded'] / C,
                                   r1['pending_generation']))
r2 = c.step(56592.0, N_FLOWS, True)
check('pending transition blocks a second command',
      r2['reason'] == 'pending_inflight' and r2['pending_generation'] == 1,
      'reason=%s gen=%s' % (r2['reason'], r2['pending_generation']))
r3 = c.step(56592.0, N_FLOWS, True, confirm_pending=True)
check('confirmation clears pending and makes boost EFFECTIVE',
      r3['pending_generation'] is None
      and abs(r3['boost_effective'] - MAX_BOOST) < 1.0,
      'effective=%.2f C pending=%s' % (r3['boost_effective'] / C,
                                       r3['pending_generation']))
check('sumR_effective > C once boost is effective',
      r3['sumR_effective'] > C,
      'sumR=%.2f G' % (r3['sumR_effective'] / 1e9))

# --- the critical property: it PERSISTS ---------------------------------
held = []
for _ in range(300):        # 300 epochs = 1.5 ms, far beyond one H_guard
    rr = c.step(56592.0, N_FLOWS, True)
    held.append(rr['boost_effective'])
check('boost_effective PERSISTS beyond H_guard (no auto-expiry)',
      all(abs(v - MAX_BOOST) < 1.0 for v in held),
      'held %.2f C for %d epochs (%.2f ms) with no command reissued'
      % (MAX_BOOST / C, len(held), len(held) * EPOCH_S * 1e3))
check('no command is reissued while the target is unchanged',
      c.last_reason == 'noop_target_unchanged',
      'reason=%s (recompute != recommand)' % c.last_reason)

# --- Q_stop drives soft; Q_safe only hard/PFC ---------------------------
c2 = Controller()
c2.boost_effective = MAX_BOOST
q_at_yellow = SOFT_BYTES - MAX_BOOST * H_GUARD_S / 8.0
r = c2.step(q_at_yellow + 1000, 0, True)
check('YELLOW entered via Q_stop (not Q_safe)', r['zone'] == YELLOW,
      'Q=%.0f -> Q_stop=%.0f >= soft=%.0f' % (q_at_yellow + 1000,
                                              r['q_stop'], SOFT_BYTES))
c3 = Controller()
c3.boost_effective = MAX_BOOST
r_below = c3.step(q_at_yellow - 50000, N_FLOWS, True)
check('packetization margin does NOT push soft (Q_safe not used for soft)',
      r_below['zone'] == GREEN and r_below['q_safe'] > r_below['q_stop'],
      'Q_stop=%.0f < soft, Q_safe=%.0f (margin %.0f) still GREEN'
      % (r_below['q_stop'], r_below['q_safe'], r_below['margin']))
check('packetization margin applied once, not accumulated',
      c3.q_safe(1000.0, N_FLOWS)[1] == c3.q_safe(1000.0, N_FLOWS)[1]
      == N_FLOWS * ON_WIRE,
      'margin=%.0f B on repeated evaluation' % c3.q_safe(1000.0, N_FLOWS)[1])

# --- YELLOW lowers the absolute target ---------------------------------
c4 = Controller()
c4.boost_effective = MAX_BOOST
ry = c4.step(q_at_yellow + 20000, 0, True)
check('YELLOW issues a LOWER absolute target',
      ry['reason'] == 'new_absolute_target'
      and 0 <= ry['boost_commanded'] < MAX_BOOST,
      'commanded=%.4f C < MAX_BOOST=%.2f C' % (ry['boost_commanded'] / C,
                                               MAX_BOOST / C))
ys = []
c5 = Controller()
c5.boost_effective = MAX_BOOST
for frac in (0.05, 0.25, 0.50, 0.75, 0.95):
    q = SOFT_BYTES + frac * (HARD_BYTES - SOFT_BYTES) \
        - MAX_BOOST * H_GUARD_S / 8.0
    ys.append(c5._desired_boost(YELLOW, c5.q_stop(q), True))
check('YELLOW target decays monotonically toward hard',
      all(ys[i] >= ys[i + 1] for i in range(len(ys) - 1)),
      ' -> '.join('%.4f' % (v / C) for v in ys) + ' C')

# --- RED: boost=0, drain>0, sumR<C, floor respected -------------------
c6 = Controller()
c6.boost_effective = MAX_BOOST
rr = c6.step(HARD_BYTES + 5000, 0, True)
check('RED -> boost_effective forced to 0 and drain>0',
      rr['zone'] == RED and rr['boost_effective'] == 0 and rr['drain'] > 0,
      'boost=%.1f drain=%.3f G' % (rr['boost_effective'], rr['drain'] / 1e9))
check('RED -> sumR < C', rr['sumR_effective'] < C,
      'sumR=%.3f G' % (rr['sumR_effective'] / 1e9))
check('RED drain never breaks the 6.5 G floor',
      rr['sumR_effective'] >= TOTAL_FLOOR - 1,
      'sumR=%.3f G >= %.1f G' % (rr['sumR_effective'] / 1e9,
                                 TOTAL_FLOOR / 1e9))
check('RED preempts a pending generation', rr['pending_generation'] is None,
      'pending cleared, reason=%s' % rr['reason'])

# --- PFC veto ----------------------------------------------------------
c7 = Controller()
c7.boost_effective = MAX_BOOST
rv = c7.step(56592.0, N_FLOWS, pfc_safe=False)
check('PFC veto zeroes boost in GREEN',
      rv['boost_effective'] == 0 and rv['reason'] == 'pfc_veto',
      'boost=%.1f reason=%s' % (rv['boost_effective'], rv['reason']))
c8 = Controller()
c8.boost_effective = MAX_BOOST
rv2 = c8.step(HARD_BYTES + 5000, 0, pfc_safe=False)
check('PFC veto does not block RED drain', rv2['drain'] > 0,
      'drain=%.3f G' % (rv2['drain'] / 1e9))

# --- invariants across a sweep ----------------------------------------
bad = []
for q in (0.0, 100000.0, SOFT_BYTES, HARD_BYTES, HARD_BYTES * 2):
    for pfc in (True, False):
        cc = Controller()
        cc.boost_effective = MAX_BOOST
        d = cc.step(q, N_FLOWS, pfc)
        if d['boost_effective'] > 0 and d['drain'] > 0:
            bad.append((q, pfc))
        if d['boost_effective'] < 0 or d['drain'] < 0:
            bad.append((q, pfc, 'negative'))
check('boost and drain never both non-zero, never negative', not bad,
      'checked 10 (queue, pfc) combinations')

# --- forbidden behaviours -------------------------------------------------
# Absolute-vs-incremental is a BEHAVIOURAL property, so test the behaviour:
# repeatedly re-issuing the same desired target must never stack. (An earlier
# version grepped this file for "target +=", which matched its own description
# text -- a self-referential source grep is not an invariant.)
c_abs = Controller()
c_abs.boost_effective = 0.0
seq = []
for _ in range(10):
    d = c_abs.step(56592.0, 0, True, confirm_pending=True)
    seq.append(d['boost_effective'])
check('boost is absolute: repeated commands never stack',
      all(v <= MAX_BOOST + 1.0 for v in seq) and max(seq) == MAX_BOOST,
      'after 10 confirm cycles boost_effective=%.2f C (never exceeds MAX_BOOST)'
      % (max(seq) / C))
# And a lower target REPLACES rather than subtracting from a running total.
c_rep = Controller()
c_rep.boost_effective = MAX_BOOST
c_rep.boost_commanded = 0.10 * C
c_rep.pending_generation = 99
d_rep = c_rep.step(56592.0, 0, True, confirm_pending=True)
check('a new absolute target REPLACES the effective value',
      abs(d_rep['boost_effective'] - 0.10 * C) < 1.0,
      '0.30C -> commanded 0.10C -> effective %.2fC (replaced, not summed)'
      % (d_rep['boost_effective'] / C))
check('SOFT_FRACTION unchanged at 0.50', SOFT_FRACTION == 0.5,
      'not lowered to force YELLOW')
check('H_guard unchanged at 175 us', abs(H_GUARD_S - 175e-6) < 1e-12,
      '%.0f us' % (H_GUARD_S * 1e6))
check('MAX_BOOST unchanged at 0.30 C', abs(MAX_BOOST - 0.30 * C) < 1.0,
      '%.2f C' % (MAX_BOOST / C))

# --- item 8: the full lifecycle ------------------------------------------
print('')
print('=== lifecycle trace (item 8): pending -> confirmed -> persist -> YELLOW ===')
life = Controller()
q = 56592.0
seen = []
t = 0.0
confirm_at = None
log = []
for i in range(400):
    confirm = (confirm_at is not None and t >= confirm_at)
    d = life.step(q, N_FLOWS if i < 5 else 0, True,
                  confirm_pending=confirm)
    if d['reason'] == 'new_absolute_target' and confirm_at is None:
        confirm_at = t + H_GUARD_S      # confirmed one brake latency later
    if confirm:
        confirm_at = None
    seen.append((d['reason'], d['zone'], d['boost_effective'],
                 d['pending_generation']))
    if len(log) < 6 or d['reason'] == 'new_absolute_target':
        log.append('    t=%7.1f us  %-22s %-6s eff=%.4fC pend=%s Q=%8.0f Q_stop=%8.0f'
                   % (t * 1e6, d['reason'], d['zone'],
                      d['boost_effective'] / C,
                      d['pending_generation'], q, d['q_stop']))
    # queue evolves with the effective excess
    q = max(0.0, q + (d['boost_effective'] - d['drain']) * EPOCH_S / 8.0)
    t += EPOCH_S
for line in log[:14]:
    print(line)
phases = [s[0] for s in seen]
zones = [s[1] for s in seen]
check('lifecycle: command pending observed',
      'pending_inflight' in phases, 'yes')
check('lifecycle: confirmation then persistence',
      any(abs(s[2] - MAX_BOOST) < 1.0 and s[3] is None for s in seen),
      'boost_effective=0.30C with pending=None')
check('lifecycle: reaches YELLOW under sustained boost',
      YELLOW in zones,
      'first YELLOW at epoch %s (%.3f ms)'
      % (zones.index(YELLOW) if YELLOW in zones else '-',
         zones.index(YELLOW) * EPOCH_S * 1e3 if YELLOW in zones else -1))
check('lifecycle: YELLOW issues a lower absolute target',
      any(s[0] == 'new_absolute_target' and s[1] == YELLOW for s in seen),
      'yes')
check('lifecycle: GREEN->YELLOW transition present',
      any(zones[i] == GREEN and zones[i + 1] == YELLOW
          for i in range(len(zones) - 1)), 'yes')

print('')
fail = 0
for name, ok, detail in results:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d passed' % (len(results) - fail, len(results)))
sys.exit(1 if fail else 0)
