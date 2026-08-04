# Input schema

In addition to the repository's existing topology, flow, trace, fixed-path,
and round files:

- `multilink_links.txt`: count, then
  `link_id node_id if_index capacity_bps ecn_threshold_bytes background_bps
  telemetry_eligible`. Host NIC outputs use `telemetry_eligible=0`; switch
  outputs use `1`.
- `multilink_paths.txt`: count, then
  `flow_id hop_count link_id...` in forward DATA INT-hop order.
- `group_schedule.txt`: count, then
  `group_id predecessor_group_id compute_gap_ns initial_release_ns`.
  The root predecessor is `-1`; all other groups have one predecessor and a
  zero absolute release.
- `collective_schedule.csv`: group, predecessor, iteration, stage, step,
  compute gap, member-QP count, and group payload bytes.

Round rows retain the existing nine fields. `round_group_id` refers to the
global group chain, `participant_count` counts transmitting QPs in that group,
and `jitter_group` is the sender rank.
