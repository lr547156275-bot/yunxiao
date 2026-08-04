# CBAP-SBA scheme 1: Startup Batch Admission

This entry point is independent of the frozen CBAP v1.x/v2.0 runners.  It
uses `CC_MODE=30`; `CC_MODE=15` remains BOP-QB and is unchanged.

CBAP-SBA owns a collective flow only from atomic batch admission until that
flow's first causally valid actionable CNP.  A positive grant is paced at the
exact applied rate and hands that real rate to native DCQCN once.  A zero
grant is a scheduler-level `ADMISSION_HOLD`: it sends no DATA, installs no
zero/1-bps transport rate, and is reconsidered on telemetry delivery,
capacity release, or the existing control tick.  A handed-off flow never
returns to CBAP-SBA.

Run the reduced suite (six conservation/state-machine checks plus the
four-flow ns-3 handoff smoke):

```bash
./cbap_sba_experiments/scripts/run_formal_reduced.sh
```

Run the four-flow ns-3 smoke (single seed, deterministic ECN to exercise the
one-time DCQCN handoff, no Clos matrix):

```bash
./cbap_sba_experiments/scripts/run_smoke.sh
```

Generated run directories live under `runs/` and are ignored by Git.  The
only structured SBA event fields are: `batch_id`, `flow_id`, `release_time`,
`path`, `available_capacity`, `grant_rate`, `applied_rate`,
`state_transition`, `hold_reason`, `readmission_reason`,
`first_feedback_time`, and `handoff_rate`.
