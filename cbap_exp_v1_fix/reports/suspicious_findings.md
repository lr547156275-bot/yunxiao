# Suspicious findings

- DETERMINISTIC_REPETITION for 24/28 scenario-algorithm groups; only 4/28 vary across seeds (all varying groups are E2). Input schedules are identical across seeds; the seed affects only stochastic simulation behavior where present.
- Mean sampled utilization slightly above 1 can arise from retained counter-window boundaries; it is not interpreted as physical over-capacity.
- E4 protection-floor values/timestamps were not retained; floor decay is NOT_MEASURED.
- Victim-flow behavior is not tested in this reduced matrix.
- CBAP-Full and Rate-Only are byte-identical in several static scenario metrics; this is disclosed rather than treated as extra seed evidence.
