# Manual run instructions

From the repository root:

```bash
python3 cbap_exp_v12_scoped/tests/test_v12_static.py
cbap_exp_v12_scoped/scripts/build_only.sh
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  cbap_exp_v12_scoped/scripts/run_scope_regression.sh
```

The core runner refuses to start unless the regression analyzer has written
exactly `SCOPE_REGRESSION_PASS`:

```bash
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  cbap_exp_v12_scoped/scripts/run_core_comparison.sh
```

Use `MAX_JOBS=1` for the lowest memory/disk pressure. Valid completed runs are
skipped automatically. Detailed results can be packaged only after the manual
runs with `cbap_exp_v12_scoped/scripts/package_results.sh`.
