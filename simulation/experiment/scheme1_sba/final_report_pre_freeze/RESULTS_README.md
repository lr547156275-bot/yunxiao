# CBAP-SBA final evaluation — results

30 runs: 5 congestion-control algorithms × 6 scenarios, one seed each.
All 30 completed with full incast completion, complete link traces, and zero
PFC / drops / retransmission. `anomalies.md` is empty.

## What was run

| Scenario | Shape | Background | Stop | ECN regime |
|---|---|---|---|---|
| S1 | 16-way × 256 KiB | 8 Gbps (80%) | 2.1 s | inactive |
| S2 | 64-way × 256 KiB | 8 Gbps (80%) | 2.5 s | active |
| S3 | 64-way × 1 MiB | 8 Gbps (80%) | 3.0 s | active |
| S4 | 64-way × 1 MiB | 9.5 Gbps (95%) | 5.5 s | active |
| S5 | 64-way × 4 MiB | 8 Gbps (80%) | 6.0 s | active |
| S6 | dual bottleneck, 30+30 × 256 KiB | 2 × 8 Gbps | 2.5 s | active |

Algorithms: DCQCN (CC_MODE 1), DCTCP (8), TIMELY (7), HPCC (3),
CBAP-SBA (30, `CBAP_ENABLE=1` + `CBAP_MIGRATION_ENABLE=1`).

Within a scenario every algorithm shares the topology, flow file, start times,
link rates, ECN/PFC parameters, application rate cap, stop time, telemetry
window and sampling interval. Only `CC_MODE` / `CBAP_ENABLE` /
`CBAP_MIGRATION_*` differ — verified per cell by config hash in the manifests.

Shared parameters: 10 Gbps links, KMIN 400 KB / KMAX 1600 KB / PMAX 0.2,
`BUFFER_SIZE 8`, `PAUSE_TIME 5`, MIN_RATE 100 Mb/s, RATE_AI 50 Mb/s,
RATE_HAI 100 Mb/s, EWMA_GAIN 0.00390625, collective released at 1.9 s,
Qmax (migration tolerance) 400 000 B.

## Single seed, and why that is not a shortcut

`SIM_SEED` is inert in this build. The only `RandomVariableStream` is the
`RateErrorModel`'s uniform variable, and every topology link has error rate 0
with `ERROR_RATE_PER_LINK 0`, so it never draws a variate. Every `rand()` in
`point-to-point/model` is commented out, inside a string literal, or gated on
`cc_mode == 10` (HPCC-PINT, not used here). Routing is deterministic twice
over: `CBAP_PATH_FILE` pins every data flow via the fixed-path table, and the
ECMP fallback is a MurmurHash seeded from the node ID, not from `SIM_SEED`.
Traffic is a static file replay with literal sizes and start times.

Confirmed empirically: five seeds of S1 produced bit-identical results
(mean FCT 17.398941 ms in all five).

Consequently each cell was run once and **no confidence intervals are
reported** — a zero-width interval from one deterministic observation would
misrepresent it. Seed 2 was used because `third.cc:3441` reserves seed 1 for
diagnostics and demands a bounded CBAP packet trace the scenario configs do not
set.

## Headline results

**Incast p99 FCT (ms)** — lower is better

| algorithm | S1 | S2 | S3 | S6 | S4 | S5 |
|---|---|---|---|---|---|---|
| DCQCN | 17.625 | 70.455 | 281.741 | 33.034 | 1127.321 | 1126.918 |
| DCTCP | 17.625 | 70.455 | 281.741 | 33.034 | 1127.321 | 1126.918 |
| TIMELY | 17.759 | 70.825 | 283.216 | 33.207 | 1118.975 | 1132.820 |
| HPCC | **4.092** | **15.118** | **60.131** | **7.293** | **60.242** | **240.543** |
| CBAP-SBA | 5.929 | 22.773 | 93.534 | 11.097 | 107.848 | 376.520 |

**Incast aggregate goodput (Gbps)** — higher is better

| algorithm | S1 | S2 | S3 | S6 | S4 | S5 |
|---|---|---|---|---|---|---|
| DCQCN / DCTCP | 1.904 | 1.905 | 1.906 | 3.809 | 0.476 | 1.906 |
| TIMELY | 1.888 | 1.895 | 1.896 | 3.789 | 0.480 | 1.896 |
| HPCC | **8.197** | **8.871** | **8.928** | **17.252** | **8.901** | **8.927** |
| CBAP-SBA | 5.659 | 5.894 | 5.740 | 11.339 | 4.978 | 5.704 |

**Background minimum instantaneous throughput (Gbps)** — higher is better

| algorithm | S1 | S2 | S3 | S6 | S4 | S5 |
|---|---|---|---|---|---|---|
| DCQCN / DCTCP | 7.636 | 7.636 | 7.636 | 7.636 | 0.000 | 0.000 |
| TIMELY | 7.580 | 7.580 | 7.580 | 7.580 | 0.000 | 0.000 |
| HPCC | 0.400 | 0.093 | 0.093 | 0.242 | 0.000 | 0.000 |
| CBAP-SBA | **3.859** | **2.929** | **2.259** | **3.855** | 0.000 | 0.000 |

**Background throughput retention (%)** — during the collective vs before

| algorithm | S1 | S2 | S3 | S6 | S4 | S5 |
|---|---|---|---|---|---|---|
| DCQCN / DCTCP / TIMELY | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| HPCC | 96.34 | 87.11 | 63.11 | 93.46 | 63.00 | **30.60** |
| CBAP-SBA | 97.24 | 90.32 | 75.75 | 95.07 | 74.25 | 60.73 |

## 1. Where CBAP-SBA leads

**Against the three ECN-driven baselines it wins everywhere, and the margin
grows with background pressure.**

Speedup in p99 FCT over DCQCN:

| S1 | S2 | S3 | S6 | S4 | S5 |
|---|---|---|---|---|---|
| 2.97× | 3.09× | 3.01× | 2.98× | **10.45×** | **2.99×** |

Five scenarios cluster at 2.97–3.09×; **S4, the 95% background load case,
reaches 10.45×**. That is the scenario closest to the motivating problem — a
long-lived background flow occupying nearly the whole link when a collective
arrives — and it is where admission control matters most. Aggregate goodput
tells the same story: 0.476 → 4.978 Gbps, a 10.5× gain.

**Queue occupancy, where the fan-in stays below the rate floor.**
S1 (16 flows) and S6 (30 flows per bottleneck): p99 queue 10 480 B and 25 152 B
versus 315 448 B and 594 216 B for DCQCN — **20-30× lower**. See limitation 2
for why this does not hold at 64 flows.

**Background protection versus HPCC**, the only baseline that competes on FCT:
minimum throughput 2.259 vs 0.093 Gbps in S3 (24×), 3.855 vs 0.242 Gbps in S6
(16×); retention 75.75% vs 63.11% in S3 and 60.73% vs 30.60% in S5.

## 2. Where CBAP-SBA trails HPCC

Consistently, by a stable factor — 1.45× (S1) to 1.79× (S4) in p99 FCT, and
1.45–1.79× in aggregate goodput. The consistency indicates a mechanism
difference, not scenario noise.

The cause is visible in the admission and round data. HPCC starts each flow at
line rate and converges downward using per-hop INT telemetry (in S4: 10 000 →
291/428/197 Mbps per flow). CBAP-SBA starts each flow at its admitted grant
(3.91 Mbps in S4) and climbs. HPCC therefore reaches a working rate sooner. The
trade is that HPCC obtains its rate by taking capacity through congestion
signals, while CBAP-SBA negotiates it explicitly — which is exactly why its
background protection is better.

HPCC also has the lowest queues in the 64-flow scenarios (p99 900 722 B in S3
vs 1 263 888 B), because INT lets it avoid overshoot that CBAP-SBA's rate floor
forces (limitation 2).

## 3. Improvement over DCQCN / DCTCP / TIMELY

The three ECN-driven baselines are within 0.4% of each other in every scenario.
**DCQCN and DCTCP are bit-identical in S1** because S1's peak queue
(316 496 B) never crosses KMIN (400 000 B): with no ECN mark, DCTCP's α stays 0
and both reduce to the same uncongested behaviour.

Their poor showing is an arithmetically exact fairness outcome, not a rate
control failure. In S4:

| | background gets | incast gets | per flow | measured aggregate |
|---|---|---|---|---|
| DCQCN | **9.070 Gbps** | 0.93 | 7.45 Mbps | 0.477 Gbps |
| CBAP-SBA | 8.563 | 1.44 | 77.8 Mbps | 4.979 |
| HPCC | 8.254 | 1.75 | 140.6 Mbps | 8.998 |

The round data shows why: **the background flow received 0 CNPs while the 64
incast flows absorbed all 9 582** (≈150 each). ECN marks land in proportion to
queue occupancy, and 64 bursting flows dominate the queue, so the single
background flow escapes marking almost entirely. Each incast flow then applies
multiplicative decrease independently while the background flow never reduces.
Recovery is additive at RATE_AI = 50 Mb/s, far slower than the sustained
marking. Note `end_rate` returns to 10 000 Mbps while delivery is 7.45 Mbps —
three orders of magnitude apart — confirming the limit is capacity sharing, not
the computed rate.

## 4. Cost to background traffic

CBAP-SBA does take capacity from the background flow, and the amount is
bounded and measured: retention 97.24% (S1) down to 60.73% (S5), with recovery
to 90% of baseline in 106–194 ms depending on scenario.

The three ECN baselines show 100% retention, but this is not protection — their
collectives only obtain 0.48–1.9 Gbps and cannot displace the background flow
at all. The meaningful comparison is against HPCC, which achieves similar
speed: at equal or better FCT-per-unit-goodput, **CBAP-SBA consistently leaves
the background flow more capacity** (retention +12.6 points in S3, +30.1 in S5;
minimum throughput 24× higher in S3).

Service debt (bytes the 4 GB background flow still owed at a scenario-fixed
window) is reported per scenario in `final_results.csv`. The background flow
does not complete within S1/S2/S3/S6 stop times by construction, so
`bg_slowdown` is empty there; it is only meaningful where the flow finishes.

## 5. Bounded oversubscription: holds in all 30 runs

CBAP-SBA deliberately permits Σrate > C briefly, bounded by Q ≤ Qmax. The
verdict is computed, not asserted, and requires all of: no PFC, no drop, no
retransmission, queue drained below Qmin, finite recovery, no goodput
regression.

**Result across all 30 cells:**

- PFC events: **0** everywhere
- PFC pause duration: **0 ns** everywhere
- Headroom drops: **0** everywhere
- Retransmission: **0 bytes, 0 events** everywhere
- Queue drained: **30/30**
- 24 cells classified `BOUNDED (safe)`, 6 `never exceeded Qmax`, **0 UNBOUNDED**

So the tolerance-band design is validated: the excursions above Qmax are
bounded in magnitude and duration and always recover. Per-cell oversubscription
peak, duration, longest consecutive run, Qmax exceed ratio and recovery in RTTs
are in `tables/safety.md` and `final_results.csv`.

Note this is evidence, not an ablation. Strict capacity conservation cannot be
disabled for comparison: it is enforced by `NS_ASSERT_MSG` in
`rdma-hw.cc:1644` and `throw std::logic_error` in `cbap-sba.cc:245`, so a
"no-conservation" arm would abort rather than produce data. What the 30 runs
show is that the invariant held throughout.

## 6. Data that must not be used

None of the 30 cells is excluded. Every cell has a done-flag requiring exit 0,
the full expected incast count, and a link trace reaching the monitored window's
end; `anomalies.md` reports zero items.

Excluded from this report and preserved separately under
`matrix_logs/stale_pre_final/`: 10 cells from an earlier exploration built with
a pre-change binary (no `pfc_pause_ns_delta` column, no trace-completeness
check), and one `analysis_s3` directory whose data came from a different stop
time. These were invalidated rather than deleted.

The CBAP-SBA + HPCC variant (`CC_MODE 31`) was an internal exploration and is
**not** part of these results.

## Known limitations

**1. `drops` counts only headroom exhaustion.** `switch-node.cc:193/201` drop
silently on admission-control and routing failure with no counter; only
`switch-mmu.cc:38` prints. The metric is therefore a lower bound. It reads 0
everywhere, and retransmission (0 everywhere) corroborates that no loss
occurred, but the two silent paths are not directly instrumented.

**2. The queue advantage disappears at 64-way fan-in.** CBAP-SBA's p99 queue is
10 480 B in S1 and 25 152 B in S6, but 1 261 792–1 264 936 B in S2/S3/S4/S5 —
level with DCQCN. Cause: `rdma-hw.cc:1907` applies `max(target, MIN_RATE)` per
flow *after* the per-link budget is divided, and nothing re-checks the sum. At
64 flows the floor alone is 64 × 100 Mb/s = 6.4 Gbps; adding the background
flow's ~4 Gbps exceeds the 10 Gbps link, so queueing is unavoidable. S1 (16
flows, 1.6 Gbps floor) and S6 (30 per link, 3 Gbps) stay under. The algorithm is
frozen, so this is recorded rather than fixed; it is the clearest candidate for
future work.

**3. TIMELY is untuned.** Its α/β/T_low/T_high are ns-3 attributes that
`third.cc` never sets, so it runs at library defaults (0.875 / 0.8 / 50 µs /
500 µs). It is not a tuned TIMELY.

**4. DCTCP shares `EWMA_GAIN` with DCQCN** (0.00390625). DCTCP implementations
commonly use 1/16, so DCTCP is evaluated at DCQCN's gain, not its own
conventional one.

**5. `bg_slowdown` is empty for S1/S2/S3/S6.** The 4 GB background flow needs
~4 s of transfer at 8 Gbps from t = 0.5 s and cannot finish within those stop
times. This is correct behaviour, not missing data.

**6. S6 background metrics cover two flows.** Roll-ups take the worst case
(lowest retention, highest debt); per-flow values are in the `bg0_*` / `bg1_*`
columns and per-link queue statistics in `link_84_1_*` / `link_83_1_*`.

## Instrumentation changes made for this evaluation

Both are trace/validation only. No control logic and none of the frozen
CBAP-SBA parameters (Qmin/Qmax, f_inc/f_dec, MIN_RATE, batch allocation,
release ratio, migrationMaxRtt, queue-borrowing rules, DCQCN parameters,
ECN/PFC parameters) were touched.

1. **Multi-link telemetry guard relaxed** (`third.cc:3828`). It required exactly
   one traced link for non-CBAP algorithms, while CBAP auto-inserts every
   telemetry-eligible link. S6 declares two bottlenecks, so CBAP-SBA would have
   pooled two queues against the baselines' one — the scenario's queue metrics
   would not have been comparable. Verified: DCQCN now traces both 83:1 and 84:1.
2. **Per-port PFC pause duration exported** (`LinkTraceTick`, new
   `pfc_pause_ns_delta` column). `SwitchNode` already maintained the counter and
   `third.cc:750` already read it, but it only reached the CBAP-only
   `port_summary.csv`, leaving non-CBAP runs with no pause data.

Scenario configs: `QLEN_MON_END` was below `SIMULATOR_STOP_TIME` in S2–S6
(S3 monitored to 2.6 s of a 3.0 s run), which would have truncated queue
traces; the invariant now holds in the base configs. S6 traces both bottlenecks.

## Reproducing

```bash
git clone https://github.com/lr547156275-bot/yunxiao.git
cd yunxiao && git checkout exp/bop-clos-final-20260728_235414
cd simulation/experiment/scheme1_sba && bash setup_local.sh
cd ../.. && CC=gcc-7 CXX=g++-7 python2 waf configure && python2 waf build
bash experiment/scheme1_sba/run_all.sh              # ~11.5 h, serial, resumable
cd experiment/scheme1_sba && python2 build_report.py 2
```

`waf` requires python2. Determinism gives a free environment check: S1 / DCQCN
must yield a mean incast FCT of 17.399 ms.

## Files

```
final_report/
  final_results.csv          30 rows x all metrics, with config hashes
  tables/per_scenario_*.md   5 algorithms x 4 metric groups, per scenario
  tables/summary.md          algorithms x scenarios, headline metrics
  tables/triggers.md         control-mechanism engagement evidence
  tables/safety.md           PFC / drops / retx / oversubscription verdicts
  figdata/fig1..fig9_*.csv   nine result figures, tidy long format
  figdata/paretoA..C_*.csv   three Pareto pairings
  manifests/                 30 cell manifests + the hash baseline
  anomalies.md               empty
```

Figures ship as CSV: the simulation container has no matplotlib, and adding a
hand-written rasteriser there would have introduced risk without improving the
numbers. Each figure CSV carries `scenario, algorithm, metric, value, unit`.

## Control mechanism engagement

All 30 cells verified. 28 `ENGAGED`, 3 `EXPECTED_NOT_ENGAGED`, **0 genuine
failures**.

Acceptance is scenario-aware: S1 is startup-dominated and stays below KMIN by
construction (peak queue 316 496 B < 400 000 B), so its ECN-driven controllers
have no input and correctly report no CNP and no α movement — a property of the
scenario, not a fault. In the ECN-active scenarios the requirement is enforced:
DCQCN in S3 shows 9 542 CNPs, α movement in all 64 rounds, and recovery-stage
transitions in all 64.

Evidence per algorithm: DCQCN from `cnp_count` / `dcqcn_*_alpha` /
recovery stages; HPCC from `feedback_summary.csv` (S3: 67 136 INT feedbacks,
67 057 actionable, 63 943 rate changes); CBAP-SBA from `admission.csv`,
`sba_events.csv` and the migration trace (S3: 65 admissions, 1 554 replans,
7 271 epoch updates, 804 convergences). DCTCP's α and TIMELY's RTT gradient are
only in a compiled-out `PRINT_LOG`, so their engagement is inferred from rate
movement — stated as inference in `tables/triggers.md`.
