# CBAP-SBA — experimental metadata (FINAL FREEZE)

Everything needed to describe or reproduce the reported results. All values are
read from the frozen artifacts, not from memory.

## 1. Topology — 68-host two-tier Clos (folded, non-oversubscribed fabric)

`experiment/scheme1_sba/topology.txt`, header `89 21 136` = 89 nodes, 21
switches, 136 links.

```
Spine   85  86  87  88                        4 switches
            |  full mesh to every leaf, 2 us
Leaf    68 .. 84                              17 switches
            |  4 hosts each, 1 us
Host    0  .. 67                              68 hosts
```

| tier | count | node ids | fan-out |
|---|---|---|---|
| spine | 4 | 85–88 | 17 down-links each |
| leaf | 17 | 68–84 | 4 hosts + 4 up-links each |
| host | 68 | 0–67 | 1 access link each |

* Every link **10 Gbps**. Access delay **1 µs**, fabric delay **2 µs**.
* Host↔host path is 4 hops (host→leaf→spine→leaf→host); the simulator reports
  `maxRtt = 15200 ns`, `maxBdp = 19000 B`.
* Each leaf has 4 hosts against 4 up-links, so the **fabric is 1:1 and is not the
  bottleneck**. Congestion is created deliberately at the *last hop into the
  receiver*: all incast flows target one host, so link `84:1`
  (leaf 84 → host 64) is the choke point. S6 adds a second, independent choke
  point at `83:1` (leaf 83 → host 60).

Note the label "64-host" is approximate: the topology provisions **68 hosts**
(0–67); the largest collective uses 64 senders plus 1 background sender and
1 receiver.

## 2. Scenarios S1–S6

All share the topology, the release time (collective at **t = 1.9 s**), the
background start (**t = 0.5 s**), and the ECN/PFC parameters in §4.

| tag | scenario name | incast | message | background | bg cap | stop | traced link(s) | ECN regime |
|---|---|---|---|---|---|---|---|---|
| S1 | `s1_fan16_256k_bg80` | 16 | 256 KiB | 1 × 4 GB | 8 Gbps (80 %) | 2.1 s | `84:1` | inactive |
| S2 | `s2_fan64_256k_bg80` | 64 | 256 KiB | 1 × 4 GB | 8 Gbps | 2.5 s | `84:1` | active |
| S3 | `s3_fan64_1m_bg80` | 64 | 1 MiB | 1 × 4 GB | 8 Gbps | 3.0 s | `84:1` | active |
| S6 | `s6_dual_bottleneck` | 30 + 31 | 256 KiB | 2 × 4 GB | 8 Gbps × 2 | 2.5 s | `84:1`, `83:1` | active |
| S4 | `s4_fan64_1m_bg95` | 64 | 1 MiB | 1 × 4 GB | 9.5 Gbps (95 %) | 5.5 s | `84:1` | active |
| S5 | `s5_fan64_4m_bg80` | 64 | 4 MiB | 1 × 4 GB | 8 Gbps | 6.0 s | `84:1` | active |

Each scenario changes **one** dimension relative to a neighbour: S1→S2 fan-in,
S2→S3 message size, S3→S4 background load, S3→S5 message size, S2→S6 number of
bottlenecks.

Flow file format (`third.cc:1679`): `src dst pg dport size start_time`, static
replay with literal sizes and times. Example (S4):

```
65                                  <- flow count
65 64 0 100 4000000000 0.5          <- background: host65 -> host64, 4 GB, pg 0
0  64 3 100 1048576    1.9          <- incast 1:  host0 -> host64, 1 MiB, pg 3
...                                    64 incast flows, all released at 1.9 s
```

Background senders: host **65** (→64, leaf 84); S6 adds host **61** (→60, leaf 83).
Background flows carry priority group **0**, incast flows **3**.
S3 and S4 share one flow file hash — they differ only in `APP_RATE_CAP_BPS` and
stop time, which live in the config.

Collective duration, measured (matters for §7 of the results summary):
S2 122 ms, S3 188 ms, S4 188 ms, **S5 451 ms**.

## 3. Algorithms and CC_MODE

| algorithm | `CC_MODE` | `CBAP_ENABLE` | `CBAP_MIGRATION_ENABLE` |
|---|---|---|---|
| DCQCN | 1 | 0 | – |
| DCTCP | 8 | 0 | – |
| TIMELY | 7 | 0 | – |
| HPCC (INT) | 3 | 0 | – |
| **CBAP-SBA** | **30** | **1** | **1** |

Within a scenario, these three keys plus `ALGORITHM` and the output paths are the
**only** configuration differences — verified per cell by `config_sha256` in the
manifests.

Not used in these results: `CC_MODE 10` (HPCC-PINT, excluded because it calls
`rand()` and would break determinism) and `CC_MODE 31` (CBAP-SBA + HPCC backend,
an internal exploration only).

## 4. Unified ECN / PFC and transport parameters

Identical for all five algorithms in all six scenarios.

```
ENABLE_QCN                 1
USE_DYNAMIC_PFC_THRESHOLD  1
CLAMP_TARGET_RATE          0
PAUSE_TIME                 5
BUFFER_SIZE                8            (MB per switch)
KMIN_MAP                   1 10000000000 400     -> KMIN 400 KB
KMAX_MAP                   1 10000000000 1600    -> KMAX 1600 KB
PMAX_MAP                   1 10000000000 0.2
RATE_AI                    50Mb/s
RATE_HAI                   100Mb/s
MIN_RATE                   100Mb/s
RATE_DECREASE_INTERVAL     4
EWMA_GAIN                  0.00390625            (1/256)
FAST_RECOVERY_TIMES        5
L2_CHUNK_SIZE              4000
L2_ACK_INTERVAL            1
L2_BACK_TO_ZERO            0
ERROR_RATE_PER_LINK        0
CRFM_TRACE_SAMPLE_US       10                    (queue/flow sampling)
QLEN_MON_START             1990000000 ns
QLEN_MON_END               = SIMULATOR_STOP_TIME (invariant enforced per cell)
```

`EWMA_GAIN` is shared with DCTCP, which conventionally uses 1/16 — so DCTCP is
evaluated at DCQCN's gain (stated as a limitation). TIMELY's α/β/T_low/T_high are
ns-3 attributes `third.cc` never sets, so it runs at library defaults
(0.875 / 0.8 / 50 µs / 500 µs).

## 5. CBAP-SBA final parameters

From the config:

```
CBAP_ENABLE                   1
CBAP_CONTROL_EPOCH_US         5
CBAP_PLANNING_DELAY_US        5
CBAP_CONTROL_DELAY_US         5
CBAP_RHO                      0.95      (usable fraction of link capacity)
CBAP_EPSILON_RATE             0.02
CBAP_PRIORITY                 3
CBAP_MAX_WIRE_PACKET_BYTES    1064
CBAP_SUMMARY_BYTES            64
CBAP_GRANT_BYTES              48
CBAP_INCREASE_POLICY          0
CBAP_INCREASE_FRACTION        0.10
CBAP_INCREASE_ABSOLUTE_BPS    2000000000
CBAP_VERSION                  sba_v1_s1
CBAP_SCOPE_POLICY             0
CBAP_SCOPE_BASE_CC            1         (DCQCN steady-state backend)
CBAP_RATE_FLOOR_POLICY        1
CBAP_QUEUE_TARGET_FRACTION    0.25
CBAP_SBA_LEASE_US             1000
CBAP_MIGRATION_ENABLE         1
CBAP_MIGRATION_TRACE          0
CBAP_ETA_FEASIBILITY_TRACE    1         (audit only; no control effect)
```

Compiled defaults not overridden by any scenario (`rdma-hw.h:260-266`):

```
migrationReleaseRatio  0.5    <- eta_base
migrationDecayBase     0.30   <- f_dec
migrationRiseBase      0.30   <- f_inc
migrationRiseSkew      0.35
migrationMaxRtt        5
budgetQLowFraction     0.5
budgetQHighFraction    1.0
maxDrainRatio          0.20
oldBatchWeight         1.0
newBatchWeight         1.0
```

Per-link capacity and tolerance band, from `s*_cbap_link.txt`
(`link_id node if rate qmax ...`):

```
0 84 1 10000000000 400000 0 1
        C = 10 Gbps      Qmax = 400 000 B  (migration tolerance band)
```

S6 declares two such links (`84:1` and `83:1`).

## 6. eta_base and eta_feasible

`eta` is the fraction of its aggregate rate the **old** (background) side
releases to an arriving batch. The allocation, per link, is
(`rdma-hw.cc:1866-1918`):

```
oldShare  = floor((1 - eta_eff) * R_old)
newShare  = max(C - oldShare, 0)
perFlow   = max(newShare / N, R_min)      <- the hard floor, rdma-hw.cc:1915
```

Because the floor is hard, whenever `newShare / N < R_min` the floor lifts all N
flows and the target sum becomes `(1-eta)*R_old + N*R_min > C` — infeasible before
a single packet is sent, with the excess going only into the queue. Solving
`N*R_min <= C - (1-eta)*R_old` for eta gives the smallest feasible release ratio:

```
    eta_feasible = ( N * R_min  -  ( C - R_old ) ) / R_old

    eta_eff      = max( eta_base , eta_feasible )        , clamped to <= 1
```

* `eta_base` = **0.5** (compiled default, never overridden in the matrix).
* `N` = number of **new-batch flows on that specific link** (not the global
  count) — the shares are computed per link, so a multi-bottleneck scenario uses
  its own fan-in. Verified in S6: the trace shows `N = 30` on two separate rows.
* `R_old` = the **runtime aggregate** of the old side (`qp->m_rate` summed,
  `rdma-hw.cc:1841`), not a configured cap. `eta_feasible` is therefore a dynamic
  quantity that changes as flows finish.
* `R_min` = `MIN_RATE` = **100 Mb/s**.
* `C` = link capacity = 10 Gbps.

This is a **feasibility floor, never an FCT optimisation**: where the configured
eta already satisfies capacity, `max()` leaves it untouched.

Measured `eta_feasible` at the handover of each scenario, matching the closed
form to six decimals:

| scenario | N per link | R_old | eta_feasible | eta_eff | raised? |
|---|---|---|---|---|---|
| S1 | 16 | 8.0 G | −0.050000 | 0.500000 | no |
| S6 | 30 (× 2 links) | 8.0 G | +0.125000 | 0.500000 | no |
| S2 | 64 | 8.0 G | +0.550000 | 0.550000 | **yes** |
| S3 | 64 | 8.0 G | +0.550000 | 0.550000 | **yes** |
| S5 | 64 | 8.0 G | +0.550000 | 0.550000 | **yes** |
| S4 | 64 | 9.5 G | +0.621053 | 0.621053 | **yes** |

Check: S3 `(64×0.1 − (10 − 8)) / 8 = 4.4/8 = 0.550`;
S4 `(6.4 − 0.5) / 9.5 = 0.62105`.

Across every replan in all six scenarios: `eta_eff == max(eta_base,
eta_feasible)` with **0 violations**, and `final_sum_target <= link_capacity`
with **0 violations**.

## 7. MIN_RATE and its scale implication

`MIN_RATE = 100 Mb/s`, unchanged throughout. At 64 flows the floor alone
demands 64 × 100 Mb/s = **6.4 Gbps** of a 10 Gbps link. The feasibility
constraint prevents that from causing target-sum overshoot, but the floor itself
remains a scale limit: per-flow delivered rate converges to ~95 Mbps in S2–S5.
At 16 flows (S1) the floor is 1.6 Gbps and at 30 per link (S6) 3.0 Gbps, both
comfortably inside available headroom — which is why the constraint is inert
there.

## 8. Seed and determinism

`SIM_SEED = 2` for every cell. **Seed 1 is unusable**: `third.cc:3441` reserves it
for diagnostics and requires a bounded CBAP packet trace the scenario configs do
not set, so seed 1 fails every cell with `CONFIG_ERROR`.

The simulation consumes **no random variates on any reachable path**:

* The only `RandomVariableStream` is `RateErrorModel`'s uniform variable, inert
  because every link has error rate 0 (`ERROR_RATE_PER_LINK 0`).
* Every `rand()` in `point-to-point/model` is commented out, inside a string
  literal, or gated on `cc_mode == 10` (HPCC-PINT, not used).
* Routing is deterministic twice over: `CBAP_PATH_FILE` pins every data flow via
  the fixed-path table, and the ECMP fallback is a MurmurHash seeded from the
  **node ID**, not from `SIM_SEED`.
* Traffic is static file replay with literal sizes and start times.

Confirmed empirically three ways:

1. Five seeds of S1 produced **bit-identical** results (mean FCT 17.398941 ms in
   all five).
2. S1/DCQCN under the frozen build reproduces **17.399 ms**, the pre-freeze value.
3. The S3 and S4 CBAP-SBA cells run **solo** and **in a 2-way parallel pair** gave
   results identical to 6 decimals, with `eta_feasibility.csv` byte-identical.

Consequently **one run per cell and no confidence intervals** — a zero-width
interval from a single deterministic observation would misrepresent it.

## 9. Frozen build identity

```
git commit          2ece98e378c69a6d38884dd1c1a74d007618ae9c
git branch          exp/bop-clos-final-20260728_235414
third               0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35
p2p shared library  0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72
                    (libns3.18-point-to-point-debug.so)
topology.txt        6091d5ec28c391c0c8ec79dcaf035d7deb44c2dd57e4c357dffe6bafe8c4fff8
toolchain           g++-7 7.5.0, python2.7.18 (container ubuntu:20.04)
compile flags       -O0 -ggdb -g3 -std=gnu++11 -fstrict-aliasing -Wstrict-aliasing
```

**Both binaries must be recorded.** `third` is a thin launcher that *dynamically*
links `libns3.18-point-to-point-debug.so`, and the CBAP-SBA logic lives in that
library — so hashing `third` alone cannot detect an algorithm change. All 30
manifests carry `binary_sha256` **and** `p2p_lib_sha256`; verified 30/30, together
with `git_commit` 30/30.

Per-scenario input hashes are in `manifests/matrix_baseline.manifest`; per-cell
`config_sha256`, `flow_file_sha256`, `topology_sha256`, `cbap_link_sha256`,
`cbap_path_sha256` and `round_schedule_sha256` are in each cell manifest.

## 10. Reproduction

```bash
git checkout 2ece98e
cd simulation
CC=gcc-7 CXX=g++-7 python2 waf configure && CC=gcc-7 CXX=g++-7 python2 waf build
# verify the build identity before trusting any result:
sha256sum build/scratch/third build/libns3.18-point-to-point-debug.so
bash experiment/scheme1_sba/run_matrix.sh s1 2.1 2      # one scenario at a time
cd experiment/scheme1_sba && python3 metrics.py s1 2
```

The runner refuses to start if either binary hash differs from
`matrix_baseline.manifest`. Free environment check: S1/DCQCN must yield a mean
incast FCT of **17.399 ms**.

Wall time on the measured host (2 vCPU, 2-way parallel): whole matrix ≈ 3 h 20 m;
S4 cells 698–779 s, S5 cells 594–799 s. Serial is ≈ 1.25× slower.
