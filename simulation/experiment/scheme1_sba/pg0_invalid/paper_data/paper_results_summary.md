# CBAP-SBA — final paper results summary

Source: `final_report/final_results.csv` (30 cells = 5 algorithms × 6 scenarios,
seed 2), the FINAL FREEZE build, plus the η sweep on S4. Nothing here is
re-simulated; every number is a reorganisation of completed runs.

**Frozen build.** `third` = `0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35`,
`libns3.18-point-to-point-debug.so` = `0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72`,
commit `2ece98e`, toolchain g++-7 7.5.0 / python2.7. All 30 manifests carry both
hashes and that commit — verified 30/30.

**Run quality.** 30/30 cells completed with the full expected incast count and
complete link traces. Across all 30: **PFC events 0, PFC pause 0 ns, drops 0,
retransmission 0 bytes**. `anomalies.md` reports 0 items.

Scenarios (2-tier leaf-spine, 10 Gbps everywhere, bottleneck = the last hop into
the receiver):

| | shape | background | stop |
|---|---|---|---|
| S1 | 16 × 256 KiB | 8 Gbps (80%) | 2.1 s |
| S2 | 64 × 256 KiB | 8 Gbps | 2.5 s |
| S3 | 64 × 1 MiB | 8 Gbps | 3.0 s |
| S6 | dual bottleneck, 30+30 × 256 KiB | 8 Gbps × 2 | 2.5 s |
| S4 | 64 × 1 MiB | 9.5 Gbps (95%) | 5.5 s |
| S5 | 64 × 4 MiB | 8 Gbps | 6.0 s |

---

## 1. Stable gain over DCQCN / DCTCP / TIMELY

Ratio of baseline p99 FCT to CBAP-SBA p99 FCT (`p6_speedup_vs_baselines.csv`):

| scenario | vs DCQCN | vs DCTCP | vs TIMELY |
|---|---|---|---|
| S1 | 2.97× | 2.97× | 3.00× |
| S2 | 3.19× | 3.19× | 3.21× |
| S3 | 3.19× | 3.19× | 3.21× |
| S6 | 2.98× | 2.98× | 2.99× |
| **S4** | **12.77×** | **12.77×** | **12.68×** |
| S5 | 3.21× | 3.21× | 3.23× |

Five scenarios cluster at **2.97–3.23×**; S4 (95 % background) reaches
**12.77×**. Goodput moves the same way — in S4, 0.476 → 6.082 Gbps.

The three ECN baselines are within 0.4 % of each other everywhere. Their weak
result is an arithmetically exact fairness outcome, not a rate-control failure:
in S4 the background flow receives **0 CNPs** while the 64 incast flows absorb
all 9 582, so each incast flow reduces multiplicatively while the background
flow never does.

## 2. FCT disadvantage against HPCC — in every scenario

**HPCC is faster than CBAP-SBA on incast FCT in all six scenarios.** The ratio
(baseline/CBAP-SBA) is below 1 throughout:

| scenario | HPCC p99 (ms) | CBAP-SBA p99 (ms) | ratio | CBAP-SBA slower by |
|---|---|---|---|---|
| S1 | 4.092 | 5.929 | 0.690 | 1.45× |
| S2 | 15.118 | 22.098 | 0.684 | 1.46× |
| S3 | 60.131 | 88.295 | 0.681 | 1.47× |
| S6 | 7.293 | 11.097 | 0.657 | 1.52× |
| S4 | 60.242 | 88.275 | 0.682 | 1.47× |
| S5 | 240.543 | 350.963 | 0.685 | 1.46× |

The consistency (1.45–1.52×) indicates a mechanism difference, not noise. HPCC
starts each flow at line rate and converges downward using per-hop INT
telemetry; CBAP-SBA starts at its admitted grant and climbs. HPCC reaches a
working rate sooner. Goodput reflects the same gap: HPCC 8.90 vs CBAP-SBA 6.08
Gbps in S4.

**No claim is made that CBAP-SBA dominates HPCC.** It does not.

## 3. Background-protection advantage over HPCC

`t3_background_protection.csv`. Retention = throughput during the collective
relative to before:

| scenario | HPCC | CBAP-SBA | advantage |
|---|---|---|---|
| S1 | 96.34 % | 97.24 % | +0.90 pts |
| S2 | 87.11 % | 90.13 % | +3.02 pts |
| S3 | 63.11 % | 74.38 % | **+11.27 pts** |
| S6 | 93.46 % | 95.07 % | +1.61 pts |
| S4 | 63.00 % | 71.03 % | **+8.03 pts** |
| S5 | 30.60 % | 57.09 % | **+26.49 pts** |

Minimum instantaneous throughput is the sharper distinction, because retention
is a mean and hides momentary starvation:

| scenario | HPCC (Gbps) | CBAP-SBA (Gbps) |
|---|---|---|
| S1 | 0.400 | **3.859** |
| S2 | 0.093 | **3.463** |
| S3 | 0.093 | **3.463** |
| S6 | 0.242 | **3.855** |
| S4 | 0.093 | **3.463** |
| S5 | 0.093 | 0.109 |

**HPCC drives the background flow to ≈0.09 Gbps in five of six scenarios**;
CBAP-SBA holds ≥3.46 Gbps in those same five. S5 is the exception (0.109 vs
0.093 — essentially no advantage), consistent with §6.

In S4, where the 4 GB background flow completes, its slowdown is CBAP-SBA
**1.070×** versus HPCC **1.107×**: CBAP-SBA reaches near-HPCC incast latency
while costing the background flow *less* time.

The 100 % retention of DCQCN/DCTCP/TIMELY is **not** protection — their
collectives obtain only 0.48–1.9 Gbps and cannot displace the background flow.

## 4. Queue advantage in S2 / S3 / S4 / S6

`t4_queue.csv`, queue p99 in bytes over the collective window:

| scenario | DCQCN | HPCC | CBAP-SBA | vs HPCC |
|---|---|---|---|---|
| S1 | 315 448 | **4 360** | 10 480 | 2.4× worse |
| S2 | 1 271 224 | 1 079 928 | **113 090** | **9.5× better** |
| S3 | 1 272 272 | 900 722 | **323 832** | **2.8× better** |
| S6 | 594 216 | 79 537 | **25 152** | **3.2× better** |
| S4 | 1 274 368 | 899 741 | **310 208** | **2.9× better** |
| S5 | 1 272 272 | **195 808** | 1 262 840 | 6.5× worse |

In S2/S3/S4/S6 CBAP-SBA has the lowest queue of all five algorithms **and zero
ECN marks**, at utilisation within 0.3 % of the baselines. S1 is a special case
(HPCC's 16-flow queue is already tiny); S5 is covered in §6.

ECN marks over the collective window:

| scenario | DCQCN | HPCC | CBAP-SBA |
|---|---|---|---|
| S1 | 0 | 0 | 0 |
| S2 | 2 271 | 274 | **0** |
| S3 | 9 542 | 274 | **0** |
| S6 | 451 | 24 | **0** |
| S4 | 9 582 | 274 | **0** |
| S5 | 38 410 | 274 | 25 062 |

In S2/S3/S4/S6 the queue never reaches KMIN (400 000 B), so the DCQCN
steady-state backend is never invoked: CBAP-SBA runs on explicit admission alone
at ~0.97 utilisation.

## 5. Improvement from the capacity-feasibility constraint

`p5_capacity_feasibility_before_after.csv`, CBAP-SBA only, before = pre-freeze
binary (no floor), after = FINAL FREEZE.

The rule is `η_eff = max(η_base, η_feasible)` with
`η_feasible = (N·R_min − (C − R_old)) / R_old`, applied per link with N the
new-batch fan-in on that link and R_old the runtime aggregate.

| scenario | p99 FCT | queue p99 | ECN | background retention |
|---|---|---|---|---|
| S1 | 0.00 % | 0.00 % | 0 → 0 | 0.00 % |
| S2 | **−2.97 %** | **−91.04 %** | 1 095 → **0** | −0.21 % |
| S3 | **−5.60 %** | **−74.38 %** | 8 253 → **0** | −1.81 % |
| S6 | 0.00 % | 0.00 % | 0 → 0 | 0.00 % |
| S4 | **−18.15 %** | **−75.48 %** | 8 983 → **0** | −4.34 % |
| S5 | **−6.79 %** | −0.08 % | — | −6.00 % |

Two honest qualifications:

* **S1 and S6 are bit-for-bit unchanged.** Their per-link fan-in (16 and 30) puts
  the floor below available headroom, so `η_feasible` is −0.050 and +0.125
  respectively — both below `η_base` = 0.5, and `max()` leaves η untouched. The
  constraint is provably inert where it is not needed.
* **Background retention decreased slightly in S2–S5 (−0.21 to −6.00 pts).**
  Raising η hands the collective capacity sooner, so the background flow gives up
  marginally more. The improvement in FCT and queue is therefore *partly* paid
  for on the background side, and the trade should be stated as such rather than
  presented as free. It remains a favourable trade — CBAP-SBA still leads HPCC on
  retention in all six scenarios by 0.90–26.49 points.

Direct evidence from `eta_feasibility.csv` (one row per replan per link, no
per-packet tracing):

| scenario | N (per link) | R_old | η_base | η_feasible | η_eff | raised |
|---|---|---|---|---|---|---|
| S1 | 16 | 8.0 G | 0.500 | **−0.050** | 0.500 | no |
| S6 | 30 × 2 links | 8.0 G | 0.500 | **+0.125** | 0.500 | no |
| S2 | 64 | 8.0 G | 0.500 | **+0.550** | **0.550** | yes |
| S3 | 64 | 8.0 G | 0.500 | **+0.550** | **0.550** | yes |
| S4 | 64 | 9.5 G | 0.500 | **+0.621053** | **0.621053** | yes |
| S5 | 64 | 8.0 G | 0.500 | **+0.550** | **0.550** | yes |

Measured `η_feasible` matches the closed form to six decimals (S3/S2/S5:
(6.4−2.0)/8.0 = 0.550; S4: (6.4−0.5)/9.5 = 0.62105). Across all replans in all
six scenarios, `final_sum_target ≤ link_capacity` held with **0 violations**, and
`η_eff = max(η_base, η_feasible)` held with **0 violations**. S6 shows N = 30 per
link on two separate rows, confirming the per-link (not global) fan-in.

## 6. S5: a genuine limit for long collectives

S5 (64 × 4 MiB) does **not** show the phase change the other 64-flow scenarios
do: queue p99 1 262 840 B, ECN 25 062, background minimum 0.109 Gbps.

This was investigated and is a real applicability boundary, not a defect:

* η **was** raised correctly at handover (t = 2.0000 s, η 0.500 → 0.550), and the
  target sum was exactly 10.000 G = C.
* Across all 42 replans: **0 infeasible rows**, and `floor_binding = 0 of 42` —
  the MIN_RATE floor never bound, so this congestion is not a floor artifact.
* The queue first crosses KMIN at **t = 2.1038 s, 104 ms after** the handover, and
  ECN follows 7 ms later.
* The collective spans **451 ms** in S5 versus 122 ms (S2) and 188 ms (S3/S4).

The constraint guarantees feasibility *at replan time*; it does not govern
burstiness during a long sustained transfer. With 64 flows each delivering
~95.7 Mbps for nearly half a second, transient bursts accumulate past KMIN and
the DCQCN backend correctly engages. CBAP-SBA still improves on its own
pre-freeze result (p99 376.520 → 350.963 ms, −6.79 %) and still beats the ECN
baselines by 3.21×, but it loses the queue advantage and most of the
minimum-throughput advantage in this regime.

**Stated plainly: the capacity-feasibility benefit is demonstrated for
collectives up to ~190 ms and does not extend to the ~450 ms case.**

## 7. The η knob: a controllable FCT ↔ background-protection frontier

`p3_eta_sweep_sensitivity.csv`, `p4_eta_pareto_retention_vs_p99fct.csv`.
S4, seed 2, sweeping only `CBAP_MIGRATION_RELEASE_RATIO`.

**Provenance, stated explicitly:** this sweep ran on the **pre-freeze** binary
`084da1fc`, before the feasibility floor existed. η = 0.50 reuses the pre-freeze
S4 matrix cell (config hash verified identical). It remains the valid evidence
for the knob — η_base is the swept parameter, and the floor only raises η when
the base value would be infeasible — but it is not a FINAL FREEZE measurement.

| η | p99 FCT (ms) | goodput (Gbps) | retention | bg min (Gbps) | queue mean (B) | ECN |
|---|---|---|---|---|---|---|
| 0.20 | 239.579 | 2.241 | 86.28 % | 7.301 | 883 739 | 9 474 |
| 0.35 | 148.826 | 3.607 | 79.35 % | 5.935 | 741 859 | 9 350 |
| 0.50 | 107.848 | 4.978 | 74.25 % | 4.283 | 627 060 | 8 983 |
| 0.65 | 85.041 | 6.313 | 70.27 % | 3.200 | 12 780 | **0** |
| 0.80 | 70.130 | 7.655 | 67.11 % | 1.826 | 10 922 | **0** |

Range of control: **3.42× in p99 FCT** and **19.17 points of retention**, strictly
monotonic across five points, every setting safe (100 % completion, 0 PFC, 0
drops, 0 retransmission, queue drained).

Two results worth reporting as measured:

* **Queue pressure falls as η rises** — the opposite of the prediction. Mean
  occupancy −98.8 %, time above Qmax 69.95 % → 0 %. η controls *how fast*
  capacity is handed over, not total demand; slow handover leaves admitted flows
  above what the link can honour. So faster collectives and safer queues are not
  in tension here — the cost falls on the background flow alone.
* **Background service debt is identically 0 at every η** and for both reference
  points, because the 4 GB flow finishes inside the 5.5 s stop time. The
  debt-vs-CCT Pareto is therefore degenerate in S4; `p4` uses retention instead.

HPCC's position: **not dominated by any η, and dominating none.** It is a fixed
point outside the frontier at the FCT-favouring extreme (retention 63.00 %,
p99 60.24 ms). Every η retains more background throughput. At η = 0.80,
CBAP-SBA comes within **1.16×** of HPCC's p99 while keeping 4.11 more points of
retention.

## 8. Ablation: migration off (S3, FINAL FREEZE)

`p7_ablation_s3_migration_off.csv`. Config-only change —
`CBAP_MIGRATION_ENABLE 1 → 0` — requiring **no source modification**
(`third.cc:648` passes the flag through; `rdma-hw.cc:788/1822/2042` return early).
Verified mechanically: the two configs differ in exactly one key. Topology, flow
file, seed 2, stop time 3.0 s, ECN/PFC, MIN_RATE, `eta_base` and the telemetry
window are identical.

| metric | full CBAP-SBA | migration off | change |
|---|---|---|---|
| incast completed | 64 | 64 | — |
| mean FCT (ms) | 88.276 | **562.428** | **+537 %** |
| p95 FCT (ms) | 88.293 | 562.500 | +537 % |
| p99 FCT (ms) | 88.295 | **562.507** | **+537 % (6.4×)** |
| CCT (ms) | 188.295 | 662.507 | +252 % |
| incast goodput (Gbps) | 6.082 | **0.955** | **−84.3 %** |
| bg during (Gbps) | 6.250 | 7.641 | +22.3 % |
| bg minimum (Gbps) | 3.200 | 7.200 | +125 % |
| bg retention | 81.79 % | **99.9997 %** | +22.3 pts |
| queue mean (B) | 83 545 | 13 528 | −83.8 % |
| queue p99 (B) | 323 832 | 61 832 | −80.9 % |
| queue peak (B) | 346 888 | 62 880 | −81.9 % |
| utilisation | 0.8944 | 0.8857 | −0.97 % |
| ECN / PFC / drops / retx | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | all zero |

**Migration is the mechanism that produces the entire incast benefit.** With it
disabled, admission still happens but capacity is never handed over: the
background flow keeps ~100 % retention and 7.2 Gbps minimum, while the collective
is starved to 0.955 Gbps and takes 6.4× longer. Queues are lower precisely
*because* the collective never obtains capacity — the same artifact that makes
the ECN baselines look like they "protect" the background flow (§3).

This isolates the contribution cleanly: the FCT and goodput gains in §1 come from
migration, and the queue/ECN gains in §5 come from the capacity-feasibility
constraint applied to that migration.

**Ablations still missing.** No-queue-borrowing and true linear migration remain
unimplemented (they would need new code, which was out of scope). Strict capacity
conservation cannot be ablated at all — it is enforced by `NS_ASSERT_MSG` at
`rdma-hw.cc:1644` and `throw std::logic_error` at `cbap-sba.cc:245`, so a
"no-conservation" arm would abort rather than produce data. Migration-off was run
only for S3, not all six scenarios.

## 9. Limitations to state in the paper

1. **Single deterministic seed, no dispersion.** `SIM_SEED` is inert on all
   reachable paths (the only `RandomVariableStream` is an error model with rate 0;
   routing is pinned by `CBAP_PATH_FILE`; traffic is static file replay).
   Confirmed empirically: five seeds of S1 gave bit-identical results. No
   confidence intervals are reported, because a zero-width interval from one
   deterministic observation would misrepresent it.
2. **HPCC leads on FCT everywhere** (§2) and on queue in S1 and S5 (§4).
3. **S5 long-collective limit** (§6).
4. **`drops` is a lower bound.** `switch-node.cc:193/201` drop silently on
   admission-control and routing failure with no counter; only
   `switch-mmu.cc:38` prints. It reads 0 everywhere and zero retransmission
   corroborates that, but the two silent paths are not instrumented.
5. **TIMELY is untuned** — its α/β/T_low/T_high are ns-3 attributes `third.cc`
   never sets, so it runs at library defaults.
6. **DCTCP shares DCQCN's `EWMA_GAIN`** (0.00390625, not the conventional 1/16),
   so it is evaluated at DCQCN's gain.
7. **`bg_slowdown` is defined only in S4 and S5**, the two scenarios where the
   4 GB background flow completes; service debt is the metric defined everywhere.
8. **MIN_RATE = 100 Mb/s is unchanged.** At 64 flows the floor alone is 6.4 Gbps;
   the feasibility constraint now prevents that from causing target-sum
   overshoot, but the floor itself remains a scale limit and is why per-flow
   delivered rate converges to ~95 Mbps in S2–S5.
9. **η sweep provenance** — pre-freeze binary (§7).
10. **`bg_recovery90_ms_never_dipped` and `bg_recovery95_ms_never_dipped` are
    UNUSABLE for S6 — do not cite them for that scenario.** S6 has two background
    flows (`bg_n_flows = 2`) and `metrics.py` does not propagate the per-flow flag
    through its worst-case roll-up, so both fields are blank for all five
    algorithms in S6. They are populated and correct for S1–S5.

    A correction to an earlier note: there are **no per-flow `bg0_*`/`bg1_*`
    retention, minimum or recovery columns** in the frozen output — the only
    per-flow columns present are `bg0_observation_end_s` and
    `bg0_bg_completed_before_end`. So the S6 distinction cannot be recovered from
    per-flow columns either; it must be inferred, as follows.

    The S6 recovery *times* are valid (they are worst-case across the two flows):
    HPCC 108 ms, CBAP-SBA 112 ms, and 0 ms for DCQCN/DCTCP/TIMELY. For the three
    ECN baselines the 0 ms is safely read as "never dipped", because their S6
    retention is 100.00 % and their minimum throughput 7.580–7.636 Gbps — a flow
    that never falls below 90 % of baseline has nothing to recover from. The
    remaining S6 background metrics (`bg_retention_pct`, `bg_min_gbps`,
    `bg_service_debt_bytes`) are worst-case roll-ups and are usable as reported.

    Not fixed here, by instruction and by principle: changing extraction code
    after the results were frozen would invalidate the freeze.

### Background recovery times (ms), for reference

| scenario | DCQCN/DCTCP/TIMELY | HPCC | CBAP-SBA |
|---|---|---|---|
| S1 | 0 (never dipped) | 104 | 106 |
| S2 | 0 (never dipped) | 116 | 122 |
| S3 | 0 (never dipped) | 160 | 190 |
| S6 | 0 (never dipped¹) | 108 | 112 |
| S4 | 0 (never dipped) | 162 | 190 |
| S5 | 0 (never dipped) | 342 | 452 |

¹ S6's `never_dipped` flags are blank (limitation 10). "never dipped" is inferred
from recovery time 0 together with 100 % retention and 7.58–7.64 Gbps minimum
throughput. Do not cite the S6 flag fields.

CBAP-SBA takes 4–110 ms longer than HPCC to restore the background flow to 90 %
of baseline. This is the counterpart to its higher *minimum* throughput: it
concedes capacity more gradually and reclaims it more gradually. The ECN
baselines never dip at all, for the reason given in §3.

## Files

```
paper_data/
  t1_fct_cct.csv                        mean/p50/p95/p99/min/max FCT, CCT, completion
  t2_incast_goodput.csv                 aggregate goodput, Jain fairness
  t3_background_protection.csv          before/during/after/min, retention,
                                        90%+95% recovery (+never_dipped flags),
                                        service debt, bg FCT, slowdown
  t4_queue.csv                          mean/p95/p99/peak, >Qmin, >Qmax, recovery, oversub
  t5_system_safety.csv                  utilisation, ECN, PFC, drops, retransmission
  p1_pareto_retention_vs_p99fct.csv     Pareto: background retention vs p99 FCT
  p2_pareto_queue_vs_p99fct.csv         Pareto: queue p99 vs p99 FCT
  p3_eta_sweep_sensitivity.csv          eta sweep, all metrics (pre-freeze provenance)
  p4_eta_pareto_retention_vs_p99fct.csv eta frontier + HPCC/DCQCN fixed points
  p5_capacity_feasibility_before_after.csv  CBAP-SBA before/after the floor
  p6_speedup_vs_baselines.csv           per-scenario ratios; HPCC row is <1 throughout
  paper_results_summary.md              this file
```

Every CSV carries `scenario, scenario_shape, algorithm` (or `label, kind, eta`)
and a leading `#` provenance line. Blank cells mean the metric is undefined for
that cell, never a substituted zero.
