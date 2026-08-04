# RS-HPCC output schema

Every run keeps `run_meta.json`, `flow_summary.csv`, `round_summary.csv`,
`feedback_summary.csv`, `controller_summary.csv`,
`rs_round_decisions.csv`, selected low-frequency flow/link series,
`pfc_events.csv`, and bounded `run.log`.

`run_meta.json` identifies mode 13 results with
`algorithm_name=rs_hpcc`, `algorithm_version=rs_hpcc_v1`, and
`old_ra_hpcc_disabled=true`. It includes the complete generated config and
round-plan SHA256.

`round_summary.csv` retains release, injection, cumulative-ACK completion,
RCT, sequence interval, and rate fields. It adds `round_group_id`,
`participant_count`, and DCQCN's per-round CNP count, start/end alpha, and
start/end recovery stage.

`feedback_summary.csv` remains one row per QP/round. It contains INT hop
evidence, actionable/late/stale counts, OFF-stage rate changes, remaining
unsent ratios, same-hop load/queue diagnostics, and live-rate before/after
evidence. Removed empirical suggested-rate fields are absent.

`rs_round_decisions.csv` is one row per QP/round:

```text
scenario, algorithm, seed, flow_id, qp_id, round_id, round_group_id,
participant_count, round_bytes, release_time, rs_applied, estimator_valid,
estimator_origin_round, feedback_delay_ewma_us, feedback_delay_source,
queue_last_bytes, queue_sample_time, queue_age_us,
residual_queue_estimate_bytes, bottleneck_capacity_bps,
background_load_bps, ecn_threshold_bytes, pfc_threshold_bytes,
queue_safe_bytes, rate_before_release_bps, rate_min_bps, rate_max_bps,
selected_rate_bps, predicted_queue_bytes, constraint_active,
constraint_infeasible_at_min, fallback_reason, bisection_iterations
```

Times named `release_time` and `queue_sample_time` are seconds;
`queue_age_us` and `feedback_delay_ewma_us` are microseconds. The latter
contains the delay actually used by the solver; `feedback_delay_source`
distinguishes EWMA, base RTT, and configured default.

Round zero has `rs_applied=0` and
`fallback_reason=first_round_baseline`. Non-RS algorithms use
`fallback_reason=not_rs_hpcc`.

`controller_summary.csv` adds `rs_init_update_count`,
`rs_fallback_count`, `rs_infeasible_count`, mean selected/predicted/residual
values, and `rs_constraint_active_count`. Removed carry counters are absent.
