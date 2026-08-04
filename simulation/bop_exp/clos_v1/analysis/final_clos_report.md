# Final single-bottleneck and Clos experiment audit

## Unique completeness verdict

`FINAL_EXPERIMENTS_READY`

This verdict evaluates experimental integrity, not whether BOP-QB wins. All 513 formal runs and all 12 audit runs are valid for the stated ns-3 scope. The performance results include substantial unfavorable cases and are reported without filtering.

## 1. Corpus and validity

| Corpus | Expected | Valid | Invalid |
|---|---:|---:|---:|
| Formal single-bottleneck (`main_v2` reuse corpus) | 273 | 273 | 0 |
| Formal Clos | 240 | 240 | 0 |
| PFC semantic audit | 9 | 9 | 0 |
| n32 DCQCN deterministic replay | 3 | 3 | 0 |
| Formal experiments total | 513 | 513 | 0 |
| Audit runs total | 12 | 12 | 0 |

The following checks passed:

- Each manifest row resolves to exactly one run, with exit status 0, completion flag, all flows complete, finite metrics, and no log truncation.
- All recorded input hashes match the files used by each run. For every Clos scenario and seed, all five algorithms have identical non-algorithm input hashes.
- Fixed ECMP paths resolve for every flow; no missing or guessed path is used.
- `collective_schedule.csv`, `group_round_summary.csv`, and generated flow work agree for every group. Collective bytes are conserved.
- Recomputed group RCT equals barrier completion minus common release. Every dependent group starts no earlier than its predecessor barrier.
- The 48 BOP-QB Clos runs contain 3,873 group decisions and 502,556 per-link constraints. Independent replay of \(T_\text{line}\), every \(T_{\text{link}}\), \(T^\*\), base rates, capacity flags, deterministic flow-credit sums, and per-link credit rooms found zero violations.
- The single-bottleneck 273-run checker reports no error other than expected current-tree source-hash drift after the later default-off Clos extension. The historical source and input hashes are preserved in the reuse manifest, the single-bottleneck strict-regression flag passes, and all three n32 DCQCN replays match their source runs exactly in RCT, FCT, queue, ECN, and packet counts.
- The nine PFC audit rows are complete: six configured runs are correctly classified `PFC_NOT_TRIGGERED`, and three disabled controls are `PFC_DISABLED_CONFIRMED`. Clos PFC metrics remain `NA` rather than being fabricated as zero.

`invalid_runs.csv` therefore contains only its header.

## 2. Statistical method

The independent unit is a run identified by `scenario + seed`. Each aggregate uses exactly three seed-level observations. Steps and rounds contribute to the per-run metric but are never treated as additional samples.

For BOP-QB versus each formal baseline, the analysis computes three paired seed differences, their mean and sample standard deviation, and a two-sided 95% t interval using \(t_{0.975,df=2}=4.30265\). These intervals describe only the three configured seeds and must not be interpreted as broad workload stability.

The formal baseline set is DCTCP, DCQCN, TIMELY, and HPCC-INT. Open-loop is excluded. DCQCN-Wire-Equalized is retained only in the existing single-bottleneck fairness ablation.

## 3. Single-bottleneck context

The corrected `main_v2` corpus remains valid after the final audits. Against the best formal CC baseline, BOP-QB simultaneously improves RCT and peak queue in 1/15 scenarios. It pays at most 3% RCT for at least 50% queue reduction in 4/15 scenarios. Its strongest single-bottleneck result is the 256 KiB case: 4.24% lower RCT and 90.27% lower peak queue. Most other cases expose the intended tradeoff: a small RCT cost with a large queue reduction.

The earlier n32 cross-version uncertainty is resolved for this corpus by three deterministic replays: all input/config/source hashes match the historical source runs and every reported delta is zero.

## 4. Clos results by scenario

Best formal CC is selected only from DCTCP, DCQCN, TIMELY, and HPCC-INT using the three-seed mean CCT. DCTCP is best by that criterion in all 16 Clos scenarios.

| Scenario | Best CC | Best CCT (us) | BOP-QB CCT (us) | CCT change | Queue-max change | ECN change |
|---|---|---:|---:|---:|---:|---:|
| `c1_all_to_all_n32_1mib` | DCTCP | 113.906 | 122.980 | +7.97% | -2.68% | both zero |
| `c1_ring_allreduce_1d_n32_1mib` | DCTCP | 937.658 | 1065.720 | +13.66% | +90.88% | both zero |
| `c1_hierarchical_allreduce_2d_n32_1mib` | DCTCP | 397.602 | 451.198 | +13.48% | +264.32% | both zero |
| `c1_all_to_all_n32_64mib` | DCTCP | 6804.593 | 7165.826 | +5.31% | +73.47% | +225.25% |
| `c1_ring_allreduce_1d_n32_64mib` | DCTCP | 12066.097 | 13089.524 | +8.48% | +94.48% | both zero |
| `c1_hierarchical_allreduce_2d_n32_64mib` | DCTCP | 13629.413 | 14688.608 | +7.77% | +7.79% | both zero |
| `c1_all_to_all_n64_1mib` | DCTCP | 118.640 | 129.708 | +9.33% | -37.43% | both zero |
| `c1_ring_allreduce_1d_n64_1mib` | DCTCP | 1773.855 | 2290.614 | +29.13% | -13.88% | both zero |
| `c1_hierarchical_allreduce_2d_n64_1mib` | DCTCP | 502.731 | 637.809 | +26.87% | -44.27% | both zero |
| `c1_all_to_all_n64_64mib` | DCTCP | 6923.795 | 7358.888 | +6.28% | +29.57% | -12.24% |
| `c1_ring_allreduce_1d_n64_64mib` | DCTCP | 13088.505 | 14513.974 | +10.89% | +153.50% | both zero |
| `c1_hierarchical_allreduce_2d_n64_64mib` | DCTCP | 15041.251 | 16231.246 | +7.91% | -26.51% | -100.00% |
| `dlrm_like_64h` | DCTCP | 26690.204 | 28835.815 | +8.04% | -56.91% | -95.00% |
| `c2_all_to_all_n64_64mib` | DCTCP | 12819.539 | 13573.968 | +5.88% | +13.00% | -91.46% |
| `c2_ring_allreduce_1d_n64_64mib` | DCTCP | 13088.546 | 14523.374 | +10.96% | +155.29% | both zero |
| `c2_hierarchical_allreduce_2d_n64_64mib` | DCTCP | 17075.185 | 18111.880 | +6.07% | -3.67% | -42.41% |

BOP-QB is 5.31%–29.13% slower than the best formal baseline in all 16 Clos scenarios. It reduces peak queue in 7/16 scenarios and increases it in 9/16. Thus the single-bottleneck low-queue advantage does not generalize uniformly to the current Clos collective generator and path layout.

Against HPCC-INT specifically, BOP-QB has lower CCT in 12/16 scenarios, but HPCC-INT usually has a lower queue. This forms a real RCT–queue Pareto tradeoff; it does not overturn DCTCP's lower CCT in this matrix.

## 5. Research questions

### RQ1: Does BOP-QB retain a low-queue advantage in a real Clos?

Only partially. Relative to the best formal CC, peak queue falls in 7/16 cases, including 64-rank 1 MiB All-to-All (-37.43%), 64-rank 1 MiB hierarchical (-44.27%), and DLRM-like (-56.91%). It rises in 9/16, severely for ring and some 32-rank cases. The correct conclusion is scenario-dependent queue control, not a universal low-queue advantage.

### RQ2: Is multi-link planning capacity- and credit-safe?

Yes for this corpus. All 3,873 BOP-QB group plans and 502,556 link constraints replay exactly. There are zero \(T^\*\), base-rate, capacity, allocation, or per-link credit-room violations. No future telemetry is needed to obtain this result.

### RQ3: Is the effect consistent across All-to-All and All-Reduce?

No. Mean CCT overhead against the best formal CC is 6.95% for All-to-All, 14.62% for ring All-Reduce, and 12.42% for hierarchical All-Reduce. Mean peak-queue change is +15.19%, +96.06%, and +39.53%, respectively. Ring is the clearest unsuitable pattern in the current implementation.

### RQ4: How does scaling from 32 to 64 participants behave?

For BOP-QB on 1:1 Clos:

- All-to-All CCT increases by 5.47% at 1 MiB and 2.69% at 64 MiB.
- Ring CCT increases by 114.94% at 1 MiB and 10.88% at 64 MiB.
- Hierarchical CCT increases by 41.36% at 1 MiB and 10.50% at 64 MiB.

The small-message sequential-step overhead dominates ring and hierarchical scaling. Capacity and credit safety remain intact at 64 participants.

### RQ5: Does 2:1 oversubscription change the RCT–queue tradeoff?

Yes, but not uniformly:

- All-to-All: BOP-QB CCT increases 84.46% and queue maximum 133.36% from 1:1 to 2:1.
- Ring: CCT and queue are effectively unchanged (+0.06% and +0.26%).
- Hierarchical: CCT increases 11.59% and queue maximum 103.37%.

Oversubscription therefore exposes traffic-pattern-specific hot links rather than applying a common multiplicative penalty.

### RQ6: Does the DLRM-like sequence improve?

No on total communication time. BOP-QB takes 28,835.815 us versus DCTCP's 26,690.204 us (+8.04%). It reduces queue maximum from 1,334,579 B to 575,005 B (-56.91%) and ECN marks from 2,606 to 130.3 (-95.00%). This is a queue/ECN benefit purchased with longer communication time.

### RQ7: Which scenarios are unsuitable for BOP-QB?

The strongest negative evidence is:

- 64-rank 1 MiB ring and hierarchical collectives, with +29.13% and +26.87% CCT;
- ring collectives generally, where mean queue maximum is 96.06% above the best formal CC;
- 2:1 64 MiB All-to-All, where oversubscription materially raises both CCT and queue;
- workloads whose objective is minimum CCT regardless of queue, because DCTCP wins all 16 Clos CCT comparisons.

## 6. Scope and claims

The data are ready for formal paper use as an ns-3 fixed-path Clos evaluation. They support claims about formula correctness, capacity/credit safety, and measured tradeoffs in the exact generated collectives. They do not support claims of universal CCT superiority, universal low queue, production deployment, dynamic routing, arbitrary background traffic, or broad statistical stability beyond three configured seeds.

The required machine-readable tables contain all seed-paired results and confidence intervals. Figures are emitted in both SVG and vector PDF. Unfavorable observations are preserved in `suspicious_findings.md`.
