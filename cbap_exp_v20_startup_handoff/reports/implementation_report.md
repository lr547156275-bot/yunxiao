# CBAP-v2.0 implementation report

## Status

CBAP-SAH is implemented as `cbap_v20_startup_handoff` with two new, previously unused modes:

- `CC_MODE=28`: `cbap_v20_startup_handoff_dcqcn`
- `CC_MODE=29`: `cbap_v20_startup_handoff_hpcc`

The implementation compiles with the repository's Python 2 waf path. No ns-3 experiment was executed while preparing this implementation.

## Source changes

- `simulation/src/point-to-point/model/rdma-hw.h`: mode IDs, v2.0 configuration, audit records, runtime state, and method declarations.
- `simulation/src/point-to-point/model/rdma-hw.cc`: causal classification, blind-window work calculation, startup budget, batch progressive filling, bounded exit, and smooth base-CC handoff.
- `simulation/src/point-to-point/model/rdma-queue-pair.h/.cc`: appended v2.0 states and initialized per-QP ownership/audit fields. Existing phase numeric values were not changed.
- `simulation/scratch/third.cc`: configuration parsing/validation, v2.0 CSV output, and run-level metric accounting.

The new experiment framework is isolated under `cbap_exp_v20_startup_handoff/`.

## Frozen behavior audit

`CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX=25` and its `v13_shadow_only` path remain present. The v2.0 implementation uses new modes and a separate planner/evaluator. It is explicitly excluded from legacy `RecomputeCbapTracking`; no existing v1.3 decision branch or constant was changed for v2.0.

The worktree was already dirty before this task. Other modified source files shown by `git status` are pre-existing and were not edited for v2.0.

`reports/code_changes.patch` is therefore a cumulative HEAD-to-worktree patch for the five source files touched by this task; it necessarily contains earlier uncommitted edits in those shared files. `reports/files_changed.txt` identifies the v2.0 source and generated framework files without claiming ownership of the pre-existing hunks.

## Ownership isolation

During `STARTUP_ADMISSION`, CBAP is the only rate writer. DCQCN CNP updates and HPCC live-rate updates are held, while HPCC telemetry remains readable. At handoff, the inherited live rate and target rate are retained, packet spacing is preserved, credit is disabled, and the phase becomes `BASE_CC_ONLY`. From that point, `SetCbapRate` is protected by an assertion, legacy tracking excludes v2.0 QPs, and CBAP packet tracing returns immediately.

## Logging

`cbap_v20_batch.csv` contains one row per batch-link and `cbap_v20_flow.csv` one row per batch-flow. Existing bounded logs and disk checks are reused. Post-handoff CBAP per-packet logging is disabled, preventing base-CC lifetime growth.

## Validation performed

- model tests: 3 passed;
- static integration tests: 6 passed;
- Python syntax checks: passed;
- shell syntax checks: passed;
- manifest determinism: passed;
- prepare-run dry check: passed;
- Python 2 waf incremental build: passed.

No performance or correctness claim is made before the semantic runs complete.

## First semantic-run corrections

The first manual semantic attempt exposed two integration defects and one post-processing mismatch. They were corrected without changing the startup-budget formula or either base CC:

- a 1-bps zero-budget startup left the only send event far in the future after DCQCN increased its rate; v2.0 now refreshes that QP's schedule after the native DCQCN timer changes the rate;
- a fresh port summary and the 2-RTT lease could share a timestamp, with the lease event winning by event UID; the lease now performs a same-timestamp deferred final check so already-queued feedback is observed first;
- v2.0 now uses the corrected generic and full-work metric collectors and validates scenario-specific semantic predicates before reusing a run.

The invalid attempts are retained by the runner under each run's `failed_attempts/` directory when the user reruns semantic validation.

The first rescheduling implementation also exposed DCQCN's integer transition from an inherited `1 bps` to a temporary `0 bps`. Calculating a finite packet interval at zero caused an ns-3 `int64x64` overflow. The final guard does not alter that native transition: it waits until DCQCN itself produces a positive rate, then refreshes the outstanding QP schedule.
