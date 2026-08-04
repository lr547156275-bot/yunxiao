# Result file index

## Generated analysis

- `reports/`: integrity, scope, metric definitions, final analysis, ablation, overhead, measured/interpreted separation, and suspicious findings.
- `processed/`: run inventory, deterministic per-run/per-scenario tables, paired comparisons, scaling slices, admission/control/audit tables, and Pareto classification.
- `figures/`: 18 figures, each with PDF, PNG, SVG, and CSV source data.

## Archive inclusion policy

- All reports, processed data, figures, configs, scripts, preflight identity, and available Codex logs.
- Ten required lightweight files from every 18 Scope and 170 Core run.
- All CSV/CSV.GZ traces for every official algorithm in the five predeclared representative scenarios.
- Existing victim calibration report/summary only; `selected_victim_scenario.json` is absent, so victim status is `VICTIM_CALIBRATION_NOT_RUN`.

## Deliberate exclusions

- Build objects, core dumps, unrelated experiments, caches, and large packet traces outside the five representative scenario groups.
- Manual scope/core terminal logs were not present as files and therefore cannot be included. Existing build and analysis logs are included without fabrication.
