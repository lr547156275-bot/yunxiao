# η sensitivity sweep on S4 — the tunable FCT / background-protection trade-off

Five values of `CBAP_MIGRATION_RELEASE_RATIO` (η) on S4 (64-way × 1 MiB,
95 % background load), one seed, everything else held identical to the
30-cell main matrix.

η is the fraction of its aggregate rate the *old* (background) side releases to
an arriving batch — [`rdma-hw.cc:1870`](../../../src/point-to-point/model/rdma-hw.cc#L1870):

```cpp
oldShare = floor((1.0L - migrationReleaseRatio) * oldAggregate);
newShare = link->second > oldShare ? link->second - oldShare : 0;
```

So larger η ⇒ background releases more ⇒ the collective gets capacity sooner.

## What varied, and the proof that nothing else did

Only `CBAP_MIGRATION_RELEASE_RATIO`. The key is absent from `s4_config.txt`, so
appending it is purely additive — it cannot perturb another setting. The runner
enforces this mechanically: after generating each cell's config it diffs against
the η=0.50 form and **refuses to run unless exactly one line differs**.

Held identical across all five: topology, flow file, seed 2, MIN_RATE,
Qmin/Qmax, f_inc/f_dec, ECN/PFC parameters, stop time 5.5 s,
`QLEN_MON_END`, sample interval 10 µs, `CC_MODE 30`, `CBAP_ENABLE 1`.

**η=0.50 was not re-run.** It is the compiled default
([`third.cc:159`](../../../scratch/third.cc#L159)) and `s4_config.txt` never
overrides it, so the main-matrix cell `m_cbapsba_s4_seed2` *is* the η=0.50 point.
Reuse was gated, not assumed: regenerating the config at η=0.50 reproduced
`config_sha256 = 5bf2c24e…d8702` byte-for-byte.

All four new cells ran on binary `084da1fc7000866a…`, identical to the matrix
baseline. DCQCN/DCTCP/TIMELY/HPCC were **not** re-run; their S4 rows are copied
from `final_report/final_results.csv` as fixed reference points.

Per-cell configuration hashes (all five distinct, as they must be):

| η | config_sha256 | wall | incast |
|---|---|---|---|
| 0.20 | `0480b1719ea5…` | 3179 s | 64/64 |
| 0.35 | `99d9f2d7a07c…` | 3090 s | 64/64 |
| 0.50 | `5bf2c24e6dfb…` (reused) | 2912 s | 64/64 |
| 0.65 | `06add77fcc47…` | 3167 s | 64/64 |
| 0.80 | `39fc1217ed35…` | 3118 s | 64/64 |

## Results

| η | mean FCT | p95 | p99 FCT | CCT | goodput | retention | bg min | queue mean | queue p99 | ECN | >Qmax | oversub |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.20 | 239.55 | 239.58 | 239.58 | 339.58 | 2.241 | 86.28 % | 7.301 | 883 739 | 1 271 224 | 9 474 | 69.95 % | 237.5 ms |
| 0.35 | 148.80 | 148.83 | 148.83 | 248.83 | 3.607 | 79.35 % | 5.935 | 741 859 | 1 268 080 | 9 350 | 59.02 % | 146.9 ms |
| 0.50 | 107.82 | 107.85 | 107.85 | 207.85 | 4.978 | 74.25 % | 4.283 | 627 060 | 1 264 936 | 8 983 | 50.49 % | 105.0 ms |
| 0.65 | 85.02 | 85.04 | 85.04 | 185.04 | 6.313 | 70.27 % | 3.200 | 12 780 | 52 400 | **0** | **0 %** | **0 ms** |
| 0.80 | 70.11 | 70.13 | 70.13 | 170.13 | 7.655 | 67.11 % | 1.826 | 10 922 | 50 304 | **0** | **0 %** | **0 ms** |

FCT/CCT in ms, goodput and bg min in Gbps, queue in bytes.
All five: **100 % completion, 0 PFC, 0 pause, 0 drops, 0 retransmission, queue
drained** → every η is inside the safe operating region.

### The knob works, and its range is wide

| quantity | η=0.20 → η=0.80 | span |
|---|---|---|
| incast p99 FCT | 239.58 → 70.13 ms | **3.42×** |
| incast goodput | 2.241 → 7.655 Gbps | **3.42×** |
| background retention | 86.28 → 67.11 % | **19.17 points** |
| background minimum | 7.301 → 1.826 Gbps | 4.00× |

Trends versus the mechanism's prediction (checked in code, not by eye):

| metric | predicted | measured |
|---|---|---|
| incast p99 FCT | ↓ | ↓ monotonic — **as predicted** |
| CCT | ↓ | ↓ monotonic — **as predicted** |
| background retention | ↓ | ↓ monotonic — **as predicted** |
| background minimum | ↓ | ↓ monotonic — **as predicted** |
| background service debt | ↑ | **flat (identically 0)** — no trend |
| queue mean occupancy | ↑ | **↓ monotonic — opposite** |
| time above Qmax | ↑ | **↓ monotonic — opposite** |
| oversubscription duration | ↑ | **↓ monotonic — opposite** |

Nothing was tuned to obtain these. The two groups that contradict the
prediction are reported as measured and explained below.

## 1. Queue pressure *falls* as η rises — the prediction was wrong

I expected higher η to deepen queues, since the collective gets more capacity
sooner. The data says the opposite, monotonically: mean occupancy −99 %, time
above Qmax 69.95 % → 0 %, oversubscription duration 237.5 ms → 0 ms.

The reason is that η controls *how quickly capacity is handed over*, not how much
total demand exists. At low η the background side releases slowly, so admitted
collective flows sit at rates the link cannot yet honour and the excess queues.
At high η the handover completes promptly, offered load tracks capacity, and the
queue never builds. **Faster collectives and safer queues are not in tension
here** — the entire cost lands on the background flow, which is precisely the
trade-off the knob is meant to expose.

Note `queue_p99` is a poor probe at this fan-in: p95 = p99 = peak in every cell
because the burst tail is narrow, so p99 is pinned to the peak and moves only
0.49 % across η=0.20…0.50. It is reported for completeness, but mean occupancy,
time-above-threshold and oversubscription duration are the discriminating
statistics. This is a measurement-methodology point, not an algorithm property.

## 2. A regime boundary between η=0.50 and η=0.65

| η | ECN marks | samples above KMIN (400 KB) | utilisation | regime |
|---|---|---|---|---|
| 0.20 | 9 474 | 4.32 % | 0.986 | admission + ECN backend |
| 0.35 | 9 350 | 2.67 % | 0.980 | admission + ECN backend |
| 0.50 | 8 983 | 51.26 % above Qmin | 0.977 | admission + ECN backend |
| 0.65 | **0** | **0.00 %** (0 of 549 999) | 0.972 | **admission-only** |
| 0.80 | **0** | **0.00 %** | 0.969 | **admission-only** |

At η ≥ 0.65 the bottleneck queue never reaches KMIN across all 549 999 samples,
so no packet is ever ECN-marked and the DCQCN steady-state backend **is never
invoked** — while utilisation stays at 0.97. CBAP-SBA is running on explicit
admission alone.

This was verified rather than inferred: 0 error lines, 0 `Drop:`, 64/64 flows
delivering the full 67 108 864 B, trace length 549 999 rows reaching t = 5.5000 s
(identical to the other cells), and the queue maximum differing per η
(1 271 224 / 1 268 080 / 1 265 984 / 52 400 / 50 304) — a hard cap would produce
one identical value. Time spent near the maximum also falls monotonically
(4.2 % → 2.6 % → 1.8 %), so the low queues are a real effect, not clipping.

## 3. Where HPCC sits relative to the curve

**HPCC is not dominated by any η, and it does not dominate any η.** It is a
single fixed point outside the frontier, at the extreme FCT-favouring end:

| point | retention | p99 FCT | vs HPCC |
|---|---|---|---|
| η=0.20 | 86.28 % | 239.58 ms | +23.28 pts background, 3.98× slower |
| η=0.35 | 79.35 % | 148.83 ms | +16.35 pts, 2.47× slower |
| η=0.50 | 74.25 % | 107.85 ms | +11.25 pts, 1.79× slower |
| η=0.65 | 70.27 % | 85.04 ms | +7.27 pts, 1.41× slower |
| η=0.80 | 67.11 % | 70.13 ms | **+4.11 pts, 1.16× slower** |
| **HPCC** | **63.00 %** | **60.24 ms** | — |
| DCQCN | 100.00 % | 1127.32 ms | 18.7× slower than HPCC |

Every η retains more background throughput than HPCC. At η=0.80 CBAP-SBA comes
within **1.16×** of HPCC's p99 FCT while keeping 4.11 more points of background
throughput — HPCC's remaining 14.1 % FCT advantage is real but no longer the
1.79× gap the default η=0.50 shows.

On queue depth the crossover is decisive: at η ≥ 0.65 CBAP-SBA's queue p99 is
**0.06× HPCC's** (52 400 / 50 304 B vs 899 741 B), a 17× reduction, with zero ECN
marks against HPCC's INT-driven control.

DCQCN's 100 % retention is not protection — its collective only obtains
0.476 Gbps and cannot displace the background flow at all (see the main matrix
analysis: the background flow received 0 CNPs while the 64 incast flows absorbed
all 9 582).

## 4. Pareto B is degenerate in S4 — and that is itself a finding

`bg_service_debt_bytes = 0.0` for all five η **and** for both reference
algorithms. The 4 GB background flow finishes inside the 5.5 s stop time in every
case, so no debt accrues and the requested x-axis collapses to a line.

`paretoB_debt_vs_cct.csv` is still emitted (it is the requested pairing, and the
uniform zero is a result). `paretoB2_bgmin_vs_cct.csv` substitutes background
*minimum throughput*, which is defined and discriminating here
(7.301 → 1.826 Gbps), so the debt-side trade-off remains plottable.

## 5. What this does and does not establish

Establishes: a single existing parameter moves CBAP-SBA along a **3.42×
FCT / 19-point background-retention frontier** with no configuration change
beyond one line, no loss of safety at any setting, and a qualitative regime
change at η ≥ 0.65 where congestion feedback becomes unnecessary. The
feedback-driven baselines expose no comparable control: their operating point is
a property of the algorithm, not a policy an operator can select.

Does not establish:
- **Any scenario other than S4.** The frontier's shape at other fan-ins,
  message sizes or background loads is unmeasured.
- **Optimality.** These are five samples of a continuum; no claim that the
  frontier is convex or that intermediate η interpolate smoothly. The regime
  boundary between 0.50 and 0.65 in particular is unresolved — it could be sharp
  or gradual, and the sweep cannot distinguish.
- **Dispersion.** One deterministic run per point, as in the main matrix
  (`SIM_SEED` is inert on all reachable paths; see the matrix RESULTS_README).
  No confidence intervals are reported, because a zero-width interval from one
  deterministic observation would misrepresent it.
- **η > 0.80 or η < 0.20.** Untested; the safe region is characterised only
  within the measured range.
- **The MIN_RATE limitation is unchanged.** 64 × 100 Mb/s = 6.4 Gbps of floor
  remains, per the main matrix's known limitation 2. It was deliberately not
  touched in this sweep.

## Reproducing

```bash
cd <repo>/simulation
bash experiment/scheme1_sba/run_eta_sweep.sh          # 4 cells, ~3.5 h, serial, resumable
cd experiment/scheme1_sba && python3 eta_metrics.py   # or python2
```

The runner refuses to start if the binary or topology hash has moved since
`matrix_baseline.manifest`, because the four new cells must share one binary with
the reused η=0.50 cell. Determinism check: η=0.50 must reproduce mean FCT
107.81862840625 ms exactly — it did, in a rebuilt Ubuntu 24.04 / gcc 13
container, confirming the numbers are environment-independent.

## Files

```
eta_sweep/
  eta_sweep_s4.csv                     7 rows (5 eta + DCQCN + HPCC) x 88 columns
  paretoA_retention_vs_p99fct.csv      x = background retention, y = incast p99 FCT
  paretoB_debt_vs_cct.csv              x = service debt (degenerate: all 0), y = CCT
  paretoB2_bgmin_vs_cct.csv            x = background minimum, y = CCT
  paretoC_queue_vs_p99fct.csv          x = queue p99, y = incast p99 FCT
  manifests/                           4 per-cell manifests (eta, hashes, wall time)
```

Each Pareto CSV carries `label, kind, eta, x_metric, x_value, x_label, y_metric,
y_value, y_label`, with `kind` separating swept points (`cbapsba_eta`) from fixed
references (`reference_hpcc`, `reference_dcqcn`).
