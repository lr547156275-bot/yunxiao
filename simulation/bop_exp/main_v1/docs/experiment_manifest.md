# Main-v1 experiment manifest

The formal matrix is generated deterministically in
`config/run_manifest.csv`.

- Main comparison: 15 scenarios × 6 algorithms × 3 seeds = 270 runs.
- Mechanism ablation: 5 scenarios × 2 extra algorithms × 3 seeds = 30 runs.
- Wire fairness: 6 extra run identities × 3 seeds = 18 runs.
- Total: 318 unique `scenario__algorithm__seedN` identifiers.

All scenarios use a 100 Gbit/s shared bottleneck, fixed ECMP paths, 1000-byte
payloads, common ECN/PFC/ACK/INT parameters, same-QP multi-round release, and a
global ACK barrier. There are no primer or background flows. Seed changes only
the deterministic per-flow release jitter; the same scenario and seed produce
identical topology, flows, fixed paths and rounds across algorithms.

The 15 formal cases cover five message sizes, three additional participant
counts, four additional compute gaps, and three heterogeneous distributions.
Each heterogeneous group contains exactly 2 MiB per round; its minimum,
maximum, mean, ratio, coefficient of variation and group payload are recorded
in both the CSV manifest and scenario JSON.

The task file ends at the “Smoke matrix” heading without providing its body.
The retained smoke is therefore a non-paper, seed-1 integration check of the
nine registered modes on `msg_64k_n16_g50`; it does not alter the 318-run
formal manifest.
