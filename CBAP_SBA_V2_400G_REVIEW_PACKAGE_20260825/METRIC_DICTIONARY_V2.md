# METRIC_DICTIONARY_V2 — exact definitions

Time base: ns-3 integer nanoseconds (`Simulator::Now().GetTimeStep()`).
Packet geometry: payload 952B, wire 1000B (48B headers); wire/payload
ratio exactly 1000/952. Rates in the config and in `*_bps` fields are
WIRE bits/s unless suffixed otherwise.

## Per-flow timestamps (`flow_timing.csv`, one row per flow)

| column | meaning |
|---|---|
| `app_start_ns` | application flow start (flow file column) |
| `application_ready_ns` | instant the round group is declared ready; for CBAP this is when admission planning begins; equals the schedule release timestamp semantics used by baselines (v1-frozen convention: baselines' release ≡ CBAP's ready) |
| `network_release_ns` | first instant the flow may inject (CBAP: ready+plan, 5µs admission latency charged to CBAP) |
| `first_data_tx_ns` | first data packet handed to the NIC |
| `last_ack_ns` | last ACK received (flow completion) |
| `total_size_bytes` | payload bytes of the flow |
| `acked_bytes` | payload bytes acknowledged by stop time |

## Derived metrics (`matrix_analyze.py` → `final_results_v2.csv`)

| column | formula | unit |
|---|---|---|
| CCT (per flow) | `last_ack_ns − application_ready_ns` (fallback ref `network_release_ns` if ready absent — never needed in v2) | ms in CSV |
| `mean_cct_ms` / `p99_cct_ms` | mean / index `round((n−1)·0.99)` of sorted per-flow CCTs over the incast batch (bg excluded via flow_id 0 and size filter) | ms |
| batch (round) completion | max `last_ack_ns` over the batch − ready; equals the p99≈max here (64 flows) | ms |
| `ideal_ms` | `fanin × size × 8 × (1000/952) / C` — line-rate drain bound of the batch, no RTT/overhead terms | ms |
| `p99_over_ideal` | `p99_cct_ms / ideal_ms` | — |
| `qpeak_mb` | max `queue_bytes` over `selected_link_timeseries.csv` (bottleneck egress, ~10µs sampling) | MiB |
| `qdelay_us` | `qpeak_bytes × 8 / C × 1e6` (wire drain time of the peak) | µs |
| fabric queue | `qlen_ts.csv`: `total_queue_bytes` = Σ egress bytes over ALL switch ports, 2µs sampling; `max_port_queue_bytes` companion | B |
| `pfc` | row count of `pfc_events.csv` (each row = one pause(1)/resume(0) frame at node/if/queue) | events |
| PFC pause duration | Σ `pfc_pause_ns_delta` over `selected_link_timeseries.csv`, or pair pause→resume events per port from `pfc_events.csv` | ns |
| `retx` | Σ `retx_events` over `flow_summary.csv` | events |
| ECN | Σ `ecn_marks_delta` over `selected_link_timeseries.csv` | marks |
| utilization / throughput | `utilization`, `tx_bytes_delta` columns of `selected_link_timeseries.csv` (per sample interval) | —, B |
| `bg_tail_gbps` | payload goodput of flow 0 over the last two samples of `selected_flow_timeseries.csv`: `Δsnd_una × 8 / Δt` | Gb/s payload |
| `bg_total_gb` | final `snd_una` of flow 0 | GB payload |
| background deficit | cap − measured bg rate over any window; cap = `APP_RATE_CAP_BPS` (wire) × 952/1000 in payload terms | Gb/s |
| goodput (per flow) | `acked_bytes × 8 / (last_ack_ns − network_release_ns)` (BCT window); FCT-window variant uses `first_data_tx_ns` | b/s payload |

## Cross-algorithm comparability (v1-frozen conventions)

CCT reference = `application_ready_ns` for every arm; baselines have
ready ≡ release, CBAP pays its planning latency inside CCT. FCT
(`flow_summary.fct`) is NOT cross-algorithm comparable (different start
conventions) and is not used in any v2 claim.

## Gate definitions (`gates` column)

incomplete (n≠fanin) | retx≠0 | CBAP `qdelay_us` > D_abs(rate)
{826,105,84}µs | bg tail unmeasured. PASS = none of these. Gate
violations are reported verbatim (5 documented 10G CBAP transients,
`matrix_report_v2.md` §3); no bound was adjusted post hoc.
