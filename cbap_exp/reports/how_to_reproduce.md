# How to reproduce CBAP-v0

From `/home/lr/workspace/yunxiao/High-Precision-Congestion-Control`:

```bash
python3 cbap_exp/tests/test_cbap_model.py
python3 cbap_exp/tests/test_manifest.py
python3 cbap_exp/tests/test_frozen_modes.py

cd simulation
python2 ./waf build
cd ..

MAX_JOBS=1 bash cbap_exp/run_smoke.sh
MAX_JOBS=4 bash cbap_exp/scripts/run_all.sh

python3 cbap_exp/scripts/analyze_results.py --runs cbap_exp/runs
```

The runner is resumable: a run that passes `check_outputs.py` is skipped.
Set `MAX_JOBS` lower for memory-constrained hosts. Formal outputs remain under
`cbap_exp/runs`; smoke outputs are separate under `cbap_exp/runs_smoke`.
No network installation is required. The current completed result set is
147/147 formal runs plus four smoke runs.
