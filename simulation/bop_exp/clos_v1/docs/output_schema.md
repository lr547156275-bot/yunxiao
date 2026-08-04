# Output schema

The existing flow, round, group-round, controller, feedback, selected-flow,
selected-link, flow-plan, and PFC files are retained.

`bop_multilink_group_decisions.csv` records one BOP-QB row per global group:
group/round, participants, bytes, alpha, T-star, number of limiting links, and
formula/capacity/credit validity.

`bop_multilink_link_constraints.csv` records one row per link used by a group:
capacity, q0, ECN threshold, flow count, workload, queue room, credit sum,
T-link, limiting-link flag, T-star, and the three validity fields.

Post-run parsing creates:

- `collective_metrics.csv`: per iteration/stage completion metrics;
- `per_link_metrics.csv`: link utilization and queue metrics;
- `run_metrics.csv`: the requested collective, network, queue, and BOP
  aggregate metrics.

PFC, dropped packets, and retransmissions remain `NA` when their semantics are
not validated or their instrumentation is unavailable.
