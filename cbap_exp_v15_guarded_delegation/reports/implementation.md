# CBAP-v1.5 implementation

- Identity: `cbap_full_v15_guarded_delegation`, CC_MODE 27, base CC DCQCN.
- Frozen identities: v1.3 is CC_MODE 25 and v1.4 is CC_MODE 26.
- State transition: the unchanged v1.4 stable-candidate predicate triggers a one-way transition from TRACKING to `CBAP_DELEGATED_ENVELOPE` (phase 8).
- Ownership: original DCQCN state writes only `dcqcnDesiredRateBps`; `ProjectCbapDelegatedEnvelope` is the only delegated-phase applied pacing writer.
- Budget: the projector uses the existing effective-capacity telemetry and the v1.3 protection floor with its existing rebalance decay. Queue credit is not added after delegation.
- Projection: each controlled link computes a proportional scale, then each flow uses the minimum scale on its path exactly once.
- Anti-windup: bound flows suppress positive Fast-Recovery/AI/HAI desired updates before target state accumulates; CNP reductions remain active.
- Pacing: the existing exact wire-byte pacing and explicit zero-rate pause/resume path is retained.
- Audits: link/flow envelope, controller ownership, control messages, incomplete incumbent progress and all-work metrics are emitted without per-packet disk logging.

No ns-3 experiment was run during implementation.
