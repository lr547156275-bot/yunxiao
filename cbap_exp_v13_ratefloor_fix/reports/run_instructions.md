# Manual run instructions

From the repository root:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v13_ratefloor_fix/scripts/run_ratefloor_semantic.sh
```

Only if the first line of `reports/ratefloor_semantic_report.md` is
`RATEFLOOR_SEMANTIC_PASS`, run:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v13_ratefloor_fix/scripts/run_reduced_validation.sh
```

Both scripts support valid-run skipping. `MAX_JOBS=1` is the safe default.
They disable `NS_LOG`, core dumps, enforce the free-space guard, cap stdout,
and retain failed diagnostics.
