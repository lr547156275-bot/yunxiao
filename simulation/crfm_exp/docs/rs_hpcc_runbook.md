# RS-HPCC runbook

Build and offline tests are safe to run without starting ns-3:

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control/simulation
python2 -m unittest discover -s crfm_exp/tests -p 'test_*.py'
python2 ./waf build -j1
```

The experiment scripts must be started manually. Run Smoke first:

```bash
cd /home/lr/workspace/yunxiao/High-Precision-Congestion-Control/simulation
./crfm_exp/run_rs_smoke.sh
```

It creates six runs under `crfm_exp/rs_runs_smoke`: five algorithms for
`gap_20us`, plus RS-HPCC for `size_256k`.

Only after Smoke passes, run the 24-run seed-1 screening:

```bash
./crfm_exp/run_rs_screening.sh
```

Optional commands:

```bash
./crfm_exp/run_rs_confirm.sh
./crfm_exp/run_rs_oracle.sh
```

Confirm uses seeds 1,2,3 and skips already valid seed-1 runs under
`crfm_exp/rs_runs`. Oracle contains only HPCC, Reset, and RS diagnostic runs.
All scripts default to `JOBS=1`, clear `NS_LOG`, disable core dumps, reject
less than 5 GiB free space, cap `run.log`, validate outputs before compression,
and support `CASES`, `ALGOS`, `SEEDS`, `MIN_FREE_GB`, and `KEEP_RAW`.
