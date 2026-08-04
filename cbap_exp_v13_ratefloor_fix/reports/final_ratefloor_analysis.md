RATEFLOOR_FIX_VALID_WITH_PERFORMANCE_LIMITATIONS

# Final CBAP v1.3 rate-floor analysis

## Executive result

The execution-layer floor is removed correctly: positive target and applied sums match, applied capacity and pacing violations are zero, zero grants pause DATA, and fan64 no longer locks to 108.9536 Gb/s. The result is performance-limited because high-fan-in CCT regresses even while queues collapse.

## Research-question answers

- RQ1 — Yes. The minimum observed positive low-rate pacing value is 0.696275 Gb/s, below 1.7024 Gb/s.
- RQ2 — Yes. v1.2 has 5950 active fan64 epoch rows at exactly 108.9536 Gb/s; v1.3 has 0.
- RQ3 — Yes. Planner/target follow the live plan and target/applied mismatch rows are 0.
- RQ4 — Yes. Post-application capacity violations are 0.
- RQ5 — Yes. Exact packet-gap formula mismatches and pacing violations are 0; the maximum observed low-rate gap is 12.042 us.
- RQ6 — Yes. Zero grant pauses for 15000 ns with 0 DATA sends, then resumes with no duplicate-time catch-up sends.
- RQ7 — Queue peak/AUC improve by at least 69.35%/57.89% across fan64 cases, and recorded incumbent drop improves where it is measurable; CCT nevertheless regresses in all four fan64 cases.
- RQ8 — Fan32 CCT changes by 0.34%, peak queue by 0.00%, and queue AUC by -0.93%, within the fixed regression limits.

## v1.3 versus v1.2

| Scenario | CCT Δ% | Peak queue Δ% | Queue AUC Δ% | Utilization Δ% |
|---|---:|---:|---:|---:|
| fan32_msg1m_load80 | 0.34 | 0.00 | -0.93 | 0.01 |
| fan64_msg1m_load80 | 43.89 | -92.63 | -92.70 | 47.03 |
| fan64_msg256k_load80 | 30.40 | -86.72 | -80.36 | 49.21 |
| fan64_msg4m_load80 | 48.03 | -92.63 | -94.04 | 40.90 |
| fan64_msg64k_load80 | 17.17 | -69.35 | -57.89 | 1.05 |

Negative queue changes are improvements. CCT uses pending collective flows from application-ready time and includes the fixed scope-decision delay.

## v1.3 versus external baselines

| Scenario | Baseline | CCT Δ% | Peak queue Δ% | Queue AUC Δ% |
|---|---|---:|---:|---:|
| fan32_msg1m_load80 | dctcp | 33.38 | -86.55 | -81.90 |
| fan32_msg1m_load80 | dcqcn | -4.76 | -86.55 | -60.49 |
| fan32_msg1m_load80 | hpcc_int | 23.11 | -87.09 | 26.06 |
| fan64_msg1m_load80 | dctcp | 37.06 | -92.73 | -89.41 |
| fan64_msg1m_load80 | dcqcn | 1.64 | -92.73 | -70.57 |
| fan64_msg1m_load80 | hpcc_int | 26.95 | -93.02 | -30.39 |
| fan64_msg256k_load80 | dctcp | 33.12 | -92.85 | -92.82 |
| fan64_msg256k_load80 | dcqcn | -1.20 | -92.85 | -83.09 |
| fan64_msg256k_load80 | hpcc_int | 12.65 | -93.13 | -79.16 |
| fan64_msg4m_load80 | dctcp | 42.17 | -92.73 | -85.05 |
| fan64_msg4m_load80 | dcqcn | 23.49 | -92.73 | -47.62 |
| fan64_msg4m_load80 | hpcc_int | 30.96 | -93.02 | 168.59 |
| fan64_msg64k_load80 | dctcp | 28.82 | -93.15 | -88.96 |
| fan64_msg64k_load80 | dcqcn | 4.61 | -93.15 | -88.10 |
| fan64_msg64k_load80 | hpcc_int | 22.88 | -93.42 | -89.79 |

## Control overhead versus v1.2

| Scenario | v1.2 bytes | v1.3 bytes | Change % |
|---|---:|---:|---:|
| fan32_msg1m_load80 | 2527008 | 2530512 | 0.14 |
| fan64_msg1m_load80 | 4738944 | 6256944 | 32.03 |
| fan64_msg256k_load80 | 2170752 | 2441088 | 12.45 |
| fan64_msg4m_load80 | 15016992 | 21613440 | 43.93 |
| fan64_msg64k_load80 | 1522560 | 1563072 | 2.66 |

## Correctness totals

- Floor clamps: 0.
- Target/applied mismatch rows: 0.
- Applied capacity violations: 0.
- Pacing violations: 0.
- Fan64 v1.3 fixed-108.9536-Gb/s rows: 0.
- Fan32 CCT change: 0.34%.
- Fan32 peak/AUC changes: 0.00% / -0.93%.

## Limitations

- One deterministic seed per reduced combination; no confidence intervals.
- Whole-simulation mean utilization is sensitive to early completion and is not active-window utilization.
- The fix removes unsafe floor clamping but does not guarantee CCT superiority.
- High-fan-in results show a pronounced queue–CCT tradeoff.
- No parameter changes or new controller were introduced.
