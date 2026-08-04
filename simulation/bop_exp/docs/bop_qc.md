# BOP-QC v1 implementation

`CC_MODE_BOP_QC=14` is a new mode. Modes 1 (DCQCN), 3 (HPCC), 12
(CRFM-Gate), and 13 (BOP-v1) retain their existing rate-control branches.
BOP-QC reuses the single `isBopFamily` calculation in
`RdmaHw::PlanRoundGroup`; there is no second BOP solver.

At the earliest jittered release of each global group, the coordinator reads
only INT state whose ACK arrival time is strictly earlier than the planning
event. The queue is the newest valid bottleneck queue sample. The feedback
delay sample is `ACK arrival time - bottleneck INT sample time`, reconstructed
by the existing HPCC INT timestamp logic, and is maintained per persistent QP
with `BOP_QC_TAU_EWMA_ALPHA`. The selected freshest QP supplies both `q0` and
its delay EWMA. Round zero has no prior observation and therefore uses queue
zero and `BOP_QC_DEFAULT_TAU_US`.

With `BOP_QC_QUEUE_LIMIT_MODE=1`, `Q_safe` is the actual kmin configured for
the explicit bottleneck rate by `KMIN_MAP`. `SwitchMmu::ConfigEcn` converts
that value to bytes with the same factor of 1000; `third.cc` passes that byte
value to every sender:

```text
packet_margin = N * BOP_PACKET_BYTES * BOP_QC_PACKET_MARGIN
queue_room = max(Q_safe - q0 - packet_margin, 0)
bdp_credit = floor((C - background) * tau / 8 * BOP_QC_BDP_FACTOR)
group_credit = min(queue_room, bdp_credit, total_group_round_bytes)
```

The runtime asserts the final ECN safety inequality. If the queue plus packet
margin is already unsafe, planning stops rather than emitting a plan that
claims the bound. Credit is divided by round-byte share using floor, then
remaining bytes are assigned in sender-rank order. The allocation is checked
to sum exactly to the one group credit; it is never multiplied by N.

Each QP begins its credit range at its NIC maximum rate after the original BOP
first-packet phase offset. A packet whose starting sequence is below the
credit boundary may cross it by at most one MTU. `GetNxtPacket` records that
crossing and `PktSent` switches to the original BOP base rate after accounting
for the burst packet at the maximum rate. The switch flag is asserted to
transition at most once. ACK feedback updates only future telemetry in this
mode and never invokes HPCC live-rate control.

`bop_qc_group_decisions.csv` records one bounded decision per group-round.
The extended `flow_plan.csv` records the reused base rate, per-flow credit,
sequence boundary, burst rate, switch result, and actual burst bytes.
`group_round_summary.csv` continues to carry queue, ECN, and PFC outcomes.

No simulation was run while implementing this mode. Validation consists of
the Python static/model tests and an incremental waf build.
