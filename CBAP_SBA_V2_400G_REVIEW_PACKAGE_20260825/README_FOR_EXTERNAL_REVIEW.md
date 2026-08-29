# CBAP-SBA v2 400G — External review package (2026-08-25)

Repository: https://github.com/lr547156275-bot/yunxiao
branch `cbap-queue-delay-credit`, evidence commit lineage ends at the hash
recorded in `code_provenance/GIT_PROVENANCE.txt`. Raw-output releases:
`evidence-2026-08` (frozen v1, 10G campaign) and `evidence-v2-2026-08`
(this v2 campaign). Nothing in this package was rerun or edited for
packaging; it is a verbatim collection.

## 1. Evidence classes — what may be cited

| class | contents | status |
|---|---|---|
| **Formal evidence** | `raw/v2_matrix.tar.gz` (120-cell formal matrix + determinism twin), `reports/final_results_v2.csv`, `reports/matrix_report_v2.md`, `RUN_INVENTORY_V2.csv` | citable |
| **Methodology evidence** | `raw/v2_prelim.tar.gz`: preflight round 3 (physical-consistency checks: single-flow line rate, integer-ns tx gaps, fabric-queue conservation), H_eff measurement (`heff_*`), pilot 67 cells incl. buffer sensitivity and stock/speed_normalized comparison; `reports/01..03,06` | citable as methodology/design input |
| **Tuning (training) data** | screening cross `scrv2_*` in `raw/v2_prelim.tar.gz`, `reports/04_screening_results.csv` — used ONLY to select CBAP parameters (frozen rules, mean-CCT, tie→conservative) | citable as the parameter-selection procedure; NOT as comparative performance evidence |
| **Superseded — do not cite** | everything indexed in `ARCHIVED_ERAS_INDEX.md` (packet-1048 era, floor-1ns era, bg-freeze era). Not included in this package; tar remains in the release. | forbidden for claims |

The 5 pilot 10G large-message baseline cells with incomplete flows
(pv10g_4m_hpcc, pv10g_16m_{hpcc,dcqs,dcqn,dcql}) are marked in
`reports/03_pilot_results.csv`; the formal matrix superseded them with the
×1.3 stop rule and completed 120/120.

## 2. Formal matrix composition (120 cells)

- Rates: 10 / 200 / 400 Gbps (all links; multi-tier 89-node/21-switch topo)
- Scenarios: S0 64×256KiB, S1 64×1MiB, S2 64×4MiB (headline),
  S3 64×16MiB, S4 64×4MiB @ bg 0.95C, S5 32×8MiB; background flow at
  0.8C (S4: 0.95C) on the same bottleneck, never completing by design
- Core arms ×6: cbap, hpcc(stock), dcqn, dcql, dctcp, timely(stock)
- Annex: dcqs (stock DCQCN) at S2 ×3 rates; cbap0 (boost-off ablation)
  at S2 ×3 rates; buffer sensitivity S2@400G × {8, 32} MB × {cbap, hpcc,
  dcqn} (64MB is the main-grid default)
- Single seed; justified by the determinism twin (fm400g_s2_cbap run
  twice, 5/5 output files byte-identical; `det_twin/` in v2_matrix)

## 3. Frozen CBAP parameters (v2)

D_target = 8µs; BMAX = 0.02; H_GUARD = measured H_eff p99 per rate
{10G: 118µs, 200G: 15µs, 400G: 12µs}; control epoch 5µs;
MIN_RATE = 0.01·C; rho_init = 0.90;
Q_abs: D_abs = max(80µs, 7×H_eff) → {826µs, 105µs, 84µs} (feasibility
rule, β calibrated once against v1's validated 10G headroom);
M_safe = fanin × 1000B. Selected by the pre-frozen screening rules
(mean CCT, 0.3% tie band → smaller BMAX, then smaller D_target) over a
declared cross grid; winner d08_b020 is an interior optimum on both axes
(`reports/04_screening_results.csv`).

## 4. Baseline profiles

- **stock**: v1 parameters verbatim (DCQCN AI=50Mb/s, HAI=100Mb/s,
  ECN KMIN/KMAX = 400/1600KB at every rate; TIMELY/HPCC upstream defaults)
- **speed_normalized (sn)**: rate-typed parameters scaled with line rate —
  DCQCN AI=0.005·C, HAI=0.01·C (arm `dcqn`); DCTCP_RATE_AI=0.1·C (arm
  `dctcp`). Dimensionless knobs (HPCC eta/maxStage) unchanged by design.
- **dcql**: sn + delay-defined tight ECN (KMIN=2µs·C/8, KMAX=8µs·C/8) —
  the "trade FCT/goodput for queue" fairness arm.
- TIMELY thresholds are compile-time attributes in this harness (TLow
  50µs / THigh 500µs); not config-exposed — reported as a limitation, and
  its near-inert behaviour at 400G is a finding, not a tuning artifact.

## 5. Metric chain (raw → final_results_v2.csv)

Per cell: ns-3 binary (`code_provenance/`) writes `flow_timing.csv`,
`flow_summary.csv`, `selected_link_timeseries.csv`,
`selected_flow_timeseries.csv`, `qlen_ts.csv`, `pfc_events.csv` (+ CBAP
controller/actuation traces). `matrix_analyze.py`
(`code_provenance/tools/`) computes every column of
`final_results_v2.csv`; formulas in `METRIC_DICTIONARY_V2.md`.
No figure generator exists for v2; all tables derive from the CSVs.

## 6. Paper-level claims → evidence pointers

| claim | columns | raw |
|---|---|---|
| queue 20–50× lower at 200/400G | `qpeak_mb`,`qdelay_us` (cbap vs others) | `selected_link_timeseries.csv`, `qlen_ts.csv` |
| zero PFC in all 120 cells vs hundreds–thousands | `pfc` | `pfc_events.csv`, `pfc_pause_ns_delta` |
| buffer-invariant vs buffer-filling | S2@400G ×{8,32,64}MB rows | same |
| batch p99 best-or-tied when msg ≥ BDP, gap grows with rate | `p99_cct_ms`,`p99_over_ideal` | `flow_timing.csv` |
| background retention exact at cap; stock DCQCN collapse | `bg_tail_gbps`,`bg_total_gb` | `selected_flow_timeseries.csv` |
| honest boundaries (sub-BDP S0; 10G row; timely-hot cells) | §2 of `matrix_report_v2.md` | as cited there |
| 10G Q_abs transient ≤ one blind window (5 gate violations, reported) | `gates` column | `matrix_report_v2.md` §3 |

## 7. Known gaps (raw-recomputability audit: `RAW_COMPLETENESS_V2.md`)

- Switch silent drops have no counter in this harness (upstream
  limitation, documented since v1); `retx_events`=0 across all 120 cells
  is the corroborating evidence that no loss occurred.
- Wire bytes are not logged per packet; derivable exactly as
  payload×1000/952 (fixed geometry, `BUILD_AND_ENVIRONMENT.md`).
- Everything else in the required-metrics list is recomputable from the
  per-cell raw files; per-cell verification results are in
  `RAW_COMPLETENESS_V2.md`.

## 8. Failure/retry record

Formal matrix: 0 cell failures, 0 timeouts, 0 disk-guard events, 0
retries (console log in `raw/v2_configs_logs.tar.gz`; DONE markers carry
exit codes, reproduced in `RUN_INVENTORY_V2.csv`).
