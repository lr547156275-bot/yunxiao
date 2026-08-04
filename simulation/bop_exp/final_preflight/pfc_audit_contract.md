# PFC event-level semantic audit contract

## Scope and fixed matrix

The audit is diagnostic-only. It runs exactly the nine seed-1 entries in
`pfc_audit_manifest.csv`; it does not change any congestion controller.
`open_loop_pfc_configured` and `open_loop_pfc_disabled` reuse the same
`pfc_only` input bundle and differ only in the runtime PFC switch and diagnostic
algorithm label.

## Objects and identities

- `queue_object_id` identifies the selected bottleneck `BEgressQueue` attached
  to `PFC_AUDIT_NODE:PFC_AUDIT_IF`. Enqueue/dequeue callbacks update the
  device-queue observation.
- `pfc_queue_object_id` identifies the switch `SwitchMmu` that evaluates the
  dynamic PFC condition for the same port/PG. The MMU threshold is reported by
  `GetPfcThreshold(PFC_AUDIT_IF)`.
- These objects have different roles and are intentionally not pointer-equal.
  A pointer inequality is not a failed PFC path. Conversely, a low-frequency
  egress queue maximum must not be presented as if it were the MMU occupancy
  that caused a pause.
- Every event must carry a numeric node, device, port, PG, queue occupancy and
  threshold. The configured audit port and PG are checked against the summary
  and configuration. `packet_owner` is `pfc_control`.

The summary's `queue_max_bytes` is a diagnostic maximum updated by both the
selected device queue callback and the PFC generation callback. Threshold
crossing is therefore established only from a `pause_generated` event row,
whose queue value is the MMU value used for that PFC decision.

## Required event chain

Only these six event types are valid:

1. `pause_generated`: the switch MMU decision emitted a pause;
2. `pause_received`: the upstream device received the pause frame;
3. `sender_paused`: that device set the selected PG's paused state;
4. `resume_generated`: the switch MMU emitted resume;
5. `resume_received`: the upstream device received resume;
6. `sender_resumed`: the device cleared the selected PG's paused state.

For every priority with a generated pause, timestamps must be nondecreasing
through the pause half of the chain and through the resume half. Counts in the
event file must exactly equal all six summary counters. A generated pause must
have queue occupancy at or above its event threshold. A `sender_paused` row
must report `sender_paused=1`; a `sender_resumed` row must report 0.
The checker reconstructs both endpoint interface indices from topology link
order: each generated pause/resume must be received on the peer device/port,
and each receive must be followed by the matching state transition on that
same device and PG.

An existing, header-only event file is an observed zero-event result. A missing
file, missing summary counter, malformed row, truncated log, or an incomplete
event chain is invalid and is never replaced with zero. In a runtime-disabled
run, all six observed counts must be zero. In a runtime-enabled run, zero
events remain a valid observation but do not verify the end-to-end PFC path.

## Sender stop semantics

Runtime `sender_paused` proves that the pause reached the sender-side
`QbbNetDevice` and activated `m_paused[PG]`. The static audit additionally
requires:

- host dequeue calls `RdmaEgressQueue::GetNextQindex(m_paused)`;
- `GetNextQindex` skips any queue whose `paused[qIndex]` is true;
- switch dequeue calls `DequeueRR(m_paused)`.

The combined runtime transition and static dequeue gate is the model-level
proof that the paused PG stops producing DATA packets. The event trace does
not claim a separate packet-by-packet no-transmit measurement. If any static
gate disappears, `sender_stop_static_gate_verified` is false and the audit
fails.

## Classification

- `PFC_PATH_VALID`: a complete six-event chain, exact counters, threshold
  crossing, sender pause/resume, and the static dequeue gate all pass.
- `PFC_NOT_TRIGGERED`: runtime PFC is enabled but no pause is generated.
- `PFC_DISABLED_CONFIRMED`: runtime PFC is disabled and all event counts are
  observed zero.
- `PFC_AUDIT_INVALID`: required output is absent, truncated, inconsistent, or
  contains a partial/invalid chain.

This audit classifies simulator semantics only. It does not convert the
open-loop reference into a formal end-host congestion-control baseline.
