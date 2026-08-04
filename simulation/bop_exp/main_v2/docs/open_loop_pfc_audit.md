# Open-loop and PFC static audit

## Static conclusion

The historical `pfc_only` identifier is misleading. `CC_MODE=0` performs no
end-host congestion-control update and injects at the QP maximum rate. ECN is
configured at switches, but this sender mode does not execute an ECN/CNP rate
controller. Its main-v2 identifier is `open_loop_pfc_configured`, its display
name is `open_loop_no_endhost_cc`, and its class is
`open_loop_reference`.

**PFC configured but runtime pause behavior not verified.**

It is excluded from every “best formal CC baseline” selection.

## PFC path

- `scratch/third.cc` configures dynamic PFC thresholds, per-port headroom,
  pause time, and Qbb devices. The main workloads use priority/PG 3.
- `SwitchNode::CheckAndSendPfc` asks `SwitchMmu::CheckShouldPause` and sends a
  PFC frame on the congested ingress port. `CheckAndSendResume` sends the
  explicit resume.
- `QbbNetDevice::Receive` recognizes protocol `0xFE`, sets
  `m_paused[priority]`, and clears it on resume.
- Host scheduling calls `RdmaEgressQueue::GetNextQindex(m_paused)`, so a
  received pause can prevent that priority from being selected.
- The old `QbbPfc` trace records only receive-side state changes. It does not
  prove pause generation, delivery pairing, or the actual paused interval.
- Paper queue statistics read the bottleneck output `BEgressQueue`. PFC
  decisions use `SwitchMmu` ingress/shared/headroom counters. These are
  distinct accounting objects and must not be treated as interchangeable.

Therefore the historical data support only `OPEN_LOOP_NOT_PFC_BASELINE`.
The manual event-level audit is required before making a runtime PFC claim.

## New diagnostic

`open_loop_pfc_disabled` keeps `CC_MODE=0`, ECN configuration, traffic,
topology, fixed paths, and timing identical, but sets `PFC_RUNTIME_ENABLE=0`.
That switch attribute only suppresses generation of PFC pause/resume frames.
Its default is enabled, so existing algorithms are unchanged.

The new event trace observes generation, reception, actual sender pause,
resume generation, resume reception, and actual sender resume. The semantic
summary explicitly names the output queue object and the MMU PFC accounting
object. Queue maxima are updated from enqueue/dequeue events rather than a
low-frequency time series.
