# Final paper experiment preflight

Status: **PREFLIGHT_READY_NOT_RUN**

- Corrected metric gate: `METRIC_PIPELINE_PASS`.
- Frozen algorithm: `cbap_full_v13_ratefloor_fix`, CC_MODE 25.
- Formal baselines: DCTCP, DCQCN, TIMELY, HPCC-INT, BOP-QB and
  Independent-Min-Grant.
- Static manifest audit: 1408/1408 rows valid.
- Preflight matrix: `fan16_msg256k_load80`, seven algorithms, seed 1.

The preparation stage did not run ns-3. The user starts preflight manually with
`bash cbap_final_paper_experiments/scripts/run_preflight.sh`.
