# RS-HPCC source audit

This audit was written before replacing the RA-HPCC controller. The requested
`research_archive/crfm_ra_hpcc_stop` archive is not present in this checkout;
`research_archive` contains only FCTree and TriSTATE stop archives. Therefore
the audit uses the current source, current git diff, the completed CRFM
documents, and the fixed-run analysis as evidence. No missing archive content
is inferred.

## Entry, modes, and persistent rounds

The executable entry is `scratch/third.cc`. The current controller dispatch is:

| CC_MODE | Controller |
|---:|---|
| 0 | no controller |
| 1 | original DCQCN |
| 3 | original HPCC |
| 7 | TIMELY |
| 8 | DCTCP |
| 10 | HPCC-PINT |
| 11 | HPCC round reset |
| 12 | CRFM gate |
| 13 | old RA-HPCC, to be replaced in place by RS-HPCC |

`ScheduleFlowInputs` creates one `RdmaClient` and one QP for each `flow.txt`
row. `RdmaHw::AddQueuePair` installs the entire round schedule on that QP and
schedules only `ReleaseRound(..., 0)`. `RecordRoundAckCompletion` schedules
each later release from the preceding cumulative-ACK completion plus the
planned compute gap and jitter. `ReleaseRound` advances only
`crfm.releasedBytes`; it does not recreate the QP or reset `snd_nxt`/`snd_una`.

The current round plan contains `flow_id`, `round_id`, `round_bytes`,
`compute_gap_ns`, `jitter_ns`, and `jitter_group`. RS-HPCC will extend the row
with `round_group_id` and `participant_count`; both values come from
`scenario_meta.json`, where the participant count is explicitly a collective
runtime prior. The current round byte count is
`RdmaQueuePair::CrfmRoundState::roundBytes`.

## ACK origin and controller paths

`ReceiveAck` resolves the QP with the existing destination-IP/source-port/PG
key and cumulatively advances `snd_una`. `HandleAckCrfm` maps `ack.seq - 1`
through `RdmaQueuePair::GetRoundIndexForSequence`, which searches the
contiguous `[startSeq,endSeq)` intervals. It then classifies the ACK as
`ACTIONABLE_CURRENT`, `LATE_SAME_ROUND`, or `STALE_OLDER_ROUND`.

Original HPCC is `HandleAckHp`/`UpdateRateHp`; original DCQCN uses the CNP bit
in `ReceiveAck`, `cnp_received_mlx`, `UpdateAlphaMlx`,
`CheckRateDecreaseMlx`, and the existing recovery timers. RS-HPCC will call
the unmodified `HandleAckHp` for actionable current-round feedback. Its only
new live-rate action will occur once in `ReleaseRound` for rounds after zero.

## INT fields and feedback timing

`SwitchNode::SwitchNotifyDequeue` pushes one NORMAL INT hop for modes 3 and
11--13. Each `IntHop` exposes:

- `GetQlen()` in bytes (80-byte encoding units times `INT_MULTI`);
- `GetLineRate()` in bit/s, including the configured 100 Gbit/s encoding;
- `GetBytes()`/`GetBytesDelta()` for transmitted bytes;
- `GetTime()`/`GetTimeDelta()` for a 24-bit nanosecond timestamp.

HPCC derives hop load from transmitted-byte delta divided by timestamp delta,
adds its queue term, and smooths it over `m_baseRtt`. It has no separate
explicit feedback-loop-delay state. For RS, feedback delay is measured as ACK
arrival time minus the origin round's actual release time; an EWMA is kept per
QP. The queue sample timestamp is reconstructed from the same selected hop's
wrapped 24-bit timestamp relative to the current simulator time. Queue,
capacity, normalized load, and sample time are never combined across hops.

## ECN and PFC thresholds

`third.cc` parses `KMIN_MAP`/`KMAX_MAP`; `SwitchMmu::ConfigEcn` converts their
kilobyte values to bytes by multiplying by 1000. RS uses the deterministic
lower ECN threshold (`KMIN_MAP`) as `RS_ECN_THRESHOLD_BYTES`.

The active cases use dynamic PFC. `SwitchMmu::GetPfcThreshold` returns

`(buffer_size - total_hdrm - total_rsrv - shared_used_bytes) >> pfc_a_shift`.

For the uniform 100-Gbit/s topology, `pfc_a_shift=3`. With `M` active
bottleneck-switch ingress ports and no unmodelled background ingress, the
earliest symmetric
pause boundary is conservatively bounded by

`(buffer_size - total_hdrm - total_rsrv) / (2^shift + M)`.

Here `M=2` is derived from the two fixed spine paths and is distinct from the
RS collective participant prior `N=16`. The RS input generator derives the
threshold from topology link delays/rates, configured buffer size, and source
constants (4 KiB reserve and three-BDP headroom). It fails closed if dynamic
PFC, a single uniform supported link rate, or these invariants do not hold.
The derived byte value is written both to config and scenario metadata.

## Round-start rate insertion point

Mode 13 will be renamed `CC_MODE_RS_HPCC`. `RdmaHw::ReleaseRound` is the sole
RS initialization point. Round zero retains the baseline line-rate start.
For each later round, a side-effect-free model selects the maximum safe rate,
then one helper updates the QP live pacing rate and the HPCC current-rate
state consistently. Subsequent actionable feedback continues through the
original `HandleAckHp`; late and stale feedback cannot change live rate.
