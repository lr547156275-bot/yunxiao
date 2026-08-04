# Input schema

Every generated run directory contains `topology.txt`, `flow.txt`,
`trace.txt`, `config.txt`, `rounds.txt`, `fixed_paths.txt`, and
`scenario_meta.json`.

## rounds.txt

The first line is the number of following records. Each record is:

```text
flow_id round_id round_group_id participant_count round_bytes compute_gap_ns jitter_ns jitter_group
```

`flow_id` indexes the single logical flow/QP in `flow.txt`. Round IDs must start
at zero and be contiguous per flow. `round_group_id` identifies the
synchronized group, and `participant_count` is its positive collective-runtime
sender-count prior; every QP in a group must carry the same value. The sum of
`round_bytes` for one flow must exactly equal its `flow.txt` `total_bytes`.
Round zero has `compute_gap_ns=0`;
its jitter is applied to the scenario's nominal first-release time. For every
later round, `compute_gap_ns + jitter_ns` must be positive.

Later absolute release times are deliberately absent from the input:

```text
release[k+1] = ack_completion[k] + compute_gap[k+1] + jitter[k+1]
```

This prevents a congested earlier round from overlapping the next release.

`jitter_group` records the sender group used by deterministic input generation;
it does not invoke an in-simulator RNG.

## fixed_paths.txt

Each record is:

```text
flow_index forced_spine_node
```

The entry installs an exact five-tuple match on the source leaf. The 16 senders
alternate spines 19 and 20; all traffic converges at destination leaf 18 and
receiver 16.

## Seed behavior

`prepare_rs_run.py` derives a fixed PRNG seed from SHA256 of
`scenario:seed`, applies ±5 us jitter to the first release and later compute
gaps, and records the plan SHA256. Thus the same scenario+seed has identical
round bytes, compute gaps, and jitter across algorithms, while seeds 1/2/3 have
distinct hashes. Algorithm-dependent absolute release times are expected.

The legacy `flow.txt` schema stores start time as floating-point seconds. Its
value creates the persistent QP at the nominal first release plus the stored
first-round jitter. `ReleaseRound(0)` records the actual ns-3 time; later
release events and RCT use dynamically recorded integer nanoseconds.

The legacy entry reads flows sequentially and schedules the next row relative
to the current simulation time. Therefore first-round jitter samples are still
drawn from the seeded PRNG but sorted and assigned in flow-ID order, keeping
`flow.txt` start times nondecreasing. Later-round jitter remains independent
and is applied only after the preceding round's ACK completion.
