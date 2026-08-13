# CBAP-SBA Core Initial-Release — Preflight Report

Scope: shrink CBAP-SBA back to a clear core capacity-handover algorithm. The
queueing-delay-credit / rate-lease direction is paused, not deleted. This report
covers the implementation, what was removed, the one correctness bug found and
fixed, and the small-scale verification (4 S3 cells + 1 S4 cell).

**Status: COMPLETE.** All 5 cells ran (4× S3 + 1× S4), 64/64 incast completed in
every one, acceptance 18/18 on S3 rho=0.40 and 18/18 on S4 rho=0.40. One
correctness bug was found and fixed during the round (section 3), and four
extraction defects in the analysis script were found and fixed before any number
here was trusted (section 7). **Read section 6b before citing any of it** — the
implementation is correct but `rho_init` is functionally inert in both scenarios,
and the one measured improvement does not come from the initial release.

---

## 1. Environment and version protection

| Item | Value |
|---|---|
| Branch | `cbap-queue-delay-credit` |
| pg=3 base commit | `3050a844dd5356f29851b8e6acb766ee7413de1a` |
| Queue-credit archive commit | `95160dcf83631c27a579ef0ab47750289491986f` |
| Container | `hpcc-build` (ubuntu:20.04, g++-7 7.5.0, python2.7.18) |
| Mount | `/workspaces/yunxiao` → `/work` |

The queue-credit work was committed *before* this change with the message
`EXPERIMENTAL, NOT VALID: queueing-delay credit and its failed acceptance`, so it
is preserved and searchable but cannot be mistaken for a validated result. The
commit message records both failure classes (`INVALID_QUEUE_CREDIT_WIRING_BUG`,
`PERSISTENT_RATE_CREDIT_WITHOUT_LEASE_EXPIRY`) and the two audit corrections that
came out of it.

Nothing was reset, cleaned, checked out over, or deleted. No experiment results
were removed. `migrationEnabled` remains `false` by default.

### pg=3 correction verified intact

Flow-file field 3 is `pg` (`third.cc:1769`: `src dst pg dport size start_time`).
All flows in `s1/s3/s4/s6_flow.txt` carry `pg = 3`. `ShouldSendCN()` and the
switch ECN-marking logic were not touched.

### Queue-credit path proven inert

Two independent gates, both verified in the built source:

- `rdma-hw.cc:1197` — the call gate; `ComputeDelayCreditBudget()` is not invoked
  when `delayCreditEnable` is false.
- `rdma-hw.cc:453` — an early return of the unmodified capacity `C`.

The SYNC_BURST / NORMAL phase machine sits *below* the early return and is
therefore unreachable. Every cell in this round additionally sets
`CBAP_DELAY_CREDIT_ENABLE 0` and has the other 8 credit keys removed from its
config entirely, so the feature is off by configuration as well as by code path.

---

## 2. What the core algorithm now is

Retained (the core capacity-handover mechanism):

1. **Capacity-feasibility constraint** — `eta_feasible` guarantees the post-
   migration plan can seat `N × R_min`.
2. **Nonlinear migration** — the `(1 - eta) · R_old` handover, unchanged.
3. **Replan** — per-epoch recomputation against observed `R_old`.
4. **DCQCN handoff** — `HandoffCbapSbaFlow()` control-return semantics unchanged.

Added:

5. **`CBAP_INITIAL_RELEASE_RATIO` (rho_init, main value 0.40)** — a
   work-conserving initial release.

Removed from the final path:

6. **The 50:50 batch weight**, now reachable only as the `legacy_50_50` control
   arm (`CBAP_CORE_INITIAL_RELEASE 0`).

Off for this entire round: queue credit, rate lease, drain, and the two-phase
1-RTT hard limit.

### The initial release

At admission the old side gives up `rho_init` of the rate it is *actually* using,
and the batch receives the untouched headroom plus exactly that release:

```
released_init = rho_init · R_old_observed
R_new_init    = (C - R_old_observed) + released_init
R_old_init    = R_old_observed - released_init
  =>  R_old_init + R_new_init = C          (no capacity hole)
```

`R_old_observed` is captured per link in `oldAppliedByLink` **before** it is
subtracted from the residual — the allocator needs the rate itself, not only the
headroom that survives it.

### eta_final

```
eta_final = max(rho_init, eta_base, eta_feasible)
```

`rho_init` participates as a floor, so the migration target can never plan the old
side *back up* above what the initial release already took from it. Critically,
the reverse does not happen: a larger `eta_feasible` does **not** silently raise
the realized `rho_init`. That is asserted in the unit test and measured in the
runs (`requested rho` vs `realized rho`).

### Relationship to R_min — stated, not hidden

At rho_init = 0.40 in S3 the initial per-flow rate is **81.25 Mbps**, which is
*below* the final `R_min` of 100 Mbps. This is a deliberate property of the
design, not a violation: `R_min` constrains the post-migration steady state that
`eta_feasible` is built to guarantee, while the initial release is a transient
that trades a lower per-flow floor for immediate work conservation. It is
recorded rather than tuned away.

---

## 3. Correctness bug found and fixed

Two of the four cells (`rho=0.4`, `rho=0.6`) aborted with SIGABRT:

```
terminate called after throwing an instance of 'std::logic_error'
  what():  SBA atomic admission violates capacity
```

The two that passed were `legacy_50_50` and `rho=0.0` — exactly the two where the
release is zero, which localized the fault immediately.

### Root cause: a stale invariant, not an over-allocation

`AdmitBatch` computed grants from `newBatchResidual` but validated against
`residual`:

```cpp
ProgressiveFill(ids, newBatchResidual)   // budget handed out = 5.2 G
CheckConservation(batchId, residual)     // but compared against 2.0 G
```

`CheckConservation` sums only *this batch's* grants, so its real meaning is "did
ProgressiveFill respect the budget it was given." Under the legacy path the two
arguments were interchangeable, because that path multiplies `residual` by a
weight ≤ 1, making `sum(grants) ≤ residual` hold automatically. Core mode
deliberately hands the batch capacity the old side is releasing, so
`sum(grants) ≤ C − R_old_observed` is **false by construction** for every
rho > 0. The unit test now pins this down explicitly: that invariant fails at
rho ∈ {0.2, 0.4, 0.6, 0.8, 1.0}.

So the wrong thing was the argument passed to the check, not the allocation.

### Fix

1. Validate against `newBatchResidual` — the budget ProgressiveFill actually
   received. **Bit-identical on the legacy path**, where `newBatchResidual` is
   what ProgressiveFill got as well.
2. Because (1) alone would leave core mode with *no* capacity safety check, add
   the invariant that genuinely holds — planned-state conservation, per link:

```
sum(batch grants) + (1 - rho_init) · R_old_observed  <=  C
```

At rho = 0.4 this is 5.2 + 4.8 = 10.0 G; at rho = 0.6, 6.8 + 3.2 = 10.0 G. The
tolerance is `ids.size()` bits, covering ProgressiveFill's per-flow `floor()`,
which can only ever round the batch *down*.

The other call site (`rdma-hw.cc:1878`) passes `available` = full link capacity
10 G, so 5.2 G never tripped it; it needed no change.

### A design consequence that is checked, not hidden

During the initial-release transient the batch holds `R_new_init` while the old
side may still *physically* occupy `R_old_observed` until its rate update lands —
transiently 13.2 G > C at rho = 0.4. This is inherent to work-conserving initial
release. It is now covered by the planned-state check above rather than being
silently unasserted. No global `sum(applied) ≤ C` claim is made.

---

## 4. Unit verification — 15/15

`core_initial_release_unit_check.py` mirrors `AdmitBatch`'s core branch and the
`eta_final` rule, so a disagreement between it and the C++ is itself a finding.

| rho_init | R_old init | R_new init | total | per-flow | eta_final |
|---|---|---|---|---|---|
| 0.0 | 8.00 G | 2.00 G | 10.00 G | 31.25 Mbps | 0.55 |
| **0.40** | **4.80 G** | **5.20 G** | **10.00 G** | **81.25 Mbps** | **0.55** |
| 0.6 | 3.20 G | 6.80 G | 10.00 G | 106.25 Mbps | 0.60 |

Also asserted: `rho_init` not overridden by `eta_feasible = 0.55`; no negative
rate for any rho in [0,1]; core ≠ legacy at rho = 0; legacy still reproduces
15.625 Mbps; `R_old + R_new = C` at every rho; equal split within the batch;
planned conservation for all rho; the stale invariant genuinely false for rho > 0;
and the legacy arm unaffected by the check change.

Expected S3 trajectory at rho = 0.40:
`R_old 8.0 → 4.8 → 3.6 G` (monotone non-increasing),
`R_new 0 → 5.2 → 6.4 G` (monotone non-decreasing), `eta_final = 0.55`.

---

## 5. Cells run

Five cells only. **No full 30-cell matrix, no lease, no parameter sweeps.**

| Cell | Scenario | Allocator | rho_init |
|---|---|---|---|
| `cr_s3_legacy5050` | S3 64×1MiB, bg 8.0 G | legacy 50:50 | — |
| `cr_s3_rho000` | S3 | core | 0.0 |
| `cr_s3_rho040` | S3 | core | **0.40** |
| `cr_s3_rho060` | S3 | core | 0.6 |
| `cr_s4_rho040` | S4 64×1MiB, bg 9.5 G | core | **0.40** |

Every config was diffed against its frozen counterpart
(`m_cbapsba_s3_seed2.txt` / `m_cbapsba_s4_seed2.txt`) and is **identical apart
from the new keys**. Topology, flow sizes, start times, seed (2), routing, and
paths are unchanged. Both S3 and S4 use 1 MiB incast flows, so
T_msg = 838.86 µs applies to both.

Binary provenance for the reported round (both hashes recorded, per the standing
requirement that hashing `third` alone is not a sufficient gate):

| Artifact | sha256 (first 16) |
|---|---|
| `build/scratch/third` | `69105306d47f3de5` |
| `build/libns3.18-point-to-point-debug.so` | `4bff8486aa2f15ef` |

All five reported cells were produced by this one binary pair. The two cells that
had aborted on the pre-fix binary were rerun on it, and the two that had passed
were rerun as well, so no reported result mixes binaries.

### Reproduction

```
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
/work/simulation/build/scratch/third cr_s3_legacy5050.txt
/work/simulation/build/scratch/third cr_s3_rho000.txt
/work/simulation/build/scratch/third cr_s3_rho040.txt
/work/simulation/build/scratch/third cr_s3_rho060.txt
/work/simulation/build/scratch/third cr_s4_rho040.txt
python3 core_initial_release_unit_check.py     # 15/15
python3 core_analyse.py                       # the 4 S3 cells, 18/18
python3 core_analyse.py cr_s4_rho040 0.4      # the S4 cell,   18/18
```

---

## 6. Results — 4 S3 cells

All four cells: 64/64 incast completed, 0 admission holds, PFC = 0, retx = 0.

### Capacity trajectory (Gbps)

| Metric | legacy_50_50 | rho=0.0 | **rho=0.40** | rho=0.6 |
|---|---|---|---|---|
| R_old observed (config) | 8.00 | 8.00 | 8.00 | 8.00 |
| R_old initial | *n/a* | 8.00 | **4.80** | 3.20 |
| R_new initial | 1.00 | 2.00 | **5.20** | 6.80 |
| realized rho_init | *n/a* | 0.0000 | **0.4000** | 0.6000 |
| initial per-flow (Mbps) | 15.625 | 31.25 | **81.25** | 106.25 |
| eta_base | 0.50 | 0.50 | 0.50 | 0.50 |
| eta_feasible | 0.55 | 0.55 | 0.55 | 0.55 |
| eta_final | 0.55 | 0.55 | **0.55** | 0.60 |
| R_old final | 3.60 | 3.60 | **3.60** | 3.20 |
| R_new final | 6.40 | 6.40 | **6.40** | 6.80 |
| final per-flow (Mbps) | 100.0 | 100.0 | **100.0** | 106.25 |
| sum final | 10.00 | 10.00 | **10.00** | 10.00 |
| infeasible epochs | 0 | 0 | 0 | 0 |

`R_old initial` / `realized rho_init` are marked *n/a* for the legacy arm on
purpose: both are inferred as `C − sum(grants)`, which is only meaningful when the
split is work-conserving. Legacy deliberately leaves a capacity hole (grants 1.0 G
while the old side holds 8.0 G), so those two cells would read 9.0 G and −0.125
and are not comparable. They are omitted rather than printed.

### Outcome metrics

| Metric | legacy_50_50 | rho=0.0 | **rho=0.40** | rho=0.6 |
|---|---|---|---|---|
| BCT (ms) | 87.9173 | 87.9173 | **87.9173** | 82.7520 |
| FCT mean (ms) | 87.8997 | 87.8997 | **87.8997** | 82.7345 |
| FCT max/min | 1.0004 | 1.0004 | 1.0004 | 1.0004 |
| bg before (Gbps) | 7.641 | 7.641 | 7.641 | 7.641 |
| bg during (Gbps) | 3.269 | 3.269 | **3.269** | 3.058 |
| bg after (Gbps) | 7.575 | 7.575 | 7.575 | 7.576 |
| queue peak (B) | 56592 | 56592 | 56592 | 56592 |
| peak queue delay (µs) | 45.27 | 45.27 | **45.27** | 45.27 |
| peak delay / T_msg | 0.054 | 0.054 | **0.054** | 0.054 |
| util during batch | 0.9825 | 0.9825 | 0.9825 | 1.0004 |

BCT is `last completion − first DATA launch` (2.0879 − 2.0000 s), not
`[1.9 s, last completion]`.

---

## 6a. S4 cell — core rho_init = 0.40, background capped at 9.5 G

S4 is the stronger test of the two, because `R_old_observed` = 9.5 G drives
`eta_feasible` to 0.6211 instead of S3's 0.55. The derived acceptance thresholds
therefore genuinely differ from S3's, which confirms the acceptance logic
generalizes rather than matching memorized S3 values.

| Metric | S4 rho=0.40 | S3 rho=0.40 (for contrast) |
|---|---|---|
| R_old observed (config) | **9.50 G** | 8.00 G |
| R_old initial | **5.70 G** | 4.80 G |
| R_new initial | **4.30 G** | 5.20 G |
| realized rho_init | **0.4000** | 0.4000 |
| initial per-flow (Mbps) | **67.19** | 81.25 |
| eta_base | 0.50 | 0.50 |
| eta_feasible | **0.6211** | 0.5500 |
| eta_final | **0.6211** | 0.5500 |
| R_old final | **3.60 G** | 3.60 G |
| R_new final | **6.40 G** | 6.40 G |
| final per-flow (Mbps) | **100.0** | 100.0 |
| sum final | 10.00 G | 10.00 G |
| infeasible epochs | 0 | 0 |
| BCT (ms) | **87.9173** | 87.9173 |
| FCT mean (ms) | 87.8997 | 87.8997 |
| bg before / during / after (Gbps) | 9.070 / 3.269 / 8.998 | 7.641 / 3.269 / 7.575 |
| bg acked (Gb) | 32.000 | 14.838 |
| queue peak (B) | 58688 | 56592 |
| peak queue delay (µs) | **46.95 (0.056 × T_msg)** | 45.27 (0.054) |
| PFC pause / events | **0 / 0** | 0 / 0 |
| retx | **0 B** | 0 B |
| util mean / in batch | 0.620 / 0.9825 | 0.537 / 0.9825 |

Two observations worth recording:

- **S4 and S3 converge to the same endpoint** (`R_old` 3.60 G, `R_new` 6.40 G,
  100 Mbps/flow) via *different* `eta_final` (0.6211 vs 0.55) from *different*
  `R_old` (9.5 vs 8.0 G). This is `eta_feasible` binding in both cases to seat
  `N × R_min` = 64 × 100 Mbps = 6.4 G — precisely what the capacity-feasibility
  constraint exists to do, and it is doing it from two different starting points.
- **BCT is identical to S3 at 87.9173 ms** despite background load rising from
  8.0 to 9.5 G. Consistent with 6b: the collective runs at `N × R_min`, set by
  feasibility, not by `rho_init` and not by background load.

One cosmetic caveat: in the single-cell S4 invocation the "no 50:50" check prints
`legacy -1.000 Mbps` because no legacy arm ran in that invocation. The check still
evaluates its real condition (67.188 ≠ 15.625 Mbps) and passes; only the
comparison text in the log is meaningless there.

---

## 6b. The finding that qualifies all of the above

**`legacy_50_50`, `rho=0.0` and `rho=0.40` produced bit-identical output**
(`flow_summary.csv` md5 `dd8559bb...` for all three). Initial per-flow rates
differ by 5.2× (15.625 vs 81.25 Mbps) yet BCT, FCT, queue and background are
identical to the last digit. That is not a plausible physical outcome, so it was
traced rather than reported.

### CORRECTED root cause — the MIN_RATE floor, not the replan

An initial version of this section attributed the identical results to "the replan
overwriting the initial release after 5 µs." **That was wrong in mechanism** and is
corrected here; the measured facts below supersede it.

`ReplanCbapSbaMigrationTargets()` writes only `migrationTargetBps` — it does not
write the rate. The rate is advanced by `EvaluateCbapSbaMigration()`
(`rdma-hw.cc:2282`) as a genuine geometric walk,
`next = current + step·(target − current)`, with `migrationRiseBase = 0.30` and a
queue-pressure-skewed `f_inc`. So a one-epoch snap to target is not what happens.

What actually happens is at `rdma-hw.cc:2341`:

```cpp
uint64_t appliedRate = std::max(minRate, (uint64_t)std::floor(nextRate));
```

with `MIN_RATE = 100 Mb/s`, while the migration target is *also* exactly
100 Mbps (6.4 G ÷ 64 flows). Measured trajectory of incast flow 1
(`CBAP_CONTROL_EPOCH_US = 5`, so each sample is one epoch):

| t (s) | legacy_50_50 | rho=0.40 |
|---|---|---|
| 1.999980 | 10000.000 Mbps | 10000.000 Mbps |
| 2.000000 | **15.625** | **81.250** |
| 2.000020 | **100.000** | **100.000** |
| 2.000040 … | 100.000 | 100.000 |

The geometric walk would give 40.9 Mbps from legacy's 15.625 and 86.9 Mbps from
rho=0.40's 81.25. Both are **below the 100 Mbps floor**, so `std::max(minRate, ·)`
clamps them to 100 Mbps in the very first epoch. **The walk runs, but its entire
output range lies under `MIN_RATE`, making it unobservable.** Corroborating:
`rate_transition.csv` contains only its header — zero rate transitions were logged
for any flow at any time.

Consequences:

- `N × R_min` = 64 × 100 Mbps = **6.4 G is simultaneously the migration endpoint
  and the rate floor**, so no trajectory below 6.4 G can be expressed at all. Any
  initial release that grants the batch less than 6.4 G in aggregate is erased on
  the first epoch.
- rho=0.40 grants 5.2 G < 6.4 G → erased. rho=0.0 grants 2.0 G → erased. Legacy
  grants 1.0 G → erased. All three land on 6.4 G, hence bit-identical output.
- rho=0.6 grants 6.8 G > 6.4 G, so it is the **only** arm whose initial release
  survives the floor — which is why it is the only one with a different BCT. Its
  −6.3% comes from clearing the floor, and it also raises `eta_final` to 0.60.

`predicted_delay`-based control cannot be validated in a regime where every
computed rate is floored, which is why this correction matters for the next round
rather than being a footnote.

Supporting evidence:
- Handoff delay is 1.000 ms for all 65 flows in every arm. This is the
  first-feedback latency, **not** a configured bound: `CBAP_HANDOFF_ENABLE 0` and
  no 1 ms constant exists in `rdma-hw.cc`. `release = 2000005000 ns`,
  `first_feedback = 2001005000 ns`.
- Post-handoff rate is 100 Mbps in both legacy and rho=0.40 — the SBA grant does
  not survive handoff.
- The link is saturated (`util = 1.0061`, queue 5–56 KB) from t = 2.00002 s in
  both arms, i.e. within ~20 µs, regardless of the initial grant.
- The remaining 7 replan epochs all fall in the 30 µs completion tail
  (`new_flow_count` 58→50→40→32→22→13→4), so there is no mid-collective replan
  for the initial release to interact with.

### What this does and does not license

- The implementation is **correct**: 18/18 acceptance on both S3 and S4,
  `realized rho = 0.4000` exactly in both, work-conserving, monotone, feasibility
  satisfied at every epoch.
- But **`rho_init` is functionally inert in both scenarios.** Its authority window
  is 5 µs against an 87.9 ms collective (`authority / BCT = 0.0001`, emitted as a
  metric so this cannot be overlooked in future rounds). It must not be presented
  as a knob that improves BCT, and the rho=0.6 improvement must not be attributed
  to the initial release — it comes from `eta_final`.
- S4 confirms this independently: raising background load from 8.0 to 9.5 G leaves
  BCT bit-identical at 87.9173 ms, because the collective rate is set by
  `eta_feasible` seating `N × R_min`, not by the initial split.
- No parameter was changed to make this look better. The finding is reported as
  measured.

### Open design decision (not taken unilaterally)

Two defensible responses, and they are not equivalent in scope:

1. **Accept the current positioning** — the initial release guarantees work
   conservation at t=0, and the steady state is owned by `eta_final`. `rho_init`
   is then part of design completeness (no capacity hole at admission), not a
   performance knob. Nothing further to implement.
2. **Give the initial release a holding period** before the replan overwrites it
   (e.g. bounded by 1 RTT or by first actionable feedback).

Recommendation: **(1)**. Option (2) is, structurally, a time-limited rate
authority — the same class of mechanism as the rate lease that was just paused,
and it would reintroduce the expiry/refresh semantics that direction failed on.
Deferred to the user; no code was written for either.

---

## 7. Acceptance — 18/18 on S3 and 18/18 on S4

Thresholds are derived per cell from that cell's own `R_old_observed` and the
trace's own `eta_final`, not from hardcoded numbers — which is why the S3 and S4
columns differ.

| Check | S3 rho=0.40 | S4 rho=0.40 |
|---|---|---|
| initial old = (1−rho)·R_old | PASS — 4.800 G | PASS — 5.700 G |
| initial new = C − initial old | PASS — 5.200 G | PASS — 4.300 G |
| realized rho ≈ 0.40 | PASS — 0.4000 | PASS — 0.4000 |
| no 50:50 on the core path | PASS — 81.250 vs 15.625 Mbps | PASS — 67.188 Mbps |
| eta_final == max(rho, eta_base, eta_feasible) | PASS — 0.5500 = max(0.40, 0.50, 0.5500) | PASS — 0.6211 = max(0.40, 0.50, 0.6211) |
| final old = (1−eta_final)·R_old | PASS — 3.600 G | PASS — 3.600 G |
| final new | PASS — 6.400 G | PASS — 6.400 G |
| R_old monotone non-increasing (init→final) | PASS — 4.800 → 3.600 G | PASS — 5.700 → 3.600 G |
| R_new monotone non-decreasing (init→final) | PASS — 5.200 → 6.400 G | PASS — 4.300 → 6.400 G |
| R_old target non-increasing, all full-batch epochs | PASS | PASS |
| R_new target non-decreasing, all full-batch epochs | PASS | PASS |
| plan row is the handover, not the tail | PASS — n=64, r_old=8.000 G | PASS — n=64, r_old=9.500 G |
| background flow excluded from the batch | PASS — 64 flows; bg granted 10 G separately | PASS — 64 flows |
| sum(target) ≈ C | PASS — 10.000 G | PASS — 10.000 G |
| 64/64 incast completed | PASS | PASS |
| PFC = 0 | PASS — 0 ns, 0 events | PASS — 0 ns, 0 events |
| retx = 0 | PASS — 0 B | PASS — 0 B |
| peak queue delay ≤ T_msg (838.86 µs) | PASS — 45.27 µs (0.054×) | PASS — 46.95 µs (0.056×) |

### Extraction defects found and fixed before these numbers were trusted

The first extraction pass produced physically impossible values (negative
`R_old initial`, `R_new initial` = 15.2 G on a 10 G link, `realized rho` = 1.65,
`eta_feasible` = −6.01). None were simulator results; all four were defects in
`core_analyse.py`, fixed and re-run:

1. **SBA batch 0 is the background flow** (flow_id 0, granted its own 10 G max,
   uncapped by SBA). Summing it with batch 1 gave 15.2 G of "batch" grants and
   drove `R_old initial` negative. The incast batch is batch 1, flow ids 1..64.
2. **The background flow is flow_id 0, not 65** — 65 is its *source host*. The
   `flow_summary` and timeseries filters were both keyed on the wrong field.
3. **The eta trace's last row is the tail, not the handover** (t = 2.0879 s, 4
   flows left, `r_old` decayed to 1.37 G). Reading it reported `eta_feasible` =
   −6.01, a legitimate pre-clamp value for that row. The handover row is the first
   epoch with `new_flow_count == 64`. An explicit acceptance check now pins this.
4. **Timeseries `time` is in seconds, not ns** (first row `1e-05`, last `2.99999`
   for a 3.0 s run), so every `/1e9` window was empty — which is why background
   and in-batch queue metrics were blank.

Scenario constants are now read from each cell's own config rather than
hardcoded, because S4 caps background at 9.5 G where S3 uses 8.0 G, and the
acceptance thresholds are derived from `R_old` and the trace's own `eta_final`
rather than from memorized values.

## 8. Limitations and what is deliberately not claimed

- This is a 5-cell verification of a mechanism, **not** a paper result. No claim
  is made about CBAP-SBA versus any baseline from this round; the baselines were
  not rerun and are not part of these cells.
- **`rho_init` is not shown to improve anything.** Both scenarios measured it as
  inert (5 µs authority, 0.0001 of BCT). The only BCT difference observed in the
  round (rho=0.6, −6.3%) is attributable to `eta_final` rising to 0.60, not to the
  initial release. Presenting rho_init as a performance knob on this evidence
  would be unsupported.
- Only one seed (2) per cell, consistent with the established determinism
  argument for this simulator; no confidence intervals are computed or implied.
- Both S3 and S4 use 64 senders and 1 MiB messages. Nothing here speaks to other
  batch sizes or message sizes, and in particular the S5 long-collective limit is
  untouched by this round.
- The queue-credit direction is paused with its failure documented, not resolved.
- `rho_init` was not tuned to produce a favourable outcome. 0.40 was specified in
  advance, and 0.0 / 0.6 are bracketing points for the mechanism check, not a
  search for a best value.
- Because the initial per-flow rate at rho = 0.40 is below the final `R_min`, the
  initial release should not be described as guaranteeing `R_min` from t=0. It
  guarantees work conservation from t=0; `R_min` is a post-migration property.
