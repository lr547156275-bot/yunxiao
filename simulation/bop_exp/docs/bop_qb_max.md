# BOP-QB-Max v1

## Mode and isolation

The source audit found modes 11--15 occupied by Round-Reset, Gate, BOP,
BOP-QC, and BOP-QB. Mode 16 was unused and is assigned to
`CC_MODE_BOP_QB_MAX`. Existing mode numbers and their controller branches are
unchanged.

`BOP-QB-Max` joins the existing `PlanRoundGroup` BOP family. It consumes the
same single `T_star` and `selected` base-rate result as BOP, BOP-QC, and
BOP-QB; it does not contain a second BOP solver. Its ACKs update only the
future telemetry estimate and never run live HPCC rate control.

## Queue observation and maximum credit

The coordinator chooses the freshest valid INT queue observation whose ACK
arrived strictly before the earliest sender release of the group. The
decision records the INT queue sample time and its age at planning. If no
eligible observation exists, `q0=0`, the sample time and age are zero, and
the fallback is `no_valid_pre_release_queue`. Feedback arriving at or after
release is ineligible.

The real shared-bottleneck ECN kmin comes from `KMIN_MAP` using the same
kilobyte-to-byte conversion as BOP-QB:

```text
packet_margin =
    participant_count * BOP_PACKET_BYTES * BOP_QB_MAX_PACKET_MARGIN
queue_room = max(Q_ECN - q0 - packet_margin, 0)
group_credit = min(queue_room, total_group_round_bytes)
```

There is no queue fraction, BDP, feedback-delay, tau, or per-QP queue
budget. Runtime assertions enforce:

```text
q0 + group_credit + packet_margin <= Q_ECN
```

The final BOP-QB-Max run config contains only these algorithm-specific
settings:

```text
BOP_QB_MAX_PACKET_MARGIN 1
BOP_QB_MAX_ENABLE_PHASE_STAGGER 1
```

## Allocation and pacing

Each flow receives the floor of its current-round byte share of the one
group credit. Remaining integer bytes are assigned in sender-rank order.
The allocation must sum exactly to the group credit, and no flow may receive
more than its current round bytes.

After the existing first-packet phase offset, a QP sends the credit interval
at its NIC/QP maximum rate. The first packet crossing the credit boundary may
overshoot by at most one MTU; immediately after that packet is paced, the QP
switches once to the unmodified BOP base rate. The persistent QP, sequence
space, five-tuple, ACK-to-round mapping, and global barrier are unchanged.

## Outputs

`bop_qb_max_group_decisions.csv` contains one row per group-round. The
`queue_sample_time` field is seconds and `queue_sample_age_us` is
microseconds. `flow_plan.csv` uses an isolated BOP-QB-Max schema containing
the base rate, flow credit, credit sequence boundary, burst rate, actual
burst bytes, and switch flag.

The existing group, flow, round, selected bottleneck, ECN, PFC, goodput, and
utilization outputs are retained. File size, disk-space, compression, and
resume protections remain in `scripts/common.sh`.

No ns-3 simulation is run as part of this implementation task.
