# CBAP-v1 manual run instructions

Run from the repository root:

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control
```

Optional repeat of the build-only check (does not run a simulation):

```bash
bash cbap_exp_v1_fix/scripts/build_only.sh
```

First run the 20-run semantic validation matrix:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v1_fix/scripts/run_semantic_validation.sh
```

The validator prints exactly `SEMANTIC_PASS` or `SEMANTIC_FAIL` and writes
`cbap_exp_v1_fix/reports/semantic_validation_report.md`. Do not start the
formal matrix after a failure.

Only after `SEMANTIC_PASS`, run the 84-run reduced formal matrix:

```bash
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v1_fix/scripts/run_formal_reduced.sh
```

Both runners support valid-run skipping. To reduce resource use, set
`MAX_JOBS=1`. Failed run directories and their bounded `stdout.log` are kept.

After formal runs exist, aggregate existing results without rerunning them:

```bash
bash cbap_exp_v1_fix/scripts/analyze_existing_results.sh
```

No performance conclusion is produced automatically by these runners.
