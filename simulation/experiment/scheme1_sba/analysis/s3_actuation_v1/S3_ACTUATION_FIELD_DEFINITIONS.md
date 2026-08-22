# S3 ACTUATION FIELD DEFINITIONS

Every semantic below is taken from source, not from the column name.

## qc_trace.csv (written by `SampleCbapQcTrace`, scratch/third.cc:1019)

| column | runtime field | what it actually is | sampling point |
|---|---|---|---|
| `q0` | `qc.q0Bytes` | the controller's OWN epoch queue sample, bytes | `sw->GetEgressQueueBytes(ifIndex)` at epoch entry |
| `q_next` | `queueBytes` arg | the NEXT queue read, same call | passed in at the call site; must not be paired with this row's `q_stop` |
| `q_stop` | `qc.qStopBytes` | max-prefix PREDICTED queue over the H_guard horizon, bytes | derived inside the controller, not a measurement |
| `boost_commanded` | `qc.boostCommandedBps` | controller TARGET increment just issued, wire bps | not yet in effect |
| `boost_effective` | `qc.boostEffectiveBps` | controller target increment whose deadline has passed, wire bps | still a TARGET, not a measured rate |
| `drain` | `qc.drainTargetBps` | target decrement, wire bps | target |
| `sumR_effective` | computed in the writer, line 1029: `capacityBps + boost_effective - drain` | a TARGET CEILING derived from LINK CAPACITY, **not** a sum of sender rates and **not** an achieved rate | writer arithmetic |
| `arrival_safe_wire_bps` | `qc.arrivalSafeWireBps` | controller's conservative PREDICTED arrival envelope, wire bps | prediction |
| `sender_effective_wire_bps` | `qc.senderEffectiveWireBps` | sum of per-QP sender pacing rates the controller believes are in force, wire bps | controller's ledger view |
| `pending_generation` | `qc.pendingGeneration` | id of the generation whose command has not yet been confirmed | ledger state |

**Critical correction.** `sumR_effective = 10 Gbps + boost_effective` is a target
ceiling built on the link capacity constant.  Its mean of 12.2573 Gbps does
**not** mean senders were asked to transmit 122 % of line rate, and it is not
comparable to a served rate.  An earlier statement of mine that framed it that
way was imprecise and is withdrawn.

## Served rate (both arms)

`served_wire_rate` is **DERIVED**, not a trace column:
`8 * tx_bytes_delta / dt` from `selected_link_timeseries.csv`, where
`tx_bytes_delta` counts `p->GetSize()` bytes actually transmitted by the
bottleneck egress.  This is the only rate in this audit that is a measured
bottleneck service rate.

## actuation.csv (writer scratch/third.cc:4760, hook rdma-hw.cc:3103)

Three stages, each wired to a real event:

| stage | fired by | meaning |
|---|---|---|
| `rate_command` | `s_cbapActuationHook(flowId, currentRate, appliedRate)` at rdma-hw.cc:3103 | the controller has issued a new pacing rate for this QP |
| `sender_rate_effect` | `RdmaQpDequeue` on the sending device | the first packet actually paced at the new rate leaves the sender |
| `first_affected_at_bottleneck` / `arrival_at_bottleneck` | `QbbEnqueue` / `EgressDequeue` on the bottleneck egress (`cbap_actuation_egress_if`) | that packet reaches / leaves the bottleneck queue |

Columns: `time_ns, generation, flow_id, old_rate_bps, rate_bps, stage,
delta_prev_stage_ns, delta_from_command_ns, seq`.

## pending_age (DERIVED, and NOT an actuation delay)

`pending_age` = epoch_time - first epoch carrying the same
`pending_generation`.  It measures how long a generation id persists in the
ledger.  It is **not** D1, D2 or D3.  My earlier "89.5 us actuation lag" used
this quantity as if it were a stage delay; that inference was unsupported and is
withdrawn.  Measured here: mean 82,564 ns, p95 165,000 ns.

## Input substitution (declared)

The audited pair `ckpt4_cbap_s3_out` has **no** actuation.csv
(`CBAP_ACTUATION_FILE` absent from its config).  Stage timestamps come from
`rec2_s3_on_out`, justified because:
- all 64 per-flow FCT strings are **bitwise identical** between the two;
- algorithm-relevant config is identical (CC_MODE 30, CBAP_ENABLE 1,
  MIGRATION_ENABLE 1, CORE_INITIAL_RELEASE 1, RATIO 0.90, SIM_SEED 2,
  MAX_BOOST 0.30, H_GUARD 175, Q_abs 838.86, M_safe 67072, MIN_RATE 100Mb/s);
- `CBAP_MIG` = 1050 in both.
Queue/zone/boost and served-rate metrics still come from the audited
`ckpt4_*` pair.
