# CBAP-v1.1 implementation report

## Implementation

The implementation retains CBAP-v1 and adds a policy selector inside the
single existing increase branch. It records every actual RATE_INCREASE with
identity, candidates, selected delta, bounds, stability, feedback age and
limiting link. Rate-transition output additionally exposes the already
existing protection floor and rebalance interval for freeze analysis.

Modified shared source files:

- `simulation/src/point-to-point/model/rdma-hw.h`: policy/config and audit
  record declarations.
- `simulation/src/point-to-point/model/rdma-hw.cc`: adaptive candidate choice
  and audit population.
- `simulation/scratch/third.cc`: config parsing/validation and CSV output.

No QP, queue, switch, PFC, ECN, BOP-QB, admission, pacing, feedback freshness,
decrease, progressive-fill or credit code was modified.

## Generated experiment framework

- Semantic regression: 11 seed-1 runs.
- Freeze validation: 63 runs over E1, E2, E4 staggered and E4 synchronous.
- Victim calibration: a frozen 54-run grid. SA–SB capacity is generated above
  aggregate access capacity; the actual candidate is selected only from
  DCQCN/PFC pathology criteria, before any CBAP result.

All runners are resumable, disk guarded, log bounded, and retain failures.
The formal runner refuses to start without `SEMANTIC_PASS`. No runner was
executed in this implementation stage.

## Verification

Static tests compare protected function bodies to the pre-change snapshot,
check both formulas and identities, validate 11/63/54 manifests, verify victim
topology capacity, and confirm BOP-QB mode 15. Incremental build succeeds with
the repository's existing Python 2/waf toolchain.
