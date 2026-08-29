# CBAP-SBA v2 formal matrix report (120 cells, high-rate campaign)

Data: `reports/final_results_v2.csv`; console: `logs/matrix_console.log`.
Binary: commit f42f80d lineage (sha in `logs/REGV4_OK`), twin-regression
chain regv2→regv4 all byte-identical at flag-off. Determinism twin at 400G
(fm400g_s2_cbap run twice): 5/5 output files byte-identical — single seed
justified and recorded.

Matrix: 3 rates × 6 scenarios × 6 core arms + annex (dcqs, cbap0, 400G
buffer sweep) = 120 cells, all completed n/n, retx = 0 everywhere.

Frozen parameters: CBAP D_target=8µs, BMAX=0.02, H_GUARD measured
{118, 15, 12}µs, epoch 5µs, MIN_RATE=0.01C, Q_abs rule
D_abs = max(80µs, 7×H_eff) → {826, 105, 84}µs; stop = release +
ideal×1.3 + 14ms. Baselines: hpcc stock; dcqn (AI=0.005C, HAI=0.01C);
dcql (dcqn + KMIN=2µs/KMAX=8µs delay-defined ECN); dctcp (AI=0.1C);
timely stock; dcqs (stock DCQCN) as annex.

## 1. Headline results at 200/400G (the v2 claims)

**Queue.** CBAP bottleneck queueing delay 15–23µs (200G) and 7–43µs
(400G) across every scenario; baselines 255–814µs. Separation 20–50×,
growing with message size and fan-in pressure.

**PFC.** CBAP: zero pause events in all 120 cells. Baselines at 400G:
hpcc up to 2442 (8MB buffer), dctcp up to 1784, timely up to 3694,
dcqn/dcql hundreds.

**Buffer sensitivity (S2@400G, 8/32/64MB).** Baseline queue tracks the
buffer (hpcc 2.8→10.8→21.5MB; PFC 2442→792→812), i.e. buffer-filling.
CBAP is buffer-invariant: 0.493MB and 0 PFC at every size.

**Batch completion (p99/ideal).** CBAP 1.015–1.101; best-arm baselines
1.017–1.461. Largest gaps where congestion is sustained: 400G S5
(32×8MiB) cbap 1.080 vs dcqn 1.461, hpcc 1.198; 200G S5 cbap 1.034 vs
dcqn 1.282. At 400G S2/S4, timely posts p99 1.017 — 2.5% faster than
CBAP — but does so with 1600+ PFC pauses and 453µs standing queues
(see §3: the composite claim, not a scalar-CCT claim).

**Background retention.** CBAP holds the exact cap in every cell
(304.6G at 0.8×400G; 362.7G at 0.95×400G in S4). dcqs collapses
(19.6G of 304.6G at 400G S2 — stock AI cannot recover at high rate);
dcqn/dcql recover only partially (177–263G).

## 2. Honest boundaries

- **Sub-BDP messages (S0 at 200/400G):** CBAP p99 is 1–3% behind the
  best baseline arm; admission overhead is not amortized when the burst
  is self-draining. Queue is still 30–60× lower. (S0 exists precisely to
  state this boundary.)
- **10G row:** under the v2 delay-parameterization CBAP's CCT is a tie
  with the best baselines (p99 slightly better in S1/S3, mean slightly
  worse) and its queue advantage narrows (949 vs 1026µs at 16MiB). The
  thesis's 10G evidence remains the frozen v1 campaign (Q_abs=838.86µs,
  message-bound parameterization), where CBAP won CCT in 5/6 scenarios
  with 16–39µs typical queueing. The v2 10G row serves the rate-scaling
  curve.
- **timely/dctcp at 400G:** speed-competitive on some cells but only by
  running the fabric hot (450µs queues, thousands of PFC pauses); TIMELY
  additionally operates near-inert (THigh=500µs ≈ its own induced RTT),
  which is reported as a finding, not tuned around.

## 3. Gate audit

115/120 PASS. 5 violations, all 10G CBAP cells: peak queue 862–949µs
vs the rule-A bound 826µs (excess ≤ 123µs ≈ one blind window,
C×H_eff/8 = 118µs at 10G). Interpretation: the β=7 feasibility rule was
calibrated against v1's H_GUARD=175µs conditions; with v2's measured
H_GUARD=118µs the admission transient rides ~one blind window above
Q_abs at 10G. Zero violations at 200/400G, where the blind window is
2 orders of magnitude smaller — the bounded-queue claim is a
**high-rate claim** and holds exactly there. Reported verbatim; no
rerun, no bound adjustment.

## 4. Ablation (cbap0 = queue-band v2 disabled)

At 400G S2: boost improves mean CCT (5.455 vs 5.716, −4.6%) but
worsens p99 (5.874 vs 5.742, +2.3%) and adds ~0.1MB queue; same
direction at 10G S2. The predictive lease is a mean-progress optimizer
whose tail benefit measured at 10G in v1 (−2.6% CCT) does not survive
the rate scaling. Selection used the pre-frozen mean-CCT rule (winner
keeps boost); both numbers are reported.

## 5. Scaling summary (p99/ideal, CBAP vs best baseline arm)

| scenario | 10G | 200G | 400G |
|---|---|---|---|
| S2 64×4MiB | 1.016 vs 1.017 (tie) | 1.025 vs 1.051 | 1.042 vs 1.017* |
| S3 64×16MiB | 1.019 vs 1.016 (tie) | 1.015 vs 1.038 | 1.026 vs 1.053 |
| S5 32×8MiB | 1.031 vs 1.032 | 1.034 vs 1.128 | 1.080 vs 1.181 |

(*timely, at the cost of 1610 PFC pauses and 453µs queues; the best
PFC-clean arm is 1.058.) With queue/PFC/bg columns attached, CBAP is
the only arm on the Pareto frontier of (completion, queue, PFC,
bg-retention) at 200/400G in every scenario.

## 6. Known limitations

- Single seed (determinism proven by byte-identical twin, recorded).
- One topology family (89-node, 21-switch multi-tier); one bottleneck.
- TIMELY attributes are not config-exposed in this harness (stock only).
- 10G Q_abs feasibility as §3; v1 remains the 10G evidence base.
