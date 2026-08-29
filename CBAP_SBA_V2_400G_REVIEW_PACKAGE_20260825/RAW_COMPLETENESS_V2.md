# RAW_COMPLETENESS_V2 - per-cell recomputability audit

Required raw files/columns per formal cell: application ready / network release / first tx / per-flow & batch last ACK / payload bytes (flow_timing); retx (flow_summary); queue timeseries, utilization/throughput, ECN, PFC count & cumulative pause ns (selected_link_timeseries + pfc_events); fabric queue (qlen_ts); background rate/goodput/recovery (selected_flow_timeseries, flow 0); the exact config.

Cells checked: 120; fully recomputable: 120; deficient: 0


## Known derivations / gaps (by design)

- wire bytes: not logged per packet; exact derivation payload x 1000/952 (fixed geometry).
- batch/round last ACK: max(last_ack_ns) over the batch rows of flow_timing.csv (also mirrored in round_summary.csv where present).
- switch silent drops: no counter in this harness (upstream limitation, documented since v1); retx_events=0 in all 120 cells corroborates zero loss.
