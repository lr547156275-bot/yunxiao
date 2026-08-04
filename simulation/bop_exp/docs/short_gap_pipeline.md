# Short-message pipeline diagnostic

## Scope

`short_gap_pipeline_v1` is a read-only event diagnostic for exactly
`gap_50us`, seed 1, and the existing DCQCN (CC_MODE 1) and BOP-QB
(CC_MODE 15, queue fraction 0.5) implementations. It does not set a rate,
change an ACK, alter a queue, change phase stagger, or modify completion.

Both runs are prepared from the same case. Their `topology.txt`, `flow.txt`,
`rounds.txt`, and `fixed_paths.txt` hashes must match.

## Exact event sources

- Host `RdmaQpDequeue`: actual first/last DATA send for each QP-round.
- Bottleneck `QbbEnqueue`: forward DATA arrival at the configured egress.
- Bottleneck `PhyTxBegin` and `PhyTxEnd`: exact serialization intervals.
- Receiver-host `MacRx`: forward DATA arrival.
- Receiver-host `QbbEnqueue`: ACK generation, when the ACK is placed in the
  real high-priority RDMA egress queue.
- Sender-host `MacRx`: ACK arrival immediately before `ReceiveAck`.

Packets are parsed through the real `CustomHeader`. Bottleneck callbacks
accept only IPv4 protocol `0x11` packets whose forward five-tuple matches a
registered experiment flow. ACK callbacks accept only protocol `0xFC` and
reverse-map the cumulative ACK sequence to the original flow and round.
PFC, CNP, NACK, reverse traffic, and other ports are excluded.

No timestamp is inferred from `selected_link_timeseries.csv`; all diagnostic
times use `Simulator::Now().GetTimeStep()` in nanoseconds.

Because the existing seed plan contains signed sender jitter,
`common_release_ns` in this diagnostic is the earliest actual QP release in
the group, not the pre-jitter barrier anchor. This keeps
`sender_launch_ns = first_qp_send_ns - common_release_ns` physically
nonnegative. The checker independently reconstructs the same group RCT as
`max(ack_completion_time) - min(release_time)` from the existing
`round_summary.csv`; it also checks that final ACK arrival equals the
original global barrier.

## Busy and idle definition

The DATA window starts at the first bottleneck `PhyTxBegin` and ends at the
last bottleneck `PhyTxEnd`. DATA busy time is the sum of exact TxBegin/TxEnd
intervals. A positive difference between the next DATA TxBegin and the
previous DATA TxEnd is one idle gap. Thus `busy + idle == window` is checked
from the event stream.

`transmitted_data_bytes` counts serialized on-wire packet bytes so that
`effective_data_rate_bps = bytes * 8e9 / window_ns` is consistent with the
device Tx interval.

## Outputs and protection

Each run writes:

- `pipeline_timeline.csv`
- `bottleneck_idle_summary.csv`
- `per_qp_tail.csv`
- `diagnostic_meta.json`
- `bottleneck_data_events.csv`

The event detail contains only forward DATA TxBegin/TxEnd rows from the one
configured bottleneck. It is capped at 16 MiB. Reaching the cap stops event
detail only; in-memory summaries continue and the meta file records the
truncation.

`flow_completion_ns` in `per_qp_tail.csv` is the QP-round ACK completion
timestamp. For the final round it is also the persistent QP's completion
timestamp.

## Manual execution

From the simulation directory:

```bash
./bop_exp/run_short_diagnosis.sh
```

The script runs exactly two simulations and supports checkpoint resume. It
forces `KEEP_RAW=1`, defaults to `JOBS=1` and `MIN_FREE_GB=5`, validates both
runs, and writes the comparison under `bop_exp/diag_runs`.
