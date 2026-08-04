# BOP-QB main-v2 baseline audit

Main-v2 corrects experiment semantics without changing frozen algorithms or
main-v1 results. The formal corpus is 273 reusable runs: 225 primary runs, 30
ablation runs, and 18 wire-fairness runs. The 45 historical `pfc_only` runs
are retained separately as an uncontrolled injection reference.

The static PFC audit classifies that mode as `open_loop_no_endhost_cc` because
runtime pause behavior was not verifiable from the old trace. Run
`run_semantic_audit.sh` manually to produce nine event-level diagnostic runs.
This repository-preparation task does not execute the script.
