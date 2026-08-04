# BOP-QB v1 implementation

`CC_MODE_BOP_QB=15` is isolated from DCQCN (1), HPCC (3), CRFM-Gate
(12), BOP (13), and BOP-QC (14). It joins the existing
`RdmaHw::PlanRoundGroup` BOP family and consumes the same single `T_star`
and base-rate calculation; no second BOP solver exists.

At the earliest jittered release of each global group, BOP-QB accepts only
the newest INT observation whose ACK arrived strictly before that planning
event. Round zero and later rounds without such telemetry use `q0=0` and
record the fallback. No observation arriving after release is eligible.

The real shared-bottleneck ECN kmin is obtained from `KMIN_MAP` using the
same byte conversion as switch ECN configuration. The one group budget is:

```text
Q_target = floor(BOP_QB_QUEUE_FRACTION * Q_ECN)
packet_margin = N * BOP_PACKET_BYTES * BOP_QB_PACKET_MARGIN
queue_room = max(Q_target - q0 - packet_margin, 0)
group_credit = min(queue_room, total_group_round_bytes)
```

The default queue fraction is fixed at 0.50. BOP-QB does not read feedback
delay, compute a BDP, use `BOP_QC_BDP_FACTOR`, or create per-QP group
credits. Runtime assertions enforce
`q0 + group_credit + packet_margin <= Q_target`.

Credit is divided by each flow's current-round byte share using floor.
Remaining integer bytes are assigned in sender-rank order, and the final
allocation must equal the single group credit exactly. Each QP sends its
credit range at its NIC maximum rate after the existing phase offset, then
switches once to the shared BOP base-rate result. A boundary packet may
cross the byte credit by no more than one MTU. INT updates future queue
observations but never invokes live HPCC control in BOP-QB.

`bop_qb_group_decisions.csv` contains one group-round budget decision.
The BOP-QB `flow_plan.csv` adds the base rate, per-flow credit, sequence
boundary, burst rate, switch state, and actual burst bytes. Existing BOP
and BOP-QC schemas remain selected only by their own CC modes.

Implementation validation uses Python model/source/input tests and an
incremental waf build. No ns-3 simulation is run by the implementation
task.
