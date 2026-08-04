# CBAP-v1.5 Guarded Delegation

This directory contains the preregistered, deterministic ns-3 framework for the final CBAP control-mechanism candidate. CBAP-v1.3 (CC_MODE 25) and v1.4 (CC_MODE 26) remain available unchanged; v1.5 uses CC_MODE 27.

The preparation phase does not contain experimental results and does not claim effectiveness. Run semantic validation first. Validation refuses to start unless `reports/guarded_semantic_report.md` begins with `GUARDED_SEMANTIC_PASS`.

Manual workflow from the repository root:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 bash cbap_exp_v15_guarded_delegation/scripts/run_guarded_semantic.sh
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=60 bash cbap_exp_v15_guarded_delegation/scripts/run_guarded_validation.sh
bash cbap_exp_v15_guarded_delegation/scripts/analyze_and_package.sh
```

Each runner supports restart by validating and skipping a directory with `completed.flag`. Failed output is retained.
