# S3 MISSING METRICS

38 metric rows are UNAVAILABLE/MISSING.  None is substituted, zeroed or replaced by a proxy.

| metric_id | arm | why unavailable |
|---|---|---|
| `C.arrival.wire.mean` | DCQCN | port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never writes arrival_rate_bps. Needs a CC-agnostic port sampler. |
| `C.service_rate.mean` | DCQCN | port_summary.csv absent for DCQCN; served rate for DCQCN is DERIVED from tx_bytes_delta instead (see C.served.wire.*) |
| `C.arrival.wire.p50` | DCQCN | port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never writes arrival_rate_bps. Needs a CC-agnostic port sampler. |
| `C.service_rate.p50` | DCQCN | port_summary.csv absent for DCQCN; served rate for DCQCN is DERIVED from tx_bytes_delta instead (see C.served.wire.*) |
| `C.arrival.wire.p95` | DCQCN | port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never writes arrival_rate_bps. Needs a CC-agnostic port sampler. |
| `C.service_rate.p95` | DCQCN | port_summary.csv absent for DCQCN; served rate for DCQCN is DERIVED from tx_bytes_delta instead (see C.served.wire.*) |
| `C.arrival.wire.p99` | DCQCN | port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never writes arrival_rate_bps. Needs a CC-agnostic port sampler. |
| `C.service_rate.p99` | DCQCN | port_summary.csv absent for DCQCN; served rate for DCQCN is DERIVED from tx_bytes_delta instead (see C.served.wire.*) |
| `C.arrival.wire.max` | DCQCN | port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never writes arrival_rate_bps. Needs a CC-agnostic port sampler. |
| `C.service_rate.max` | DCQCN | port_summary.csv absent for DCQCN; served rate for DCQCN is DERIVED from tx_bytes_delta instead (see C.served.wire.*) |
| `E.zone.fraction` | DCQCN | DCQCN has no CBAP queue controller; qc_trace.csv is a header-only 447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and must not be reported as 0. |
| `E.boost.mean` | DCQCN | DCQCN has no CBAP queue controller; qc_trace.csv is a header-only 447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and must not be reported as 0. |
| `E.drain.mean` | DCQCN | DCQCN has no CBAP queue controller; qc_trace.csv is a header-only 447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and must not be reported as 0. |
| `E.pending.frac_nonzero` | DCQCN | DCQCN has no CBAP queue controller; qc_trace.csv is a header-only 447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and must not be reported as 0. |
| `E.sumR.mean` | DCQCN | DCQCN has no CBAP queue controller; qc_trace.csv is a header-only 447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and must not be reported as 0. |
| `E.migration.events` | DCQCN | DCQCN has no capacity migration mechanism by construction |
| `G.cnp.count` | CBAP | No per-flow CNP counter is emitted in these outputs; feedback_summary.csv aggregates without a CNP column. |
| `G.cnp.count` | DCQCN | No per-flow CNP counter is emitted in these outputs; feedback_summary.csv aggregates without a CNP column. |

## Minimum instrumentation needed (NOT implemented this round)

1. **DCQCN arrival / service rate, queue gradient, port state** - `port_summary.csv` is written only on the CBAP telemetry path.  Needs a CC-agnostic egress-port sampler emitting the same columns regardless of CC_MODE.  Re-run: `ckpt4_dcqcn_s3` (~17 min, ~50 MB).

2. **Per-flow CNP counts** - no CNP column exists in any output.  Needs a per-QP CNP counter surfaced into flow_summary.csv.  Re-run: both S3 cells (~35 min).

3. **H_obs / H_sender / H_path / H_eff actuation latency** - needs commanded -> sender-effective -> bottleneck-arrival timestamps per QP.  actuation.csv exists for CBAP only, so no cross-arm comparison is possible.

4. **DCQCN controller zones / boost / drain / pending** - do not exist for DCQCN by construction.  Reported MISSING rather than 0, because 0 would falsely imply "measured and found zero".
