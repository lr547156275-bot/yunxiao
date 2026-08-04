# CRFM / Round-Safe HPCC experiment

This directory implements periodic communication rounds on one persistent RDMA
QP, origin-round ACK classification, original HPCC and DCQCN baselines,
CRFM-Gate, the diagnostic HPCC Round Reset oracle, and Round-Safe HPCC.

The former empirical carry/recovery mechanism has been removed from runtime
code. Existing `analysis`, `analysis_fixed`, `results`, and prior run
directories are historical evidence only and are not valid RS-HPCC outputs.

No ns-3 simulation was run during the RS implementation task. Static tests and
incremental build success establish implementation consistency only, not
algorithm effectiveness.

From the simulation directory, manually run Smoke first:

```bash
./crfm_exp/run_rs_smoke.sh
```

After it passes, run the 24-run seed-1 screening:

```bash
./crfm_exp/run_rs_screening.sh
```

Confirm and diagnostic oracle commands are documented in
`docs/rs_hpcc_runbook.md`. New outputs go to `crfm_exp/rs_runs_smoke` and
`crfm_exp/rs_runs`. Scripts default to `JOBS=1`, bound logs, check disk space,
validate outputs, and resume only runs that pass the RS checker.
