# CBAP-SBA final results — README

This directory is the complete, frozen data delivery for the paper. It contains
no figures: only CSVs, summaries, manifests and the reproduction metadata.

**Nothing here was re-simulated during packaging.** Every number is either copied
from a completed run or a reorganisation of `final_results.csv`.

## What was run

30 cells = 5 congestion-control algorithms × 6 scenarios, one seed (2) each, on
the FINAL FREEZE build. Plus two supporting experiments:

* an η sensitivity sweep on S4 (5 values of `CBAP_MIGRATION_RELEASE_RATIO`),
* one S3 ablation with migration disabled.

All 30 matrix cells completed with the full expected incast count and complete
link traces. Across all 30: **PFC events 0, PFC pause 0 ns, drops 0,
retransmission 0 bytes**. `anomalies.md` reports 0 items.

Build identity (both must match — see `paper_metadata.md` §9):

```
git commit  2ece98e378c69a6d38884dd1c1a74d007618ae9c
third       0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35
p2p library 0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72
```

Verified 30/30 manifests carry both hashes and that commit.

## Read these first

| file | purpose |
|---|---|
| `paper_results_summary.md` | the findings, partitioned by claim, with limitations |
| `paper_metadata.md` | topology, scenarios, every parameter, the η formulas, determinism, build hashes |

## Data files

| file | contents |
|---|---|
| `final_results.csv` | 30 cells × 70 columns — the source for everything below |
| `t1_fct_cct.csv` | mean / p50 / p95 / p99 / min / max FCT, CCT, completion rate |
| `t2_incast_goodput.csv` | aggregate goodput, Jain fairness, acked bytes |
| `t3_background_protection.csv` | before / during / after / minimum throughput, retention, 90 % + 95 % recovery, service debt, background FCT, slowdown |
| `t4_queue.csv` | queue mean / p95 / p99 / peak, > Qmin and > Qmax fractions, recovery, oversubscription |
| `t5_system_safety.csv` | utilisation, ECN, PFC, drops, retransmission |
| `p1_pareto_retention_vs_p99fct.csv` | Pareto: background retention vs incast p99 FCT |
| `p2_pareto_queue_vs_p99fct.csv` | Pareto: queue p99 vs incast p99 FCT |
| `p3_eta_sweep_sensitivity.csv` | η sweep, all metrics (pre-freeze binary — see below) |
| `p4_eta_pareto_retention_vs_p99fct.csv` | η frontier with HPCC and DCQCN as fixed points |
| `p5_capacity_feasibility_before_after.csv` | CBAP-SBA before / after the feasibility floor, all six scenarios |
| `p6_speedup_vs_baselines.csv` | per-scenario ratios; the HPCC rows are all < 1 |
| `p7_ablation_s3_migration_off.csv` | S3: full CBAP-SBA vs migration disabled |
| `tables/` | per-scenario tables, summary, **triggers**, **safety** |
| `manifests/` | 30 per-cell manifests + `matrix_baseline.manifest` |
| `anomalies.md` | auto-generated; states 0 items |

Every CSV carries a leading `#` provenance line and identifies its rows by
`scenario, scenario_shape, algorithm` (or `label, kind, eta`). **A blank cell
means the metric is undefined for that cell — never a substituted zero.**

## Caveats that affect how the numbers may be cited

**1. `bg_recovery90_ms_never_dipped` / `bg_recovery95_ms_never_dipped` must not be
used for S6.** Both fields are blank for all five algorithms in S6, because S6 has
two background flows (`bg_n_flows = 2`) and `metrics.py` does not propagate the
per-flow flag through its worst-case roll-up. They are populated and correct for
S1–S5.

There are **no per-flow `bg0_*`/`bg1_*` retention, minimum or recovery columns**
in this output — the only per-flow columns are `bg0_observation_end_s` and
`bg0_bg_completed_before_end`. For S6, therefore, use the recovery *times*
(valid, worst-case across both flows: HPCC 108 ms, CBAP-SBA 112 ms, 0 ms for the
three ECN baselines) and infer "never dipped" for the baselines from their 100 %
retention and 7.58–7.64 Gbps minimum throughput. All other S6 background metrics
are worst-case roll-ups and are usable as reported.

This is recorded rather than fixed: changing extraction code after the results
were frozen would invalidate the freeze.

**2. HPCC is faster than CBAP-SBA on incast FCT in all six scenarios**
(ratio 0.657–0.690, i.e. CBAP-SBA is 1.45–1.52× slower). No claim of overall
superiority over HPCC is made anywhere in this delivery.

**3. S5 is a genuine applicability limit, not a defect.** With 4 MiB messages the
collective runs 451 ms and CBAP-SBA loses its queue and minimum-throughput
advantage (queue p99 1 262 840 B, ECN 25 062, background minimum 0.109 Gbps).
The feasibility constraint held throughout (0 infeasible rows across 42 replans,
floor never binding); the queue builds 104 ms *after* the handover, from sustained
burstiness rather than from an infeasible allocation. S5 is reported in full, not
omitted.

**4. The η sweep ran on the pre-freeze binary** `084da1fc`, before the feasibility
floor existed. It remains valid evidence for the knob (η_base is the swept
parameter) but is not a FINAL FREEZE measurement. Stated in
`p3_eta_sweep_sensitivity.csv` and summary §7.

**5. Single deterministic seed, no confidence intervals.** `SIM_SEED` is inert on
all reachable paths; five seeds of S1 gave bit-identical results, and solo vs
parallel runs of S3/S4 matched to 6 decimals. A zero-width interval from one
deterministic observation would misrepresent it. See `paper_metadata.md` §8.

**6. `drops` is a lower bound.** `switch-node.cc:193/201` drop silently on
admission-control and routing failure with no counter; only `switch-mmu.cc:38`
prints. It reads 0 everywhere and zero retransmission corroborates that, but the
two silent paths are not instrumented.

**7. Baseline tuning.** TIMELY runs at ns-3 library defaults (its α/β/T_low/T_high
are never set by `third.cc`). DCTCP shares DCQCN's `EWMA_GAIN` of 0.00390625
rather than the conventional 1/16.

**8. `bg_slowdown` is defined only for S4 and S5**, the two scenarios where the
4 GB background flow completes within the stop time. Service debt is the metric
defined everywhere.

## Ablations

Present: **migration off, S3 only** (`p7`). It is a config-only change requiring
no source modification, and the two configs were verified to differ in exactly one
key. Result: disabling migration degrades incast p99 FCT 6.4× (88.3 → 562.5 ms)
and goodput 84 %, while the background flow keeps ~100 % retention — capacity is
never handed over. This isolates migration as the source of the incast benefit.

Missing, and not added: migration-off for the other five scenarios,
no-queue-borrowing, and true linear migration (all would need new code). Strict
capacity conservation cannot be ablated at all — it is enforced by
`NS_ASSERT_MSG` at `rdma-hw.cc:1644` and `throw std::logic_error` at
`cbap-sba.cc:245`, so a "no-conservation" arm would abort rather than produce
data.

## Reproducing

See `paper_metadata.md` §10. Quick environment check: S1/DCQCN must yield a mean
incast FCT of **17.399 ms**; any other value means the environment differs.
