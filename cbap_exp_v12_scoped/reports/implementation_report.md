# Implementation report

The implementation adds CC_MODE 24 and a structural dispatcher around the
frozen Full-v1.1 planner. Mode 23 continues to call the old planner directly.
Mode 24 is DCQCN-capable from QP creation; the DCQCN CNP handler is suppressed
only after the scope decision enabled CBAP for that QP. A bypassed QP therefore
keeps its original DCQCN alpha, target rate, timers, and recovery behavior.

New configuration fields are `CBAP_SCOPE_POLICY`, `CBAP_SCOPE_BASE_CC`,
`CBAP_SCOPE_SUMMARY_FILE`, and `CBAP_SCOPE_LINK_FILE`. The two new CSVs expose
batch decisions, per-link counterfactual demand, admission capacity,
oversubscription, causality timestamps, and trigger state.

The scope calculation duplicates only the read-only Full-v1.1 admission
inputs needed for the predicate. ENABLE still calls the original progressive
filling and rate/credit implementation. Existing increase/decrease,
admission-hold, freshness, pacing, queue credit, control epoch, ECN/PFC
threshold, and baseline algorithm code was not replaced.

Generated framework artifacts include 6 scope cases, 23 core cases, manifests
of exactly 18 and 170 unique run IDs, preparation/integrity/analysis scripts,
disk-safe resumable runners, a packaging script, and static tests. No run
directory contains simulated results at delivery time because no ns-3
experiment was executed.

The pre-existing worktree was dirty. Existing modifications were preserved.
The immutable `cbap_exp_v11_freeze/` tree was checked against a complete
pre-change SHA-256 inventory and remained unchanged.
