# BOP-v1 code map

## Entry and input formats

- Executable entry: `scratch/third.cc`, invoked as
  `python2 ./waf --run "scratch/third <config>"`.
- `topology.txt`: header `node_count switch_count link_count`, one line of
  switch IDs, then `src dst rate delay error_rate` per link.
- `flow.txt`: count, then `src dst pg dport total_bytes start_time_seconds`.
  Every logical flow creates one QP for all rounds.
- `trace.txt`: traced-node count followed by node IDs; BOP cases use zero.
- `rounds.txt`: count, then
  `flow_id round_id group_id participant_count round_bytes compute_gap_ns
  sender_jitter_ns sender_rank common_release_hint_ns`.
  Only round zero carries the absolute common-release hint. Later releases
  are calculated at runtime from the preceding global ACK barrier.
- `fixed_paths.txt`: `flow_id forced_spine_id`. Exact-match forwarding is
  installed in `scratch/third.cc::InstallFixedPath`.

## Persistent QP and ACK mapping

- `RdmaQueuePair::snd_nxt/snd_una` remain continuous across rounds.
- `crfm.releasedBytes` gates new transmission in `RdmaHw::GetNxtPacket`.
- `GetRoundIndexForSequence(ack_seq-1)` maps cumulative ACK feedback to its
  original sequence interval and round.
- `RecordRoundAckCompletion` detects `snd_una >= round.endSeq`.

## Global barrier

`RdmaHw::s_roundGroups` is a simulation-process coordinator shared by all
sender `RdmaHw` objects. `NotifyRoundGroupAck` counts QPs and records the
maximum ACK completion. Only when the count reaches `participantCount` does
it schedule the next group at `barrier + compute_gap`. Each sender release is
then `common_release + sender_jitter`.

## CC modes and telemetry

- DCQCN: 1 (unchanged).
- HPCC: 3 (unchanged).
- HPCC Round Reset: 11 (diagnostic infrastructure retained).
- CRFM-Gate: 12 (unchanged).
- BOP: 13 (reuses the removed RS mode).
- BOP-QC: 14 (bounded group BDP credit layered on the shared BOP plan).
- BOP-QB: 15 (fixed 0.5 ECN-threshold queue-budget credit).
- BOP-QB-Max: 16 (maximum no-ECN queue-budget credit).

`SwitchNode::UsesHpccInt` supplies INT for modes 3 and 11–16. HPCC mode 3
still calls the original `HandleAckHp`; Gate calls it only for actionable
current-round feedback. BOP-family modes never call it:
`EvaluateHpFeedback` only updates a future-round queue/capacity observation;
BOP-QC also updates its feedback-delay EWMA. BOP-QB-Max shares the single
BOP `T_star`/base-rate plan, but its isolated credit block reads only the
pre-release queue sample, ECN threshold, participant count, packet size, and
round bytes; it does not read the QB fraction or QC tau/BDP state.

## Explicit BOP-v1 bottleneck

All generated cases declare one `selected_bottleneck` and use fixed paths
that converge on it. `BOP_BOTTLENECK_BPS` is copied from the topology's
uniform 100-Gbit/s rate. BOP-v1 does not infer or guess a multi-link path.
