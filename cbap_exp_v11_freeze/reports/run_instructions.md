# Manual run order

From the repository root:

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control
```

1. Optional build-only repeat:

```bash
bash cbap_exp_v11_freeze/scripts/build_only.sh
```

2. Run the 11 semantic regressions:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v11_freeze/scripts/run_semantic_regression.sh
```

3. Confirm the first line of
`cbap_exp_v11_freeze/reports/semantic_regression_report.md` is
`SEMANTIC_PASS`.

4. Run the 63-run freeze matrix:

```bash
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v11_freeze/scripts/run_freeze_validation.sh
```

5. Victim calibration is independent and is not started automatically:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=180 \
  bash cbap_exp_v11_freeze/scripts/run_victim_calibration.sh
```

6. In the next analysis-only stage:

```bash
python3 cbap_exp_v11_freeze/scripts/analyze_freeze_results.py
INCLUDE_RUNS=1 bash cbap_exp_v11_freeze/scripts/package_results.sh
```

All run scripts support valid-run skipping. A `SKIP valid` line is normal.
