# Final scoped CBAP analysis

## Unique decision

**SCOPED_CBAP_VALID_WITH_LIMITATIONS**

## [Measured] integrity and scope

- Scope: 18/18 complete; Core: 170/170 complete; missing=0, invalid=0.
- All six scope decisions match the predeclared semantics; the single-flow BYPASS raw overhead is the fixed 5 us decision delay and its unexplained overhead is 0.000000000 us.
- Controller audit violations: 0; PFC events: 0; ECN marks across all core runs: 1898324.
- Pareto-positive versus DCQCN: 13/23 scenarios. At load 80%, the largest adjacent fan-in/message component has 11 points, so this is a continuous region under the declared grid adjacency.

## [Measured] Scoped CBAP relative to each comparator

Percentage is (Scoped - baseline)/baseline; negative CCT/queue is favorable.

| Baseline | Mean CCT difference | Mean peak-queue difference | CCT wins |
|---|---:|---:|---:|
| DCTCP | 15.23% | -52.24% | 2/23 |
| DCQCN | -1.31% | -52.24% | 11/23 |
| TIMELY | -3.33% | -52.69% | 10/23 |
| HPCC-INT | 2.18% | -54.30% | 11/23 |
| BOP-QB | 9.80% | -38.45% | 6/23 |
| Independent-Min-Grant | 7.36% | -47.98% | 9/23 |

The per-scenario raw comparisons are in `processed/paired_comparisons.csv`; no scenario was discarded.

## Research questions

- **RQ1 — structural scope:** PASS in all six semantic cases: single flow, low demand, and no-shared-link bypass; incast, overload, and synchronous parking-lot enable.
- **RQ2 — activation region:** every one of the 23 formal core scenarios is oversubscribed under synchronized release and enables CBAP; the three bypass classes are demonstrated by the separate scope matrix.
- **RQ3 — independent admission:** actual Independent-Min-Grant aggregation rises monotonically with fan-in in the 1 MiB/load-80 slice and reaches 27.181x the 100 Gbit/s bottleneck in the full grid.
- **RQ4 — continuous behavior:** 13/23 points are queue–CCT Pareto-positive versus DCQCN; the largest adjacent load-80 component contains 11 grid points.
- **RQ5 — queue versus utilization:** queue reduction is not free in every case. Scoped utilization is below 90% in the fan-in=64 rows and also reflects the configured low-load window; the raw per-run values remain published.
- **RQ6 — benefits and costs:** mean paired results above show large queue reductions against most baselines, but CCT is worse against DCTCP and BOP-QB on average and varies by scenario.
- **RQ7 — ablation:** the 15 small/middle/large mechanism rows are retained in `ablation_summary.csv`; they isolate joint admission, tracking/rate behavior, and scope without selecting favorable points.
- **RQ8 — control overhead:** the largest Scoped control/DATA-wire ratio is 8.443%; the fixed 5 us scope delay is visible in short-message raw CCT.
- **RQ9 — adverse cases:** fan-in=64 utilization loss and short-message CCT cost are present; controller constraint violations and PFC are both zero. One 100.156% utilization value is flagged as a window-normalization audit issue rather than silently replaced.

## [Measured] parameter scans

- Fan-in, message, and load slices are in `fanin_scaling.csv`, `message_scaling.csv`, and `load_scaling.csv`.
- Scoped CBAP utilization falls below 90% in at least one fan-in=64 run: **True**. This is retained as an adverse scaling result.
- One raw utilization value exceeds 100% slightly; the exact run and clipped audit-only value are in `utilization_audit.csv`. Main comparisons preserve raw utilization.
- Independent actual admission oversubscription and all capacity/credit/pacing checks are published without filtering.

## [Interpretation]

The measured queue reductions are not uniformly accompanied by lower CCT. The fan-in=64 utilization loss and the short-message/control-delay cost bound the useful region. The results support a scoped queue--completion-time tradeoff in portions of this single-bottleneck synchronized matrix, rather than universal dominance.

## [Unverified]

These runs do not validate victim-flow performance, 200/400 Gbit/s links, Clos fabrics, release skew, production deployment, random statistical significance, dynamic routing, or general multi-bottleneck behavior.

Victim calibration status: **VICTIM_CALIBRATION_NOT_RUN**. Existing calibration artifacts, if present, are identity/context only; no CBAP victim-performance claim is made.
