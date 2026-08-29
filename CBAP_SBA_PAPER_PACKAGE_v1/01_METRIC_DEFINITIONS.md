# Metric definitions (FROZEN)

```
CCT            = last_ack - application_ready        (batch completion, the
                                                      cross-algorithm metric)
BCT            = last_ack - network_release
FCT_i          = last_ack_i - first_data_tx_i        (per flow)
injection_span = injection_end - first_data_tx
```

## Timestamp sources (exact file/column, per algorithm class)

| timestamp | CBAP-SBA (CC_MODE 30) | baselines (CC_MODE 1/3/7/8) |
|---|---|---|
| application_ready | flow_timing.csv:application_ready_ns (from admission stage; = 2.000000000 s in S1-S6) | not produced (no admission stage): flow_timing.csv:application_ready_ns = 0; CCT reference falls back to network_release |
| network_release | flow_timing.csv:network_release_ns (= ready + 5 us admission delay) | flow_timing.csv:network_release_ns (round release = 2.000000000 s) |
| first_data_tx | flow_timing.csv:first_data_tx_ns (stamped in PktSent for EVERY cc_mode) | same |
| last_ack | flow_timing.csv:last_ack_ns (flow completion handler) | same |
| injection_end | round_summary.csv:injection_end_time (seconds) | same |

Key comparability fact: the baselines' network_release and CBAP's
application_ready are the SAME instant (2.000000000 s), so CCT is
cross-algorithm comparable; CBAP's CCT-BCT = 5.0 us admission delay is
charged to CBAP.  flow_summary.csv:fct is NOT usable across algorithms (its
start_time is application_ready for CBAP but qp->startTime for baselines)
and is not used anywhere in this package.

Background-flow metrics: goodput over [flow_start, sim_stop] from
flow_summary.csv:acked_bytes; retention = ratio vs same-scenario DCQCN;
recovery = first time after last_ack where the background flow's commanded
rate (selected_flow_timeseries.csv:current_rate) >= 95% of its pre-batch
mean ([ready-50ms, ready)).

Cross-check of the three completion timestamps: 02_TIMESTAMP_CROSSCHECK.csv
(per matrix cell: last_ack vs injection_end ordering, ready/release deltas).
