# v2_400g — Formal matrix design (PROPOSAL, pending user approval)

## A. Q_abs feasibility rule (fixes pilot finding 6; a constraint, not tuning)

The controller cannot bound the queue below its own actuation envelope:
during the blind window H_eff the bottleneck can accumulate up to C×H_eff/8
plus the floor-driven admission transient. Rule:

    D_abs_eff(rate) = max(80µs, β × H_eff(rate)),  β = 7

β is calibrated ONCE against v1's empirically validated 10G headroom
(7×118µs = 826µs ≈ v1's proven 838µs) and then applied unchanged across
rates. Resulting Q_abs: 10G 1.03MB (826µs), 200G 2.63MB (105µs),
400G 4.2MB (84µs). D_target stays 8µs everywhere; zones keep their frozen
fractions of Q_abs. Recorded in every manifest.

## B. Stop-time rule (fixes pilot finding 8)

    stop = release(20ms) + ideal_drain × 1.3 + 14ms tail

Any cell finishing <64/64 ⇒ the whole scenario's stop is extended and ALL
arms of that scenario rerun together (v1 anomaly discipline).

## C. Matrix

Rates: 10 / 200 / 400G (10G under rule A; links v2 to the frozen v1 story).

Scenarios (bg = 0.8C except S4; fan-in 64 except S5):
| id | shape | purpose |
|----|-------|---------|
| S0 | 64×256KiB | honest boundary (msg < BDP at 200/400G) |
| S1 | 64×1MiB | light congestion |
| S2 | 64×4MiB | headline (screening point) |
| S3 | 64×16MiB | sustained congestion |
| S4 | 64×4MiB, bg 0.95C | tight headroom |
| S5 | 128×2MiB | wider fan-in, same volume |

Arms (core table): cbap, hpcc, dcqn (speed-normalized DCQCN), dcql
(queue-tight DCQCN), dctcp_sn (DCTCP_RATE_AI=0.1C), timely_stock.
Annex arms: dcqs (stock DCQCN — its high-rate collapse is reported as a
finding), cbap0 (ablation, one headline cell per rate), TIMELY inertness
note at 400G (THigh=500µs ≫ queue delays; attributes not config-exposed —
recorded, not tuned).

Cell count: 6 scenarios × 3 rates × 6 arms = 108 core
+ dcqs annex (S2 × 3 rates) 3 + ablation 3 + 400G buffer sweep
(S2 × {8,32}MB × {cbap,hpcc,dcqn}) 6 ≈ **120 cells**.
Measured pace (~2–6 min/cell, 2-worker pool): **≈ 4–6 h**, overnight-safe,
resume-safe.

## D. Frozen before launch

- CBAP: D_target=8µs, BMAX=0.02, H_GUARD=118/15/12µs, epoch 5µs,
  MIN_RATE=0.01C, rho_init=0.90, rule-A Q_abs. No mid-matrix changes.
- Baselines: the six arms above, parameters as in the pilot generator.
- Metrics: v1 frozen definitions (CCT ref=ready≡release, BCT, FCT) +
  p99/ideal, queue peak (MB and µs), fabric qlen_ts, PFC count+pause-ns,
  drops/retx, bg tail/total/retention, link idle area, CBAP zone/violation
  counters. Single seed (determinism re-verified once at 400G by a
  byte-identical twin re-run before the matrix).
- Gates: completion, hash/manifest gate, trace completeness, bg-alive,
  anomaly classes and stop rules as v1. No tuning on any failure.

## E. Deliverables

final_results_v2.csv (120 rows), matrix_report_v2.md, per-scenario tables,
figdata (rate-scaling gap curve, queue-vs-rate, PFC-vs-buffer, boundary
crossover, ablation), 120 manifests, anomalies.md, then
CBAP_SBA_PAPER_PACKAGE_v2 mirroring v1's structure.

## F. Pre-launch chores (approval needed where marked)

1. Commit the five v2 source patches + generators + reports to the git
   branch (provenance before the matrix binary is used for the record).
2. (approval) Reclaim ~12GB: the uncompressed v1 outputs under
   simulation/experiment are already tarred in GitHub Release
   evidence-2026-08; delete on-disk copies after sha-verifying the tars.
3. Determinism twin at 400G (one cell, run twice, byte-compare).
