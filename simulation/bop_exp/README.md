# Barrier-Optimal Pacing (BOP-v1)

This experiment uses one persistent QP per sender, a true group-wide
max-ACK barrier, fixed ECMP paths, and an explicit single shared bottleneck.

From the simulation directory, run manually:

```bash
./bop_exp/run_smoke.sh
./bop_exp/run_screening.sh
./bop_exp/run_confirm.sh
```

BOP-QC is a separate mode and writes to separate run roots:

```bash
./bop_exp/run_qc_smoke.sh
./bop_exp/run_qc_screening.sh
./bop_exp/run_qc_confirm.sh
```

BOP-QB is another isolated mode and writes to `qb_runs_smoke`/`qb_runs`:

```bash
./bop_exp/run_qb_smoke.sh
./bop_exp/run_qb_screening.sh
./bop_exp/run_qb_confirm.sh
```

The BOP-QB smoke matrix has 8 runs, screening has 35 seed-1 runs, and
confirm has 105 total runs while resuming valid seed-1 outputs.

BOP-QB-Max uses separate `max_runs_smoke`/`max_runs` roots:

```bash
./bop_exp/run_max_smoke.sh
./bop_exp/run_max_screening.sh
./bop_exp/run_max_confirm.sh
```

Its smoke matrix has 6 runs. Screening has 22 seed-1 runs: four short
scenarios with DCQCN, Gate, BOP-QB, and BOP-QB-Max, plus three control
scenarios with BOP-QB and BOP-QB-Max. Confirm contains 66 runs across seeds
1, 2, and 3 and resumes valid seed-1 output automatically.

The exact-event short-message pipeline diagnostic is separate from every
suite and runs only `gap_50us`, seed 1, for DCQCN and BOP-QB:

```bash
./bop_exp/run_short_diagnosis.sh
```

It writes to `bop_exp/diag_runs`, preserves raw event detail, and does not
change either controller. See `docs/short_gap_pipeline.md`.

These scripts default to `JOBS=1`, enforce the existing disk and log limits,
and resume only runs accepted by the corresponding output checker.

Smoke has 6 runs, screening has 32 seed-1 runs, and confirm has 96 total
runs while resuming already valid seed-1 outputs. Defaults are `JOBS=1`,
`MIN_FREE_GB=5`, `KEEP_RAW=0`; `CASES`, `ALGOS`, and `SEEDS` may override
the matrices. Outputs are under `bop_exp/runs_smoke` and `bop_exp/runs`.

The implementation task did not run any ns-3 simulation and makes no claim
about BOP effectiveness.
# Final BOP-QB validation

The frozen final candidate is `bop_qb` (CC_MODE 15) with
`BOP_QB_QUEUE_FRACTION 0.50`. The final-validation suite adds only two
diagnostic-only modes:

- `dcqcn_wire_equalized` (CC_MODE 17);
- `bop_qb_oracle_q0` (CC_MODE 18).

Run these manually from the simulation directory:

```bash
./bop_exp/run_final_smoke.sh
./bop_exp/run_final_screening.sh
./bop_exp/run_final_confirm.sh
```

The screening matrix has 20 runs for seed 1. The confirm matrix has 60 runs
for seeds 1,2,3 and skips valid seed-1 runs already in `bop_exp/final_runs`.
Do not start screening unless smoke passes.
