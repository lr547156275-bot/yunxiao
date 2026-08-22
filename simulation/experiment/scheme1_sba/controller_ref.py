# Reference implementation of the queue-bounded controller (method C:
# continuous signed control across the YELLOW band).
#
# Imported by controller_state_machine_test.py and controller_trace_replay.py so
# the two cannot drift apart. Mirrors RdmaHw::QueueControllerEpoch in C++.
#
# Control law:
#   p     = clamp((Q_stop - Q_soft) / (Q_hard - Q_soft), 0, 1)
#   u     = MAX_BOOST * (1 - p) - MAX_DRAIN * p
#   boost = max(u, 0)      drain = max(-u, 0)      (mutually exclusive)
#
#   GREEN         : boost = MAX_BOOST, drain = 0
#   YELLOW early  : positive boost, decreasing
#   YELLOW late   : drain, increasing
#   RED           : boost = 0, drain = MAX_DRAIN
#
# u is strictly decreasing in Q_stop, so there is no sumR == C fixed point: the
# old design parked at 99.6% of hard because YELLOW's floor was boost = 0.
#
# Q_stop integrates the pending command by its ETA rather than taking a max:
#   tau    = clamp(pending_effect_time - now, 0, H_guard)
#   Q_stop = Q + (R_eff - C)*tau/8 + (R_pending - C)*(H_guard - tau)/8
# with no pending: Q_stop = Q + (R_eff - C)*H_guard/8
C = 10e9
H_GUARD_S = 175e-6
EPOCH_S = 5e-6
MIN_RATE = 100e6
N_FLOWS = 64
ON_WIRE = 1048
APP_HARD_DELAY_S = 838.86e-6
SOFT_FRACTION = 0.5
MAX_BOOST = 0.30 * C

HARD_BYTES = APP_HARD_DELAY_S * C / 8.0
SOFT_BYTES = SOFT_FRACTION * HARD_BYTES
TOTAL_FLOOR = N_FLOWS * MIN_RATE + MIN_RATE      # 6.5 G
MAX_DRAIN = C - TOTAL_FLOOR                      # 3.5 G, from the floor

# Rearm margin: packetization burst + one actuation step. Both already exist;
# no new ratio parameter is introduced.
REARM_MARGIN = N_FLOWS * ON_WIRE + MAX_BOOST * H_GUARD_S / 8.0
REARM_BYTES = SOFT_BYTES - REARM_MARGIN

# Preemption deadband. A pending command may only be replaced by a MEANINGFULLY
# lower target, not by an infinitesimally lower one -- otherwise the continuous
# law refreshes the pending slot every epoch, the actuation ETA is pushed back
# forever, and boost_effective never catches up to the target. Measured: 281 of
# 285 commands were such preemptions, with pending_inflight holding 95.8% of
# epochs.
#
# The quantum is per-flow, because a command re-rates each flow by u/N: the
# smallest change worth actuating moves one on-wire packet per guard window.
# Derived from existing quantities (ON_WIRE, H_GUARD_S); no new ratio.
PREEMPT_DEADBAND = ON_WIRE * 8.0 / H_GUARD_S      # ~47.9 Mbps

GREEN, YELLOW, RED = 'GREEN', 'YELLOW', 'RED'


class Controller(object):
    def __init__(self):
        self.boost_effective = 0.0
        self.drain_effective = 0.0
        self.commanded = None          # signed absolute target u
        self.pending_generation = None
        self.pending_eta_ns = None
        self.generation = 0
        self.descending = False        # a lowering command is in flight
        self.rearm_required = False    # set after a descent confirms
        self.reason = ''

    # --- prediction: pending integrated by ETA, never a max() ------------
    def q_stop(self, q_current, now_ns=0.0, pending_excess=0.0):
        r_eff = self.boost_effective - self.drain_effective
        if self.commanded is None or self.pending_eta_ns is None:
            return max(0.0, q_current + pending_excess
                       + r_eff * H_GUARD_S / 8.0)
        tau = min(max((self.pending_eta_ns - now_ns) / 1e9, 0.0), H_GUARD_S)
        r_pend = self.commanded
        return max(0.0, q_current + pending_excess
                   + r_eff * tau / 8.0
                   + r_pend * (H_GUARD_S - tau) / 8.0)

    def signed_target(self, q_stop_val):
        span = HARD_BYTES - SOFT_BYTES
        p = 0.0 if span <= 0 else (q_stop_val - SOFT_BYTES) / span
        p = max(0.0, min(1.0, p))
        return MAX_BOOST * (1.0 - p) - MAX_DRAIN * p, p

    def step(self, q_current, active_senders, pfc_safe, now_ns=0.0,
             pending_excess=0.0, confirm=False, ledger_counted=0.0):
        if confirm and self.commanded is not None:
            u = self.commanded
            self.boost_effective = max(u, 0.0)
            self.drain_effective = max(-u, 0.0)
            if self.descending:
                # A descent has landed: positive boost stays locked out until
                # Q_stop falls below the rearm line.
                self.rearm_required = True
            self.commanded = None
            self.pending_generation = None
            self.pending_eta_ns = None
            self.descending = False

        qs = self.q_stop(q_current, now_ns, pending_excess)
        margin = max(0.0, active_senders * ON_WIRE - ledger_counted)
        qsafe = qs + margin

        # RED on the SAFE quantity, so it fires before the queue actually
        # crosses hard. No new threshold: Q_safe = Q_stop + deduped margin.
        if qsafe >= HARD_BYTES or not pfc_safe:
            zone = RED
        elif qs >= SOFT_BYTES:
            zone = YELLOW
        else:
            zone = GREEN

        if self.rearm_required and qs < REARM_BYTES:
            self.rearm_required = False

        if zone == RED:
            # Preempts everything, including a pending descent.
            self.commanded = None
            self.pending_generation = None
            self.pending_eta_ns = None
            self.descending = False
            self.boost_effective = 0.0
            self.drain_effective = MAX_DRAIN
            self.reason = 'red_clamp' if pfc_safe else 'pfc_veto'
            return self._out(zone, qs, qsafe, margin, 0.0)

        u, p = self.signed_target(qs)
        desired = u
        # Direction hysteresis: no RE-ACCELERATION while a descent is pending,
        # and none after it lands until Q_stop falls below the rearm line.
        #
        # The lock must HOLD the current target, not force u to zero. An earlier
        # version used min(0, current_u), which clamped u to exactly 0 and
        # created a NEW fixed point (dQ/dt = 0) at whatever queue the descent
        # landed on -- observed frozen at 527,217 B instead of converging to the
        # intended u=0 equilibrium at 766,266 B. Clamping to the current value
        # forbids increases while still allowing the law to command drain when
        # the queue keeps rising.
        if self.descending or self.rearm_required:
            cur_u = self._current_u()
            if desired > cur_u:
                desired = cur_u

        cur = self._current_u()
        if self.commanded is not None:
            # A pending command may only be replaced by a LOWER target.
            if desired < self.commanded - PREEMPT_DEADBAND:
                self._issue(desired, now_ns)
                self.reason = 'lower_target_preempts_pending'
            else:
                self.reason = 'pending_inflight'
        elif abs(desired - cur) < PREEMPT_DEADBAND:
            self.reason = 'noop_target_unchanged'
        else:
            self._issue(desired, now_ns)
            self.reason = 'new_absolute_target'
        return self._out(zone, qs, qsafe, margin, p)

    def _current_u(self):
        return self.boost_effective - self.drain_effective

    def _issue(self, target, now_ns):
        self.generation += 1
        self.commanded = target
        self.pending_generation = self.generation
        self.pending_eta_ns = now_ns + H_GUARD_S * 1e9
        self.descending = target < self._current_u() - 1.0

    def _out(self, zone, qs, qsafe, margin, p):
        return dict(zone=zone, q_stop=qs, q_safe=qsafe, margin=margin, p=p,
                    boost_effective=self.boost_effective,
                    drain_effective=self.drain_effective,
                    commanded=self.commanded,
                    pending=self.pending_generation,
                    reason=self.reason,
                    sumR=C + self.boost_effective - self.drain_effective)
