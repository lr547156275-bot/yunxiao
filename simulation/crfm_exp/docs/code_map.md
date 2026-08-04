# Source code map

## Entry and input parsing

The executable entry is `scratch/third.cc`. Its first positional argument is
the config path. The parser reads whitespace-separated key/value records. It
opens:

- topology: first line `node_count switch_count link_count`; second line is the
  switch-node list; each link is
  `node_a node_b data_rate propagation_delay error_rate`.
- flow: first line is flow count; each row is
  `src dst priority_group dst_port total_bytes start_time_seconds`.
- trace: first line is the count, followed by node IDs. CRFM cases use zero
  packet-trace nodes.
- rounds: first line is row count; rows are documented in `input_schema.md`.

`ScheduleFlowInputs` installs the exact-match fixed path, registers the round
schedule, and installs one `RdmaClient`. `RdmaClient::StartApplication` calls
`RdmaDriver::AddQueuePair`, which calls `RdmaHw::AddQueuePair`.

## Packet and ACK path

`RdmaHw::GetNxtPacket` obtains payload from the same QP and advances
`RdmaQueuePair::snd_nxt`. New data is eligible only up to
`crfm.releasedBytes`; `m_size` remains the total over all rounds.

On receipt, `RdmaHw::ReceiveUdp` creates the cumulative ACK and preserves the
existing PFC/ECN/INT path. `RdmaHw::ReceiveAck` resolves the sender QP with the
existing `(source IP, ACK destination port, priority group)` key and advances
`snd_una`.

The ACK origin round is obtained from `ack.seq - 1` against the QP's contiguous
round sequence intervals. No PacketTag or network header field is used.

## Round events

- Release: round zero is released at persistent-QP creation. On cumulative ACK
  completion, `RecordRoundAckCompletion` schedules the next release after its
  configured compute gap plus jitter. `RdmaHw::ReleaseRound` records the actual
  release time, increments only `releasedBytes` to the registered end sequence,
  and wakes the existing NIC/QP.
- Injection end: `GetNxtPacket` detects the first transition where `snd_nxt`
  reaches that round's end sequence.
- ACK completion: `RecordRoundAckCompletion` detects the first cumulative ACK
  where `snd_una` reaches the end sequence.
- QP completion: the original `IsFinished` remains `snd_una >= m_size`, so the
  QP is deleted only after the final round.

## HPCC and CRFM

HPCC is mode 3. `HandleAckHp` and its `UpdateRateHp` action remain the baseline
rate controller. `SwitchNode::UsesHpccInt` enables the same NORMAL INT
`PushHop` implementation for modes 3 and 11–13.

For a round QP, `HandleAckCrfm` classifies feedback and evaluates the same HPCC
normalized-load hop without side effects. It invokes original `HandleAckHp`
where the selected mode permits. RS late feedback updates only an estimator.
Final live QP rates are changed by original `UpdateRateHp`, Reset through
`SetCrfmRate`, or the one-shot RS initializer in `ReleaseRound`.

Current rate is `RdmaQueuePair::m_rate`; HPCC's controller rate is
`hp.m_curRate`. Sequence progress is `snd_nxt`/`snd_una`.

PFC state is read from `QbbNetDevice::IsPaused`. Queue bytes come from the
selected switch Qbb queue. Per-port transmitted bytes and ECN marks come from
bounded counters on `SwitchNode`. No per-packet disk output was added.
