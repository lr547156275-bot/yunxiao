# BOP-v1 implementation

RS-HPCC's queue-threshold predictor, bisection solver, configuration fields,
QP state, decision CSV, and mode name were removed from runtime
`scratch/src`. Persistent QPs, sequence-to-round ACK mapping, INT, DCQCN,
HPCC, Gate, fixed paths, bounded traces, and disk safeguards were retained.

At the earliest sender release of a group, the coordinator plans exactly
once. For the explicitly configured shared bottleneck:

```text
work = residual_queue + sum(round_bytes)
available = BOP_RHO * capacity - BOP_BACKGROUND_BPS
T_link = 8 * work / available
T_line = max_f(8 * B_f / Rmax_f)
T_star = max(T_line, T_link)
r_f = min(Rmax_f, floor(8 * B_f / T_star))
```

Round zero uses queue zero and records
`first_round_queue_zero`. Later rounds select the freshest valid INT
observation that arrived no later than the planning event; absent telemetry
uses queue zero and records `no_valid_telemetry_queue_zero`. Capacity is
always available from the explicit scenario bottleneck and is replaced only
by a valid same-hop INT capacity observation.

BOP writes the rate once before release. ACK feedback never modifies its live
rate. `BOP_PHASE_STAGGER=1` sets only `m_nextAvail` for the first packet by
`sender_rank * BOP_PACKET_BYTES * 8 / capacity`; it does not alter the common
barrier or subsequent pacing.

`group_round_summary.csv` records common release, max-ACK barrier, group RCT,
formula terms, lower-bound efficiency, queue/ECN/PFC samples, and fallback.
`flow_plan.csv` records every per-flow rate and phase plan. Low-frequency
selected-link/flow traces retain the existing 64-MiB file and 128-MiB
per-run limits.

No ns-3 simulation was run during implementation. Validation consists only
of Python model/input/source tests and an incremental waf build.

## BOP-QB extension

BOP-QB is implemented as `CC_MODE=15` without changing the BOP-v1 solver.
The shared `PlanRoundGroup` result supplies its base rates. Its separate
group-credit block uses half of the real ECN threshold as the target queue,
subtracts the latest pre-release queue and participant packet margin, and
caps only by current group bytes. It has no feedback-delay or BDP term.

The new mode has isolated per-QP credit/switch state, flow-plan columns, and
`bop_qb_group_decisions.csv`. Modes 1, 3, 12, 13, and 14 retain their
existing branches and output schemas. See `docs/bop_qb.md` for the exact
formula, telemetry cutoff, and safety assertions.

## BOP-QB-Max extension

BOP-QB-Max uses the audited unused `CC_MODE=16` and directly reuses the
existing BOP family `T_star` and base-rate result. Its separate group credit
is the maximum current-round byte budget satisfying the real ECN threshold
after subtracting the latest eligible pre-release queue and participant
packet margin. It has no queue fraction, BDP, or feedback-delay input.

The mode has isolated QP credit/switch state, output schema, configuration,
checker, parser, and run roots. Existing modes 1, 3, 12, 13, 14, and 15 keep
their numbers and controller branches. See `docs/bop_qb_max.md`.
