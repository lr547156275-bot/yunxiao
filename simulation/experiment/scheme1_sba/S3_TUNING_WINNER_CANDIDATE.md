# S3_TUNING_WINNER_CANDIDATE — scr7_b040 (BMAX = 0.04C)

Status: **CANDIDATE ONLY**, single seed, S3 only.  NOT a final
parameter.  b040 must not be re-tuned on S3 and then presented
against S4/S5 as an independent validation.

**REVALIDATION REQUIRED**: the b080 audit found a shared
correctness defect (LEDGER_GHOST_ARRIVAL, see B080_ROOT_CAUSE.md)
that biases the boost law input in ALL v2 cells including b040.
The scr7 numbers below are the PRE-FIX record; the scr8 rerun
supersedes them once complete.

## Pre-fix screening record (scr7, S3, seed=2)

| metric | D1 | D3 | b040 |
|---|---|---|---|
| CCT (ms) | 58.3730 | 58.4911 | 56.8572 |
| batch goodput (G) | 9.1972 | 9.1787 | 9.4425 |
| queue p99 / max (B) | 967,304 / 1,279,608 | 1,048 / 9,432 | 6,288 / 26,200 |
| bg full /D1 | 1.0000 | 0.9984 | 0.9992 |
| PFC / drop / retx | 0/0/0 | 0/0/0 | 0/0/0 |

Note: BCT improvement and batch-goodput improvement are the same
effect expressed twice (fixed batch bytes), not two independent
contributions.

## Frozen configuration

```
#MANIFEST,link_id=0,steady_cap_fraction=1.000000,rho=0.900000,bmax_ratio=0.040000,bmax_wire_bps=400000000,qtarget_ratio=0.025000,qtarget_bytes=26214,q_low=524287,q_high=915877,q_red=981502,q_abs=1048574,h_eff_us=175.000,queue_band_v2=1,queue_band_v1=0,migration=1,steady_cap=1,seed=2
```

| key | scr7_b040 value |
|---|---|
| CC_MODE | 30 |
| CBAP_ENABLE | 1 |
| CBAP_RHO | 0.90 |
| CBAP_STEADY_CAP_ENABLE | 1 |
| CBAP_STEADY_CAP_FRACTION | 1.000 |
| CBAP_MIGRATION_ENABLE | 1 |
| CBAP_QUEUE_BAND_ENABLE | 0 |
| CBAP_QUEUE_BAND_V2_ENABLE | 1 |
| CBAP_QB2_BMAX_RATIO | 0.040 |
| CBAP_QB2_QTARGET_RATIO | 0.025 |
| CBAP_QC_SOFT_FRACTION | 0.5 |
| CBAP_QC_MAX_BOOST_RATIO | 0.30 |
| CBAP_QC_H_GUARD_US | 175 |
| CBAP_QC_APP_HARD_DELAY_US | 838.86 |
| CBAP_QC_SAFETY_MARGIN_BYTES | 67072 |
| MIN_RATE | 100Mb/s |
| SIM_SEED | 2 |
| SCENARIO | s3_fan64_1m_bg80 |
| SIMULATOR_STOP_TIME | 3.0 |
| APP_RATE_CAP_BPS | 8000000000 |
| FLOW_FILE | s3_flow.txt |
| TOPOLOGY_FILE | topology.txt |

## SHA-256 manifest (state at registration, ledger fix applied, pre-rebuild)

git HEAD a745d58dec82ffa445155557147b0bba42d0dee6 (dirty files: 701, deliberate: unpushed round work)

| artefact | sha256 |
|---|---|
| binary third | 5b5920f859fa86a269b5de4d9a7479226e27b03ecfc63c8356b100edb116c7e1 |
| libns3 p2p | ABSENT |
| rdma-hw.cc (post-ledger-fix) | a8107a973fdad1dc262029b259e3eed80f368175e03a418f0445ea96a4cb5e1c |
| rdma-hw.h | 87d052b7e65dff473025b5eec1ccf6a6bee06bf53fc5cf3cf5682af10b1d4dbe |
| third.cc | d866cf86cd6df6b239cb83c2403f95f06cad5857502eec64b495789da94bae58 |
| checker d_metrics3.py | ebffdc74e95dd345987aa2ca229e046f423966f340baac1e60d6ed82d1f01408 |
| config scr7_d1.txt | 153f5137a4bd160002c3b929c9035d5ecf604cc67ae461bd98fbb8c45c502cb9 |
| config scr7_d3.txt | cbd5d3e6fc147a80e867983a8f6a9e3a95a92ece41279c11ff59bf50b69b7959 |
| config scr7_b040.txt | ede9fb59b33b436615ceda68c018e14f202559baaf73b3d02e29fd40d8afaa4e |
| topology | 6091d5ec28c391c0c8ec79dcaf035d7deb44c2dd57e4c357dffe6bafe8c4fff8 |
| flow file | 6b922c67e56c04aa32f67078c89bd8a0a0fafceae58f078bfa272cc8223ada0b |
| round schedule | 8a40b3d13abe225d745360e5db26ccf71253837486b43a14423d65e9827200bb |

## scr8 post-fix record (SUPERSEDES the scr7 table above)

Ledger fix verified: 16/16 D1/D3 result files byte-identical to scr7; ghost
eliminated (b080 LAW_ZERO 11,615 -> 161 epochs; pending_excess no longer a
constant).  Post-fix landscape:

| arm | CCT (ms) | vs D1 | batch goodput (G) | queue p99/max (B) | gates |
|---|---|---|---|---|---|
| scr8_d1 | 58.3730 | - | 9.1972 | 967,304 / 1,279,608 | FAIL (qmax>Q_abs, baseline) |
| scr8_d3 | 58.4911 | TIE (+0.20%) | 9.1787 | 1,048 / 9,432 | PASS |
| scr8_b005 | 58.2011 | TIE (-0.29%) | 9.2244 | 1,048 / 11,528 | PASS |
| scr8_b010 | 58.2367 | TIE (-0.23%) | 9.2188 | 1,048 / 13,624 | PASS |
| scr8_b020 | 58.2217 | TIE (-0.26%) | 9.2212 | 1,048 / 15,720 | PASS |
| **scr8_b040** | **56.8412** | **-2.62%** | **9.4451** | 19,912 / 26,200 | PASS |
| scr8_b080 | 58.4757 | TIE (+0.18%) | 9.1811 | 2,096 / 29,344 | PASS |

Honesty notes carried into any later use of this table:
- scr7's apparent b010/b020 gains (-0.78%/-1.75%) were LEDGER_GHOST artifacts
  and DISAPPEAR after the fix; the scr7 v2 columns must not be cited.
- The post-fix landscape is a LONE SPIKE at BMAX=0.04C (all other doses TIE).
  Non-smooth response on one deterministic seed+scenario is an overfit /
  resonance warning; b040 is therefore a CANDIDATE pending S4/S5 hold-out.
- Mechanism hypothesis (unproven, from scr8 audit): b040 sustains a
  17.5-22.3 KB standing queue for the whole batch at applied ~= 10.0 G (full
  cap, no idle gaps); b080 still shows an UNEXPLAINED ~0.28 G applied
  underfill (9.70-9.74 G across all batch thirds) and cannot hold a deposit.
  Open items, not conclusions.

## HELD_OUT_S4_S5_PASS (2026-08-19, single seed per scenario)

Label deliberately NOT "GENERALIZES": that term is reserved for
GENERALIZES_ACROSS_SEEDS after the multi-seed/perturbation stage.  b040 is
hereby FROZEN as the candidate configuration (BMAX=0.04C,
Q_target=0.025*Q_abs); no later held-out result may be used to swap the
winner or retune it.

### Gates, kept separate
- CANDIDATE gates (b040): PASS in S4 and S5 (all incast complete, PFC=0,
  drop=0, retx=0, qmax <= Q_abs, bg full & outside >= 99% of same-scenario D1).
- BASELINE observations (D1/DCQCN, report-only -- never absorbed into any
  aggregate PASS): violates Q_abs in BOTH scenarios: S4 15.90 ms over
  (qmax 1,276,464 B), S5 100.96 ms over (qmax 1,279,608 B).

### S4 (64x1MiB, bg cap 9.5G, stop 5.5 s)
| metric | D1 | D3 | b040 |
|---|---|---|---|
| CCT / BCT (ms) | 59.0692 / 59.0692 | 58.4925 / 58.4875 | 56.8446 / 56.8396 |
| FCT mean/p95/p99 (ms) | 54.33/58.12/58.45 | 58.44/58.45/58.45 | 56.79/56.81/56.81 |
| batch goodput (G) / util | 9.0888 / 0.909 | 9.1785 / 0.918 | 9.4445 / 0.944 |
| bg full / in-win / outside (G) | 7.1111 / 0.2001 / 7.2030 | 7.1111 / 0.1005 / 7.2034 | 7.1111 / 0.1011 / 7.2008 |
| bg recovery (ms) | 24.75 | 0.048 | 0.035 |
| queue mean/p95/p99/max (B) | 10140/0/410,792/1,276,464 | 16/0/0/12,576 | 230/0/17,816/28,296 |
| PFC / drop / retx | 0/0/0 | 0/0/0 | 0/0/0 |
| b040 vs D1 | CCT -3.77%, BCT -3.77%, p99 FCT -2.81% | | |

### S5 (64x4MiB, bg cap 8G, stop 6.0 s)
| metric | D1 | D3 | b040 |
|---|---|---|---|
| CCT / BCT (ms) | 230.3722 / 230.3722 | 233.9551 / 233.9501 | 227.2639 / 227.2589 |
| FCT mean/p95/p99 (ms) | 222.51/228.85/229.36 | 233.90/233.91/233.91 | 227.22/227.24/227.24 |
| batch goodput (G) / util | 9.3218 / 0.932 | 9.1790 / 0.918 | 9.4493 / 0.945 |
| bg full / in-win / outside (G) | 6.4000 / 0.1809 / 6.7004 | 6.4000 / 0.0965 / 6.7094 | 6.4000 / 0.0969 / 6.7001 |
| bg recovery (ms) | 20.93 | 0.045 | 0.036 |
| queue mean/p95/p99/max (B) | 38759/0/1,064,768/1,279,608 | 42/0/2,096/9,432 | 1176/0/37,728/48,208 |
| PFC / drop / retx | 0/0/0 | 0/0/0 | 0/0/0 |
| b040 vs D1 | CCT -1.35%, BCT -1.35%, p99 FCT -0.93% | | |

Notes carried forward:
- BCT and batch-goodput improvements are one effect (fixed batch bytes).
- D3 alone is scenario-dependent (-0.98% on S4, +1.56% on S5); the v2 top-up
  is the consistent-gain component.
- b040's controller stayed GREEN throughout both scenarios (HOLD/DRAIN/RED
  residence 0 ms); a dedicated stress cell is required before any claim about
  behaviour in the upper zones.
