# Manual run instructions

Run from the repository root. The commands preserve failed diagnostics, skip only outputs that pass validation, check free space, limit console logs, disable `NS_LOG` and core dumps, and default to four jobs.

Semantic validation (8 runs):

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v20_startup_handoff/scripts/run_semantic.sh
```

Run the Pareto diagnostic only after semantic validation succeeds (30 runs):

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control
MAX_JOBS=4 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 \
  bash cbap_exp_v20_startup_handoff/scripts/run_pareto_diagnostic.sh
```

Package completed results:

```bash
bash cbap_exp_v20_startup_handoff/scripts/package_results.sh
```
