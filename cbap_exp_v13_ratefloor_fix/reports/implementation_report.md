# CBAP v1.3 rate-floor fix implementation

## Scope

This change adds `cbap_full_v13_ratefloor_fix` beside the frozen
`cbap_full_v12_scoped`. It does not replace v1.2, alter scope admission,
queue credit, progressive filling, feedback freshness, or the existing
baseline congestion-control modes. Existing `cbap_exp_v12_scoped/` results
were not modified.

## Execution semantics

- v1.2 remains CC_MODE 24 with `ONE_PACKET_PER_EPOCH_LEGACY`.
- v1.3 is CC_MODE 25 with `EXACT_GRANT_PACING`.
- A positive v1.3 grant is capped only by the existing QP maximum and
  Admission-Hold grant. It is not raised to one packet per control epoch.
- Packet spacing is `ceil(8 * wire_bytes * 1e9 / rate_bps)` nanoseconds.
  `CONTROL_EPOCH` remains a controller update interval, not a sending floor.
- A zero grant puts the QP into `zeroGrantPaused`, invalidates the current
  egress schedule, and prevents DATA selection. A later positive grant
  schedules from `max(now, last_actual_tx + new_gap)` and therefore does not
  repay paused service as a burst.

## Capacity audit

Each controlled link receives one audit row per CBAP epoch. The audit records
planner, requested target, applied QP rate, measured TX rate, legacy-floor
clamps, zero grants, and post-application capacity excess. The violation
tolerance is `max(1 bps, 1e-9 * C_l)`. Measured TX is reported separately
because packetization makes it unsuitable as a substitute for the applied
rate constraint.

The audit capacity follows the plan that is actually live: while any flow on
a link remains in Admission Hold it retains that admission plan's capacity,
including the existing Queue Credit allowance. It switches to tracking
capacity only after the hold exits. This is audit bookkeeping only and does
not feed the controller.

## Diagnostic zero-grant case

The synthetic hook is disabled by default and accepted only in mode 25. The
generated diagnostic case forces flow 1 to zero for epochs 610 through 612,
then releases it back to the unchanged planner. This is not a new policy and
is not enabled by either formal matrix.

## Validation boundary

This preparation phase ran source-level tests and an incremental build only.
The semantic and reduced scripts are user-run workflows; no ns-3 experiment
was executed here. Performance and research conclusions require those runs.
