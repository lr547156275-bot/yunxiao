# CBAP-v1 result integrity report

- Semantic status: `SEMANTIC_PASS`
- Expected formal runs: 84
- Valid formal runs: 84
- Invalid formal runs: 0
- Missing formal runs: 0
- Input-hash consistency issues: 0
- Statistical unit: scenario + algorithm + seed.
- Packet/epoch rows are used only to derive run metrics.
- No p-values are reported; three seeds use mean, median, min and max.

## Seed effect

DETERMINISTIC_REPETITION for 24/28 scenario-algorithm groups; only 4/28 vary across seeds (all varying groups are E2). Input schedules are identical across seeds; the seed affects only stochastic simulation behavior where present.
