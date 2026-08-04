# Suspicious findings

- 19/21 scenario-algorithm groups have byte-identical `result.json` metrics across three seeds (`DETERMINISTIC_REPETITION`).
- DCQCN sampled utilization can exceed 1.0; it is retained as measured and not clipped.
- Victim calibration is absent and excluded from the decision.
- E1 and E4 recovery failures are retained.
