# Unit checks for the core initial-release allocator (50:50 removed).
#
# Mirrors AdmitBatch()'s core branch and the eta_final rule exactly, so a
# disagreement between this file and the C++ is itself a finding.
#
# Chain being modelled, in source order (cbap-sba.cc AdmitBatch):
#   residual  = availableCapacity                                  (line 190)
#   residual -= sum(appliedRateBps of old flows)   -> C - R_old     (line 198)
#   core mode: residual += rho_init * R_old_observed                (line 244+)
#              clamped to the link capacity
#   legacy   : residual *= newW/(oldW+newW)                         (line 272)
#   grants    = ProgressiveFill(ids, residual)
#
# and the final migration target:
#   eta_final = max(rho_init, eta_base, eta_feasible)
#   R_old_final = (1 - eta_final) * R_old_observed
#   R_new_final = C - R_old_final
import sys

C = 10_000_000_000          # bit/s, bottleneck 84:1
R_OLD_OBS = 8_000_000_000   # background applied rate (its app cap in S3)
N = 64                      # synchronous senders
R_MIN = 100_000_000         # MIN_RATE
ETA_BASE = 0.50


def initial(rho, capacity=C, r_old=R_OLD_OBS, n=N):
    """Core-mode initial allocation. Returns (old_init, new_init, per_flow)."""
    headroom = max(capacity - r_old, 0)          # what AdmitBatch has after :198
    released = int(rho * r_old)
    new_init = min(headroom + released, capacity)
    old_init = r_old - released
    return old_init, new_init, (new_init / n if n else 0)


def legacy(capacity=C, r_old=R_OLD_OBS, n=N, old_w=1.0, new_w=1.0):
    headroom = max(capacity - r_old, 0)
    share = new_w / (old_w + new_w)
    new_init = int(headroom * share)
    return r_old, new_init, (new_init / n if n else 0)


def eta_feasible(capacity=C, r_old=R_OLD_OBS, n=N, r_min=R_MIN):
    return max(0.0, (n * r_min - (capacity - r_old)) / r_old)


def final_targets(rho, capacity=C, r_old=R_OLD_OBS):
    eta_f = max(rho, ETA_BASE, eta_feasible(capacity, r_old))
    old_final = int((1.0 - eta_f) * r_old)
    new_final = capacity - old_final
    return eta_f, old_final, new_final


results = []


def check(name, ok, detail):
    results.append((name, ok, detail))


print('=== core initial-release unit checks ===')
print('  C = %.1f G   R_old_observed = %.1f G   N = %d   R_min = %.0f Mbps'
      % (C / 1e9, R_OLD_OBS / 1e9, N, R_MIN / 1e6))
print('  eta_base = %.2f   eta_feasible = %.4f'
      % (ETA_BASE, eta_feasible()))
print()

# --- the three specified parameter points --------------------------------
EXPECT = {
    0.0: (8.0e9, 2.0e9),
    0.4: (4.8e9, 5.2e9),
    0.6: (3.2e9, 6.8e9),
}
for rho in (0.0, 0.4, 0.6):
    oi, ni, per = initial(rho)
    eo, en = EXPECT[rho]
    ok = abs(oi - eo) < 1e6 and abs(ni - en) < 1e6 and abs(oi + ni - C) < 1e6
    check('rho=%.1f -> old=%.2fG new=%.2fG total=%.2fG' % (rho, oi/1e9, ni/1e9, (oi+ni)/1e9),
          ok, 'expected old=%.2fG new=%.2fG ; per-flow=%.4f Mbps'
              % (eo/1e9, en/1e9, per/1e6))

# --- eta_final must include rho_init ------------------------------------
for rho, exp_eta in ((0.0, 0.55), (0.4, 0.55), (0.6, 0.60)):
    ef, of, nf = final_targets(rho)
    check('rho=%.1f -> eta_final=%.4f' % (rho, ef), abs(ef - exp_eta) < 1e-9,
          'expected %.2f ; old_final=%.2fG new_final=%.2fG per-flow=%.4f Mbps'
          % (exp_eta, of/1e9, nf/1e9, nf/N/1e6))

# --- rho_init must NOT be silently raised by eta_feasible ---------------
oi, ni, per = initial(0.4)
realized_rho = (R_OLD_OBS - oi) / R_OLD_OBS
check('rho_init not overridden by eta_feasible (0.55)',
      abs(realized_rho - 0.4) < 1e-9,
      'requested 0.4000, realized %.4f ; initial per-flow %.4f Mbps is BELOW '
      'final R_min %.0f Mbps by design' % (realized_rho, per/1e6, R_MIN/1e6))

# --- initial per-flow may be below final R_min, but never negative ------
neg = [rho for rho in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
       if min(initial(rho)) < 0]
check('no negative rate at any rho in [0,1]', not neg,
      'checked 0.0..1.0 ; below-final-R_min count at rho=0.4 = %d of %d flows'
      % (N if per < R_MIN else 0, N))

# --- the core path must never apply the 0.5 weight ----------------------
_, ni_core, _ = initial(0.0)
_, ni_leg, _ = legacy()
check('core rho=0 differs from legacy 50:50', ni_core != ni_leg,
      'core new_init=%.2fG vs legacy new_init=%.2fG (legacy halves the headroom)'
      % (ni_core/1e9, ni_leg/1e9))

# --- legacy arm unchanged ----------------------------------------------
lo, ln, lper = legacy()
check('legacy_50_50 reproduces (C-R_old)*0.5', abs(ln - 1.0e9) < 1e6,
      'new_init=%.3fG per-flow=%.4f Mbps (matches measured 15.625)'
      % (ln/1e9, lper/1e6))

# --- work conservation: no capacity hole while the batch has demand ----
holes = [rho for rho in (0.0, 0.4, 0.6) if abs(sum(initial(rho)[:2]) - C) > 1e6]
check('old_init + new_init == C for every rho', not holes,
      'no capacity hole at rho in {0.0, 0.4, 0.6}')

# --- fairness inside the batch -----------------------------------------
_, ni4, per4 = initial(0.4)
check('ProgressiveFill splits the batch share equally',
      abs(per4 * N - ni4) < 1e3,
      '%d x %.4f Mbps = %.4f G' % (N, per4/1e6, per4*N/1e9))

# --- planned-state conservation, the invariant AdmitBatch now asserts ----
# The old check (sum(grants) <= C - R_old_observed) is FALSE by construction in
# core mode -- it was written when the batch could only ever get a subset of the
# headroom, and it aborted rho=0.4/0.6 with "SBA atomic admission violates
# capacity".  What must hold instead is:
#     sum(grants) + (1 - rho_init) * R_old_observed <= C
bad_planned = []
bad_stale = []
for rho in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    oi, ni, _ = initial(rho)
    released = int(rho * R_OLD_OBS)
    retained = R_OLD_OBS - released
    if ni + retained > C + N:            # +N tolerates per-flow floor()
        bad_planned.append(rho)
    if ni > C - R_OLD_OBS:               # the stale invariant
        bad_stale.append(rho)
check('planned conservation holds for every rho in [0,1]', not bad_planned,
      'sum(grants) + (1-rho)*R_old <= C at rho in {0.0..1.0}')
check('the stale invariant is genuinely false for rho>0',
      bad_stale == [0.2, 0.4, 0.6, 0.8, 1.0],
      'sum(grants) > C-R_old at rho=%s -- this is why the run aborted, and why '
      'the check argument was wrong rather than the allocation'
      % (bad_stale,))

# --- the fix must not change the legacy arm -----------------------------
# On the legacy path newBatchResidual = residual * share with share <= 1, so
# checking against newBatchResidual is no weaker than checking against residual.
lo, ln, _ = legacy()
check('legacy: grants still within its own budget', ln <= (C - R_OLD_OBS),
      'new_init=%.3fG <= headroom=%.3fG (check unchanged on this path)'
      % (ln/1e9, (C - R_OLD_OBS)/1e9))

print('  %-52s %s' % ('check', 'detail'))
fail = 0
for name, ok, detail in results:
    print('  [%s] %-50s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print()
print('  %d/%d passed' % (len(results) - fail, len(results)))
print()
print('=== S3 expected trajectory, rho_init = 0.4 ===')
oi, ni, per = initial(0.4)
ef, of, nf = final_targets(0.4)
print('  before admission : old=%.1fG new=0' % (R_OLD_OBS/1e9))
print('  initial sync     : old=%.1fG new=%.1fG  (per-flow %.2f Mbps)'
      % (oi/1e9, ni/1e9, per/1e6))
print('  after migration  : old=%.1fG new=%.1fG  (per-flow %.2f Mbps), eta_final=%.2f'
      % (of/1e9, nf/1e9, nf/N/1e6, ef))
print('  old is monotone non-increasing %.1f -> %.1f G' % (oi/1e9, of/1e9))
print('  new is monotone non-decreasing %.1f -> %.1f G' % (ni/1e9, nf/1e9))
sys.exit(1 if fail else 0)
