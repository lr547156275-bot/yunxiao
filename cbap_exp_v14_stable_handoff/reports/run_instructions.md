# Manual run instructions

From the repository root, run semantic validation first:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v14_stable_handoff/scripts/run_handoff_semantic.sh
```

Only after it reports `HANDOFF_SEMANTIC_PASS`, run the 30-run validation:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v14_stable_handoff/scripts/run_handoff_validation.sh
```

Both scripts support断点续跑 by skipping directories with a valid completion
flag and output contract. Failures retain diagnostics and are not treated as
zero-valued results.
