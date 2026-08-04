# Metrics and validity rules

`collect_run_metrics.py` derives the declared run-level summaries from
flow-round, group-round, selected bottleneck, PFC, controller and wire records.
It never substitutes zero for a failed or missing run. Fields unavailable from
the current simulator counter path (for example packet drops, retransmissions,
and exact aggregate control bytes) are emitted as `NA`, not fabricated.

Group RCT is replayed as the last collective ACK completion minus common
release. Active utilization uses the sum of group-RCT windows, excluding
compute gaps. Completion skew, barrier-minus-percentile tails, and Jain
fairness are computed per group-round and then averaged; Jain fairness uses
inverse per-flow round completion time. The physical payload lower bound is
`8*group_payload/100 Gbit/s` for the single shared bottleneck. The checker
rejects incomplete flows, ACK-byte mismatches, incorrect
flow/group counts, barrier overlap, NaN/Inf, nonzero exit, truncation, input or
framework hash drift, and frozen source-hash drift.

BOP/BOP-QB validation additionally checks:

- one decision per group-round;
- aggregate base rate does not exceed 100 Gbit/s;
- `T_star` and capacity projection fields are finite;
- QB group credit replays
  `min(max(Q_target-q0-packet_margin,0),group_bytes)`;
- per-flow credit sums exactly to group credit;
- safety bounds are true.

Wire fairness compares application bytes, DATA packet count and mean/min/max
wire DATA bytes between Wire-Equalized DCQCN and BOP-QB. Padding is statically
restricted to the forward DATA construction path; ACK/CNP are unpadded.

`completed.flag` is created only after metric collection and validation pass.
Invalid/timeout runs retain raw files and are excluded by the parser.
