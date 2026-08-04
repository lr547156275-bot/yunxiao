# CBAP-v1.4 final deterministic validation analysis

**Overall assessment: MIXED — REVISE OR NARROW THE STABLE-HANDOFF CLAIM.**

The 30/30-run matrix is complete and internally valid, but the results do not support a general RCT-superiority claim for v1.4. They do support a strong queue-reduction claim against DCQCN and HPCC-INT in these deterministic single-seed scenarios.

## Data validity and scope

- Valid runs: 30/30; invalid or missing: 0.
- Scenarios: 6; algorithms per scenario: 5; seed: 1 only.
- All preregistered collective flows and rounds completed; capacity, credit, and CBAP-owned pacing violations are zero.
- PFC event rows are zero for every algorithm and scenario.
- Metrics use the preregistered pending collective only; incumbent traffic remains real network load.
- This is deterministic ns-3 evidence, not a multi-seed confidence interval or deployment result.

## Stable-handoff coverage

Handoff occurred in 3/6 scenarios: fan64_msg1m_load80, fan64_msg1m_load95, fan64_msg4m_load80. The other cases completed before satisfying the unchanged eligibility predicate.

| Scenario | Handoff | Time (us) | Remaining | Queue at handoff (B) | Reason |
|---|---:|---:|---:|---:|---|
| fan32_msg1m_load80 | 0 | 0.000 | 0.05% | 54552 | completed_before_handoff |
| fan64_msg1m_load80 | 1 | 7295.001 | 50.76% | 0 | none |
| fan64_msg1m_load95 | 1 | 3260.001 | 96.92% | 1048 | none |
| fan64_msg256k_load80 | 0 | 0.000 | 0.05% | 50304 | completed_before_handoff |
| fan64_msg4m_load80 | 1 | 7295.001 | 87.69% | 0 | none |
| fan64_msg64k_load80 | 0 | 0.000 | 0.82% | 72992 | completed_before_handoff |

## v1.4 compared with v1.3

| Scenario | RCT change | Queue-max change | Queue-AUC change | Goodput change |
|---|---:|---:|---:|---:|
| fan32_msg1m_load80 | 0.00% | 0.00% | 0.00% | 0.00% |
| fan64_msg1m_load80 | 2.29% | 92.15% | 37.96% | -2.24% |
| fan64_msg1m_load95 | 2.43% | 98.41% | 79.13% | -2.37% |
| fan64_msg256k_load80 | 0.00% | 0.00% | 0.00% | 0.00% |
| fan64_msg4m_load80 | -18.85% | 141.74% | 29.36% | 23.23% |
| fan64_msg64k_load80 | 0.00% | 0.00% | 0.00% | 0.00% |

The non-handoff cases are bit-for-bit equal in these aggregate metrics. Stable handoff improves 4 MiB RCT by 18.85% and goodput by 23.23%, but raises peak queue by 141.74%. In both 1 MiB handoff cases, RCT regresses by 2.29–2.43% while peak queue rises by 92.15–98.41%; those two cases do not justify the handoff on the measured RCT–queue tradeoff.

## External congestion-control baselines

| Scenario | vs DCQCN RCT | vs DCQCN queue | vs HPCC RCT | vs HPCC queue |
|---|---:|---:|---:|---:|
| fan32_msg1m_load80 | -4.76% | -86.55% | 23.11% | -87.09% |
| fan64_msg1m_load80 | 3.96% | -86.04% | 29.85% | -86.58% |
| fan64_msg1m_load95 | 7.10% | -84.98% | 32.27% | -85.57% |
| fan64_msg256k_load80 | -1.20% | -92.85% | 12.65% | -93.13% |
| fan64_msg4m_load80 | 0.21% | -82.43% | 6.28% | -83.12% |
| fan64_msg64k_load80 | 4.61% | -93.15% | 22.88% | -93.42% |

Against DCQCN, v1.4 improves RCT in 2/6 scenarios (1.20% and 4.76%), is nearly tied at 4 MiB (+0.21%), and regresses by 3.96–7.10% in the remaining three. Peak queue is lower in all six by 82.43–93.15%. Against HPCC-INT, v1.4 RCT is worse in all six by 6.28–32.27%, while peak queue is lower by 83.12–93.42%.

## Interpretation

1. The stable-handoff implementation works causally and preserves its safety audits.
2. Its clearest benefit is recovering long-message throughput relative to continuously controlled v1.3.
3. The same handoff is not beneficial in the two measured 1 MiB cases and gives up much of v1.3's queue advantage.
4. HPCC-INT remains the RCT leader in all six scenarios; v1.4 occupies a lower-queue, higher-RCT operating point.
5. Init-Only applied-rate excess is retained as an ablation outcome because that mode intentionally stops ongoing CBAP capacity enforcement.

## What can and cannot be claimed

Supported: v1.4 is correctly implemented; it sharply reduces peak queue versus DCQCN/HPCC-INT; and it repairs the v1.3 long-message throughput/RCT penalty in the 4 MiB case.

Not supported: universal RCT improvement, superiority to HPCC-INT, multi-seed stability, production performance, or a general benefit from stable handoff at all message sizes. No parameter change should be selected from these same results.

## Recommended next decision

Treat v1.4 as a mixed result. Preserve the validated implementation and report the 4 MiB recovery honestly, but revise or narrow the stable-handoff claim before a paper-level general-performance claim. Any new eligibility rule must be preregistered and evaluated on new runs, not chosen retrospectively from this matrix.
