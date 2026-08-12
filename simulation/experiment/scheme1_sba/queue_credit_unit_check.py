# Unit checks for the queueing-delay credit control law.
#
# These mirror ComputeDelayCreditBudget() in rdma-hw.cc exactly, in the same
# order and with the same clamps, so a disagreement between this file and the
# C++ is itself a finding.  Running the checks here rather than only in the
# simulator means a broken control law is caught before any cell is launched,
# which is what section 8 of the plan requires.
#
# Usage: python3 queue_credit_unit_check.py
# Exit 0 only if every check passes.
import sys

C = 10_000_000_000          # bit/s
RTT_S = 15.2e-6             # base RTT for this topology (simulator maxRtt)
MTU_ON_WIRE = 1048          # bytes a full RDMA data packet occupies


def q_bytes(delay_s):
    return int(C * delay_s / 8)


def budget(queue_bytes, n_active, target_s, hard_s, horizon_s,
           max_oversub, max_drain, phase='sync', safety_margin=0,
           ecn_threshold=0, burst_seen=True):
    """Returns (total_bps, credit_bps, drain_bps, q_pred, q_hard, phase_out)."""
    q_target = int(C * target_s / 8)
    hard_delay_bytes = int(C * hard_s / 8)
    q_sync_floor = n_active * MTU_ON_WIRE
    q_hard_startup = q_sync_floor + hard_delay_bytes
    if safety_margin > 0 and ecn_threshold > safety_margin:
        q_hard_startup = min(q_hard_startup, ecn_threshold - safety_margin)

    # Phase latch.  Mirrors the C++: the transition needs evidence that the
    # synchronous burst actually formed (burst_seen), otherwise the very first
    # replan -- where the queue is still 0 because the batch's DATA has not
    # reached the bottleneck -- would consume the startup allowance and charge
    # the burst that follows as a NORMAL-phase violation.
    phase_out = phase
    if phase == 'sync' and burst_seen and queue_bytes <= hard_delay_bytes:
        phase_out = 'normal'
    q_hard = hard_delay_bytes if phase_out == 'normal' else q_hard_startup

    credit = 0
    drain = 0
    total = C
    if queue_bytes >= q_hard:
        d = (queue_bytes - q_target) * 8 / horizon_s if horizon_s else 0
        drain = int(min(max_drain * C, d))
        total = C - drain
    elif queue_bytes > q_target:
        d = (queue_bytes - q_target) * 8 / horizon_s if horizon_s else 0
        drain = int(min(d, max_drain * C))
        total = C - drain
    elif queue_bytes < q_target and horizon_s > 0:
        from_target = (q_target - queue_bytes) * 8 / horizon_s
        from_hard = max(q_hard - queue_bytes, 0) * 8 / horizon_s
        cap = max_oversub * C
        c = min(from_target, from_hard, cap)
        allowed = (q_hard - queue_bytes) * 8 / horizon_s
        if c > allowed:
            c = max(0.0, allowed)
        credit = int(c)
        total = C + credit
    total = max(0, int(total))

    q_pred = queue_bytes
    if total > C and horizon_s > 0:
        q_pred = queue_bytes + int((total - C) * horizon_s / 8)
    return total, credit, drain, q_pred, q_hard, phase_out


TARGET = 0.50 * RTT_S       # 9500 B
HARD = 1.00 * RTT_S         # 19000 B
H = 5e-6                    # control epoch, 5 us (CBAP_CONTROL_EPOCH_US)
OVERSUB = 0.20
DRAIN = 0.20

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


# 1. q = 0 with a positive target must oversubscribe.
t, c, d, qp, qh, ph = budget(0, 64, TARGET, HARD, H, OVERSUB, DRAIN)
check('1 q=0 -> total_budget > C', t > C,
      'total=%.3f G credit=%.3f G (C=%.0f G)' % (t/1e9, c/1e9, C/1e9))

# 2. q = q_target must give exactly C.
qt = q_bytes(TARGET)
t, c, d, qp, qh, ph = budget(qt, 64, TARGET, HARD, H, OVERSUB, DRAIN)
check('2 q=q_target -> total_budget == C', t == C and c == 0 and d == 0,
      'total=%.3f G credit=%d drain=%d' % (t/1e9, c, d))

# 3. q > q_target must drain (total < C).
t, c, d, qp, qh, ph = budget(qt + 2000, 64, TARGET, HARD, H, OVERSUB, DRAIN)
check('3 q>q_target -> total_budget < C and drain>0', t < C and d > 0 and c == 0,
      'total=%.3f G drain=%.3f G' % (t/1e9, d/1e9))

# 4. q >= q_hard must give zero credit.
#    Use the NORMAL phase, where q_hard is the 1-RTT bound.
t, c, d, qp, qh, ph = budget(q_bytes(HARD) + 1, 64, TARGET, HARD, H,
                             OVERSUB, DRAIN, phase='normal')
check('4 q>=q_hard -> credit == 0 and total < C', c == 0 and t < C,
      'credit=%d total=%.3f G q_hard=%d' % (c, t/1e9, qh))

# 5. The credit must never push the predicted queue past the bound.
#    Stated against max(q_hard, q): where the measured queue already exceeds the
#    bound the controller grants no credit and cannot retroactively fix it; what
#    it owes is that crediting never makes the prediction worse than what it
#    found.  Checked separately: whenever credit > 0, the prediction must be
#    within the bound outright.
worst = None
credit_worst = None
for q in range(0, q_bytes(HARD) + 4000, 250):
    for ph0 in ('sync', 'normal'):
        t, c, d, qp, qh, pho = budget(q, 64, TARGET, HARD, H,
                                      OVERSUB, DRAIN, phase=ph0)
        if qp > max(qh, q) + 1:
            worst = (q, qp, qh, ph0)
        if c > 0 and qp > qh + 1:
            credit_worst = (q, qp, qh, ph0, c)
check('5a credit never worsens the prediction past the bound', worst is None,
      'ok across sweep' if worst is None else 'violated at %s' % (worst,))
check('5b when credit>0, q_predicted <= q_hard', credit_worst is None,
      'ok across sweep' if credit_worst is None
      else 'violated at %s' % (credit_worst,))

# 6. disabled credit must reproduce strict conservation.
#    Modelled by horizon 0 / target 0, which is what enable=0 does in C++.
t, c, d, qp, qh, ph = budget(0, 64, 0.0, 0.0, 0.0, 0.0, 0.0)
check('6 credit disabled -> total == C exactly', t == C and c == 0 and d == 0,
      'total=%.3f G' % (t/1e9))

# 7. the sync-burst allowance is one-shot and must not be a standing target.
q_sync = 64 * MTU_ON_WIRE
t1, c1, d1, qp1, qh1, ph1 = budget(q_sync, 64, TARGET, HARD, H, OVERSUB, DRAIN,
                                   phase='sync')
# still in sync phase (q_sync=67072 > 19000), so bound is startup...
startup_bound = q_sync + q_bytes(HARD)
# ...and because q_sync > q_target the controller must DRAIN, not credit.
check('7 sync burst: bound is startup but controller drains',
      qh1 == startup_bound and c1 == 0 and t1 < C,
      'q_hard=%d credit=%d total=%.3f G' % (qh1, c1, t1/1e9))

# 8. latch: once the burst has been seen and the queue falls back, phase sticks.
t, c, d, qp, qh, ph = budget(q_bytes(HARD) - 1, 64, TARGET, HARD, H,
                             OVERSUB, DRAIN, phase='sync', burst_seen=True)
check('8 latch to NORMAL after burst seen and q<=1RTT',
      ph == 'normal' and qh == q_bytes(HARD),
      'phase=%s q_hard=%d' % (ph, qh))

# 9. THE DEFECT-1 REGRESSION: at the first replan the queue is still 0 because
#    the batch's DATA has not reached the bottleneck.  The link must remain in
#    SYNC_BURST, keeping the startup allowance for the burst that is about to
#    form.  The earlier implementation latched here and then charged the burst
#    as a NORMAL-phase violation.
t, c, d, qp, qh, ph = budget(0, 64, TARGET, HARD, H, OVERSUB, DRAIN,
                             phase='sync', burst_seen=False)
check('9 first replan at q=0 stays in SYNC_BURST',
      ph == 'sync' and qh == 64 * MTU_ON_WIRE + q_bytes(HARD),
      'phase=%s q_hard=%d (startup bound retained)' % (ph, qh))

print('=== queueing-delay credit unit checks ===')
print('  C=%.0f Gbps  base RTT=%.1f us  H=%.1f us' % (C/1e9, RTT_S*1e6, H*1e6))
print('  q_target(0.50 RTT)=%d B  q_hard(1.00 RTT)=%d B  q_sync_floor(64)=%d B'
      % (q_bytes(TARGET), q_bytes(HARD), 64 * MTU_ON_WIRE))
print('  q_hard_startup = %d + %d = %d B (%.2f RTT)'
      % (64 * MTU_ON_WIRE, q_bytes(HARD), 64 * MTU_ON_WIRE + q_bytes(HARD),
         (64 * MTU_ON_WIRE + q_bytes(HARD)) * 8 / C / RTT_S))
print()
fail = 0
for name, ok, detail in results:
    print('  [%s] %-52s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print()
print('  %d/%d passed' % (len(results) - fail, len(results)))
sys.exit(1 if fail else 0)
