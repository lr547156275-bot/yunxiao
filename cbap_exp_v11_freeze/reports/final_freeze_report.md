RESTRICT_SCOPE_AND_FREEZE

# CBAP-v1.1 final analysis

## Integrity

- Semantic regression: `SEMANTIC_PASS` (11/11).
- Formal runs: 63/63 valid; 0 invalid; 0 missing.
- Increase-policy events: 1988; invariant failures: 0.
- CBAP capacity/credit/pacing violations: 0.
- Victim calibration: `NOT_RUN_0_OF_54` (not used for CBAP performance).
- Statistical unit is scenario + algorithm + seed; packet and epoch rows are diagnostic only.

## E1: one incumbent plus one newcomer

| Metric | Full-v1.1 vs DCQCN | Result |
|---|---:|---|
| New-flow CCT | +8.900% | fails <=5% |
| Peak queue | -20.370% | passes >=15% reduction |
| Queue AUC | -97.916% | passes >=80% reduction |
| Utilization | 93.547% | fails >=95% |

The adaptive increase improves newcomer CCT by 3.077% relative to Full-v1, but does not close the DCQCN gap.

## E2: synchronized batch incast

| Metric | Full-v1.1 vs DCQCN | Result |
|---|---:|---|
| New-batch CCT | -10.878% | improvement |
| Peak queue | -69.686% | passes >=60% reduction |
| Queue AUC | -96.420% | passes >=90% reduction |
| Utilization | 94.991% | passes >=90% |
| New-batch CCT vs HPCC-INT | -1.237% | within 3% |

Full-v1.1 retains the synchronized-batch benefit. Relative to Full-v1 its CCT changes by -0.107% and queue AUC by +15.800%.

## E4 staggered parking lot

- F0 rate at 4/6/8 RTT: 30.429 / 44.552 / 47.500 Gbit/s.
- F0 reaches 40/45/47.5 Gbit/s after 5.409 / 6.611 / 6.611 RTT.
- Simultaneous-active Jain fairness: 0.999316.
- L1/L2 mean utilization: 94.257% / 94.274%.
- Group maximum RCT vs Full-v1: -1.024%.
- Final rate reaches 47.5 Gbit/s; no 25 Gbit/s steady double penalty is observed. The preregistered 4-RTT and 6-RTT recovery thresholds are nevertheless missed.

## E4 synchronous regression

Full-v1.1 is numerically identical to Full-v1 for the retained run metrics: fairness 0.999980, minimum link utilization 95.273%, and peak queue 106896 bytes.

## Interpretation

The data support CBAP-v1.1 only for synchronized multi-flow batch admission. E1 remains slower than DCQCN and staggered E4 misses the registered recovery deadlines, so the scope is restricted rather than introducing a third increase rule.

Three configured seeds are reported, but most controlled runs are deterministic repetitions; they do not establish broad statistical robustness.
