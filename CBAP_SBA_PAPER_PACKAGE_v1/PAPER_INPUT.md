# PAPER INPUT (verified results only)

## Problem
Synchronized incast batches (training barriers) on RoCE force reactive CC
(DCQCN/DCTCP/TIMELY/HPCC) to *discover* congestion through queue growth:
~1.28MB standing queues, ~1ms queuing delay for all co-existing traffic,
and a fixed per-burst discovery cost. The batch arrival is, however, a
known event at the application boundary.

## Mechanisms (code: simulation/src/point-to-point/model/)
1. Batch admission planning + explicit capacity migration (cbap-sba.cc,
   rdma-hw.cc EvaluateCbapSbaMigration): old flows retreat to floors in
   ~35us at batch release and get capacity back ~40us after completion.
2. Steady-state capacity cap at C with demand bound + DCQCN backend for
   handed-off/out-of-scope flows (rdma-hw.cc static-cap fill).
3. Leased predictive headroom (D4v2, rdma-hw.cc QueueControllerEpoch):
   boost = min(BMAX, max(0, Q_target - Q_pred)*8/H_eff), lease = H_eff,
   4-zone hysteresis, veto when prediction crosses Q_red.

## Setup
ns-3 (HPCC codebase), 10G single/dual bottleneck, 64 hosts, RTT ~8us,
8MB shared-buffer switch, ECN 400/1600KB. Scenarios S1-S6 (16-64 flows,
256KiB-4MiB, bg 8/9.5G, dual-bottleneck S6). Deterministic (bit-identical
across seeds) -> single seed per cell; all definitions in
01_METRIC_DEFINITIONS.md.

## Main results (03_MAIN_RESULTS_LONG.csv)
CCT vs DCQCN: S1 -5.133%, S2 -8.903%, S3 -2.624%, S4 -3.766%, S5 -1.349%, S6 0.179% (TIE).
Fastest algorithm in S1-S5; S6 is a tie. Only algorithm with zero
over-Q_abs samples in all six scenarios; queuing delay 16-39us vs
~1021-1037us for baselines. Background retention >=99.2% of DCQCN with
recovery ~35-45us (DCQCN: 20-25ms). PFC/drops/retx = 0 everywhere (8MB
buffer; on 2MB baselines fire 438-11,548 PFC pauses, CBAP byte-identical).

## Ablation (08)
D2 (cap, no migration): CCT +43.8% vs D1 -- migration is necessary.
D3 (cap+migration): ties DCQCN (+0.20%) at 135.7x lower queue.
D4v2 boost: converts the tie into -2.62% CCT / +2.7% goodput at 26.2KB
queue. D4v1 (+0.30C fixed) is INVALID_OVERBOOST_POLICY (retained).

## Fairness of comparison (06/07)
Baselines run standard codebase defaults in the matrix; a 21-point S3
parameter sweep (ECN ladders, PMAX, DCTCP AI, TIMELY AI, HPCC eta/MI)
shows no configuration enters CBAP's (completion x queue) region; the
fastest reachable baseline point is ECN-inert (effectively no CC) and is
still +0.58% slower at 64x the queue. CBAP was tuned on S3 only and
validated untouched on held-out S4/S5.

## Robustness (09)
BMAX neighborhood robust on completion (0.03/0.04/0.05 identical CCT;
queue cost non-monotonic, disclosed); buffer-depth and ECN-threshold
variants leave CBAP byte-identical; zone machinery exercised end-to-end
under batch-overlap stress (peak 97.5% of Q_abs, full recovery).

## Ties / failures (write as such)
S6 dual-bottleneck completion is a TIE (+0.18%). In-window background
suppression to floor is an explicit trade-off (every algorithm suppresses
in-window; DCQCN itself ~3%). st_2555/st_2550 overlap probes exceed Q_abs
structurally (drain cannot go below MIN_RATE floors) -- design envelope
T~2.2ms, documented.

## Limitations
Single-hop bottlenecks; single seed (determinism proven, perturbation
study not run); fan-in <= ~94 (floor feasibility envelope); mixed-domain
startup transient (~4.6%) in grant budgets; TIMELY thresholds not swept;
baseline sweep on S3 only.

## Do NOT write
"comprehensively superior", "optimal parameters", any cross-random-
environment generalization, S6 as a win, baseline PFC/loss claims on the
8MB main matrix, or any number from scr7/pa/D4v1-era runs.
