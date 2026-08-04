# Implementation report

The final-paper framework is input-, script- and analysis-only. It does not
change simulation C++ or any congestion-control behavior. CBAP-v1.3 remains
CC_MODE 25 with scoped admission, exact-grant pacing and its existing fixed
parameters. BOP-QB remains CC_MODE 15.

The framework reuses the repository's verified star input writer, the verified
two-link parking-lot schema, and the verified 64-host Clos topology/path model.
All algorithm variants of a scenario point to one immutable case blueprint.
Prepared runs record the blueprint and prepared-config hashes separately.

Successful runs invoke
`cbap_final_metric_pipeline/scripts/collect_full_work_metrics.py`; only runs
that pass byte conservation, completion, capacity, credit, pacing, input-hash
and finite-value checks receive `completed.flag`. Failed attempts are retained.

No ns-3 experiment was run while creating this framework.
