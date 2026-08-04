SCOPE_REGRESSION_PASS

# Scope regression report

## Input completeness

- Reused result count: 18/18
- Newly executed ns-3 run count: 0
- Original per-run scope checks: PASS

## single_pending overhead decomposition

- DCQCN raw RCT: 351.849000000 us
- Scoped raw RCT: 356.849000000 us
- Scope decision delay: 5.000000000 us
- Raw overhead: 5.000000000 us (1.421064%)
- Network-only scoped RCT: 351.849000000 us
- Network-only relative difference: 0.000000000%
- Unexplained overhead: 0.000000000 us
- Timing tolerance: 0.100 us
- Scope decision: BYPASS
- Grant/credit/tracking/rate-transition count: 0 / 0 / 0 / 0
- single_pending acceptance: PASS

## Other original semantic checks

- batch_incast RCT relative difference: 0.112264970%
- batch_incast queue-max relative difference: 0.000000000%
- batch_incast queue-AUC relative difference: 0.000000000%
- batch_incast acceptance: PASS
- synchronous_parking_lot Jain fairness: 1.000000000
- synchronous_parking_lot min/max rate ratio: 1.000000000
- synchronous_parking_lot acceptance: PASS

## Interpretation

Formal performance analysis continues to use the raw RCT, which includes the fixed 5 us scope-decision delay. Network-only RCT is used only to verify that BYPASS introduces no additional network behavior. The fixed control overhead has not been removed or hidden. This acceptance correction removes a mathematical conflict in the original test specification; it is not result-driven parameter tuning.

## Final status

SCOPE_REGRESSION_PASS
