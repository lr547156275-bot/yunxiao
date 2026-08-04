# CRFM INT and round-schedule fix report

## Scope

This fix is limited to the three requested items. It does not change the
RA-HPCC formulas, feedback classification, CC parameters, topology, traffic
sizes, or congestion-control baselines. No ns-3 simulation was run.

## 1. Shared HPCC INT

`SwitchNode::UsesHpccInt` is the single mode predicate for NORMAL HPCC INT.
Modes 3, 11, 12, and 13 now enter the same existing `PushHop` statement.
There is no duplicated per-mode telemetry implementation. Mode 3 still reaches
the original `HandleAckHp`; Reset/Gate/RA remain different only at ACK handling
and round release.

## 2. ACK-aligned round schedule

`rounds.txt` now stores:

```text
flow_id round_id round_bytes compute_gap_ns jitter_ns jitter_group
```

The first release occurs when the persistent QP is created at the scenario's
nominal first time plus its seeded jitter. Each later release is scheduled only
when the preceding cumulative ACK crosses that round's end sequence:

```text
release[k+1] = ack_completion[k] + compute_gap[k+1] + jitter[k+1]
```

The same QP, five tuple, `snd_nxt`, `snd_una`, total size, and contiguous
sequence intervals are preserved. Input plans remain identical across
algorithms for a given scenario/seed; actual absolute releases may differ.
`run_meta.json` records both the input-plan SHA256 and actual release times.

## 3. Fixed smoke checks

The updated checker rejects a fixed run unless:

- every algorithm records a nonzero INT hop;
- modes 11–13 record nonzero normalized load;
- RA records a nonzero suggested rate and at least one carry update;
- Gate records zero carry updates;
- HPCC records direct original-controller updates;
- every later release is after the preceding ACK completion and exactly follows
  the compute-gap-plus-jitter plan;
- every injection-relative gap is positive;
- fixed-smoke RA and Gate next-round start-rate vectors are not identical.

Static checks additionally require one shared `PushHop`, all four mode IDs in
the helper, ACK-completion scheduling, unchanged continuous sequence gating,
and distinct seed plans.

## Output isolation

Fixed scripts write only to `crfm_exp/runs_fixed`. The original
`crfm_exp/runs` results and `crfm_exp/analysis` invalid-first-audit artifacts
are retained without modification.

## Verification

- Python syntax checks: passed.
- Eight-case schema and seed-plan static checks: passed.
- Shared INT and ACK-aligned scheduling source invariants: passed.
- Incremental `python2 ./waf build`: passed.
- ns-3 simulations executed by this fix task: zero.
