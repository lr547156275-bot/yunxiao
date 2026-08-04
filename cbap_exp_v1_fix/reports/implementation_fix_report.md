# CBAP-v1 admission/credit repair

## Scope

This repair is restricted to CBAP modes 20–23 and their diagnostics. BOP-QB
remains `CC_MODE=15`; DCQCN, HPCC-INT, and BOP-QB control decisions were not
changed. No simulation result is interpreted here.

The task named `cbap_exp_v0_buggy_20260731/` as the prior-result location, but
that path was absent. The existing 452 MiB `cbap_exp/` tree was treated as the
old-result set and was neither overwritten nor deleted.

## Fix 1: strict admission hold

`RdmaHw::HasCompletePostReleaseFeedback` now requires every configured path
link to have both `sampleTimeNs > networkReleaseNs` and
`deliveryTimeNs > networkReleaseNs`. `ADMISSION_HOLD` ignores ordinary targets
until that condition is complete. Only post-release PFC, Q-high, local pause,
or root-congestion evidence can reduce the live rate early. Admission exits
through the named `ExitCbapAdmission` transition, which records the complete
feedback and audit timestamps.

## Fix 2: admission-scoped credit

`creditGateActive` is enabled only for CBAP-Full on release. Base-token plus
credit eligibility now requires all of: CBAP enabled, Full credit,
`creditGateActive`, and phase `CBAP_ADMISSION_HOLD`. Admission exit, recovery,
and completion disable the gate. The remaining credit is retained in
`creditRemainingAtAdmissionExit`; tracking packet eligibility is governed by
the current paced rate rather than the initial base rate.

## Fix 3: sender-side pacing and rescheduling

CBAP rate changes recompute the earliest unsent packet from the actual last
sender transmission time and the new serialization gap. The NIC wake-up is
cancelled and rescanned across all QPs so a stale wake-up cannot preserve the
old rate or postpone another QP. This path is CBAP-scoped; the original
non-CBAP `ChangeRate` branch is unchanged.

Actual sender `PktSent` callbacks now produce `TX_SEND`; scheduling and rate
changes produce `TX_SCHEDULE`, `TX_RESCHEDULE`, and
`TX_CANCEL_OR_INVALIDATE`. Tracking event rows are bounded by
`CBAP_TX_TRACE_TRACKING_PACKETS`, while the pacing-violation counter covers all
packets.

## Audit outputs

`cbap_flow_state.csv` contains admission entry/exit, first actual send,
post-release sample and complete-feedback timestamps, actual admission and
tracking rates, rate-update counters, gate timestamps, retained credit, and
pacing violations. `cbap_tx_events.csv` contains the required sender event,
packet, rate, credit, schedule, actual send, and gap fields.

The semantic validator compares the E2 independent and joint-batch rates from
actual admission sends, not only offline grants. It also enforces strict
post-release feedback, zero ordinary admission updates, admission-only credit,
the staggered E4 tracking check, and zero early sender gaps.

## Verification performed

- Generated exactly 20 seed-1 semantic entries and 84 reduced formal entries.
- Python/shell syntax checks passed.
- Ten source/manifest/resume static guards passed.
- Incremental build passed with `python2 ./waf build`.
- No `waf --run`, experiment runner, or ns-3 scenario was executed.

E3 victim is intentionally absent from the reduced rerun matrix: its previous
version generated neither PFC nor victim degradation, so it is retained only
as an old, ineffective scenario rather than silently treated as evidence.

Dynamic invariants deliberately remain unclaimed until the user runs the
20-run semantic gate. The 84-run formal script refuses to start unless the
semantic report begins with `SEMANTIC_PASS`.
