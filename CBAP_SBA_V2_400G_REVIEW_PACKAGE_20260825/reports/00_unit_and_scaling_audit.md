# v2_400g — Unit & scaling audit (pre-change, code state 0c090e4)

Scope: every rate-dependent quantity on the control and measurement paths,
audited for 200/400G semantics. Columns: current unit / 10G value /
derivation at 200/400G / scale-or-absolute / change decision.

## A. CBAP controller (QueueControllerEpoch, rdma-hw.cc:668-1010)

| parameter | file:site | unit | 10G value | 200/400G derivation | scale? | decision |
|---|---|---|---|---|---|---|
| C (capacityBps) | cbap_link file col4 -> runtime.config.capacityBps | bps WIRE | 10e9 | topology+link file value | scales | new link files per rate |
| Q_abs | derived: qcAppHardDelayS x C/8 | bytes (from a DELAY config) | 838.86us -> 1,048,575 B | v2 rule: Q_abs = min(C x D_abs/8, 0.25 x BUFFER); D_abs in {40,80,160}us | delay-parameterised | CHANGE: config becomes CBAP_QC_APP_HARD_DELAY_US = D_abs; the old "one message" binding is dropped per instruction |
| Q_low | 0.5 x Q_abs (qcSoftFraction) | fraction | 524,287 B | same fraction | auto | keep fraction 0.5 |
| Q_red | Q_abs - M_safe | bytes | 981,503 B | same formula | auto | keep |
| Q_high | Q_red - MAX_BOOST x H/8 | bytes | 915,877 B | same formula (H = measured H_eff) | auto | keep |
| M_safe | qcSafetyMarginBytes | bytes | 67,072 (= 64 pkts x 1048) | = FANIN x 1048 (packetization) | bytes, fan-in-scaled | keep formula; recompute if FANIN changes |
| H_eff (qcHGuardS) | config CBAP_QC_H_GUARD_US | us ABSOLUTE (measured) | 175 | MUST BE RE-MEASURED per rate (section 四); serialization component shrinks ~C-fold, propagation (2x1us/hop) does not | measured | re-measure; forbidden to divide or inherit |
| control epoch | CBAP_CONTROL_EPOCH_US (exists, default 5) | us | 5 | sweep {1,2,5}; at 400G 5us = 250 KB line-time | config sweep | config-only, no code change |
| BMAX | CBAP_QB2_BMAX_RATIO x C | ratio | 0.04C | ratio, screening {0.02,0.04,0.06} | auto | re-screen (b040 does NOT carry over) |
| Q_target | CBAP_QB2_QTARGET_RATIO x Q_abs | ratio of Q_abs | 26,214 B | v2 rule: Q_target = C x D_target/8, D_target in {8,16,32}us -> expressed as ratio = D_target/D_abs | delay-parameterised | generator computes the ratio |
| deadband | 1048 x 8 / H_eff | bps | ~48 Mbps | scales with 1/H_eff | auto | keep formula |
| MIN_RATE | config MIN_RATE | payload bps | 100 Mb/s (=1% C) | v2 rule: 0.01 x C -> 2G/4G payload at 200/400G | rate-scaled | generator sets it |
| drainMax | C - floorWire | bps | auto | auto | auto | keep |

## B. Admission / migration (cbap-sba.cc, EvaluateCbapSbaMigration)

| parameter | site | unit | 10G value | 200/400G | decision |
|---|---|---|---|---|---|
| availableCapacity | GetCbapSbaAvailableCapacity (rdma-hw.cc:2918) | **PAYLOAD** bps when telemetry initialized (latest.effectiveCapacityBps), WIRE when not | 9,541,984,732 measured | domain mixing vs wire-domain appliedRateBps | **CONFIRMED still present (~4.6% startup transient)**; v2-only fix: flag SBA_WIRE_DOMAIN_PLANNING converts effective to wire (PayloadRateToLinkRate); default 0 = v1 byte-identical; unit test added |
| appliedRateBps (old side) | cbap-sba ledger, fed from qp->m_rate | WIRE bps | - | unchanged | consistent once fix on |
| initial_release_ratio | CBAP_INITIAL_RELEASE_RATIO | ratio | 0.90 | dimensionless | keep 0.90 per instruction |
| migration decay/rise | config | ratio per step | 0.30/0.30 | dimensionless, but step CADENCE is epoch-driven -> absolute-time convergence shrinks with epoch | keep; record in metadata |
| migration_max_rtt | CBAP_MIGRATION_MAX_RTT | us? absolute | (config) | RTT roughly unchanged (prop-dominated) | keep, record |
| wire/payload ratio | PayloadRateToLinkRate: x1048/1000 | bytes | 1048/1000 | packet size unchanged (PACKET_PAYLOAD_SIZE 1000 + 48 hdr) | keep |

## C. QP / host / topology

| item | site | unit | 10G | 200/400G | decision |
|---|---|---|---|---|---|
| QP initial rate | rdma-hw.cc:6230 qp->m_rate = m_bps (NIC line rate) | WIRE bps | 10G | scales with topology automatically | topology change only |
| topology link rate | topology.txt col3 ("10Gbps") | string | 10Gbps | "200Gbps"/"400Gbps" all links (hosts + core) | generator emits per-rate topology |
| link delay | topology.txt col4 | 1us absolute | 1us | propagation: keep absolute -> RTT stays ~8us (preflight verifies) | keep |
| bg rate | APP_RATE_CAP_BPS | bps | 8e9 (0.8C) | BG_LOAD_FRAC x C | generator |
| HPCC window | maxBdp from topology (third.cc:4925+) | bytes | 19,000 | recomputed from rate x RTT automatically | auto; record printed maxRtt/maxBdp |

## D. Baselines

| parameter | unit | 10G stock | 400G stock | 400G speed_normalized | rationale |
|---|---|---|---|---|---|
| DCQCN RATE_AI / HAI | bps abs | 50M / 100M | unchanged | **2G / 4G** | recovery slope must scale with C or recovery time inflates 40x |
| DCTCP_RATE_AI | bps abs | 1000M | unchanged | **40G** | same |
| TIMELY RATE_AI | bps abs | 50M | unchanged | **2G** | same |
| HPCC eta / MI / INT | dimensionless | 0.95 / 5 | unchanged | unchanged | dimensionless per instruction |
| DCQCN timers (alpha_resume 55us, rate_decrease 4?, RP_TIMER 300us) | us ABSOLUTE | 55/4/300 | unchanged (recorded in metadata) | unchanged (recorded) | per instruction: absolute for now, metadata-logged |
| TIMELY TLow/THigh/minRtt | ns ABSOLUTE (attributes, not config keys) | 50us/500us/20us | unchanged | unchanged | RTT is prop-dominated and roughly rate-invariant, so RTT-threshold semantics survive; NOT config-exposed (harness limitation, recorded); NOTE: THigh 500us >> queue delays at 400G/64MB -> TIMELY may be near-inert at 400G; report as finding, do not tune |
| ECN KMIN/KMAX/PMAX | bytes (rate-indexed map) | 400KB/1600KB/0.2 @10G row | same KB values, NEW map row for 200/400G rate | same (per instruction, only rate-type params normalized) | reported also as BDP multiples and delay: 400KB = 38xBDP / 320us @10G; = 0.95xBDP / 8us @400G (BDP~420KB) |
| PFC PAUSE_TIME | us ABSOLUTE (QbbNetDevice::PauseTime, third.cc:4369) | 5us | unchanged | unchanged | one pause = 5us of line-time regardless of rate (250KB @400G vs 6.25KB @10G); semantics acceptable (pauses re-issued while above threshold) but pause GRANULARITY coarsens 40x -> recorded; PFC dynamic threshold scales with BUFFER_MB |
| BUFFER_SIZE | MB abs | 8 | {8,32,64} sweep | same | 8MB = 6.4ms @10G but 160us @400G; 64MB @400G = 1.28ms (close to real TH4-class per-port share) |

## E. Measurement / analysis paths

| item | site | issue at high rate | decision |
|---|---|---|---|
| queue->delay conversion | analysis scripts hardcode C=10e9 (d_metrics*, matrix_metrics, pkg2) | WRONG at 200/400G | v2 analyzers read C from config; never reuse v1 scripts unmodified |
| link timeseries sampling | ~10us interval | 1 RTT = ~8.4us -> queue_at_1RTT under-resolved | preflight reports first-100us window peak + plateau; note granularity; if a finer knob exists it is used (checked in preflight) |
| CBAP planning time in CCT | application_ready at plan instant; release=ready+5us | plan cost included since CCT ref = ready | already satisfied; 5us admission delay stays charged to CBAP |
| actuation 4-stage audit | CBAP_ACTUATION_FILE (decision->dispatch->sender->bottleneck) | reused as the H_eff measurement instrument | section 四 uses it per rate |

## F. Known-open items carried into v2

1. ~4.6% wire/payload startup transient: fix implemented behind
   SBA_WIRE_DOMAIN_PLANNING (v2 configs only; default 0 keeps v1 bytes).
2. Admission does not bound infeasible-overlap duration (v1 envelope
   T ~ (Q_red-Q_std)x8/(SumFloor-C)); at 400G the envelope shrinks ~C-fold
   in time -- re-derive after H_eff measurement.
3. MIN_RATE_FRAC=0.01 x C keeps the fan-in feasibility envelope at ~1/0.0105
   ~ 95 controlled flows independent of rate (floors scale with C).
