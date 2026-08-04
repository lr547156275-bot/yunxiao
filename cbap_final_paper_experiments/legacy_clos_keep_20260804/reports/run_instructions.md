# Run instructions

Run from the repository root. First execute preflight and inspect its exit code:

```bash
MAX_JOBS=1 MIN_FREE_GB=5 KEEP_RAW=0 RUN_TIMEOUT_MIN=180 \
  bash cbap_final_paper_experiments/scripts/run_preflight.sh
echo "PREFLIGHT_EXIT=$?"
```

Only after preflight succeeds, run families separately or use
`run_all_final.sh`. Default `MAX_JOBS` is 4; use 1 when memory is constrained.
All scripts are resumable and skip only complete, hash-valid runs.

After all 1408 runs:

```bash
python3 cbap_final_paper_experiments/scripts/analyze_final_results.py
python3 cbap_final_paper_experiments/scripts/generate_paper_figures.py
bash cbap_final_paper_experiments/scripts/package_final_results.sh
```
