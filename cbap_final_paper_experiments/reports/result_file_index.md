# Result file index

Each successful run contains immutable inputs and hashes, `manifest.json`,
`run_meta.json`, raw low-frequency summaries, `result_full_work.json`,
`flow_outcome_ledger.csv`, `metric_provenance.json`, bounded `stdout.log` and
`completed.flag`.

Run roots are `preflight/runs`, `runs_single_bottleneck`,
`runs_release_skew`, `runs_multibottleneck`, `runs_clos`, `runs_randomized` and
`runs_ablation`. Aggregate outputs are under `processed`, figures and their CSV
sources under `figures`, and written interpretation under `reports`.
