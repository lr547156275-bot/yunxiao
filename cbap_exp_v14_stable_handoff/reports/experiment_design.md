# Experiment design

The semantic gate has seven seed-1 runs: fan64 1 MiB/load80, fan64 4 MiB/load80,
fan64 1 MiB/load95, a persistent-root diagnostic, a recovery-block diagnostic,
fan64 64 KiB/load80, and a v1.3 4 MiB shadow run. Required, forbidden,
conditional, optional, and shadow-only expectations are preregistered in
`configs/semantic_manifest.csv`.

The reduced deterministic validation has 30 runs: fan32 1 MiB/load80; fan64
64 KiB, 256 KiB, 1 MiB, and 4 MiB/load80; and fan64 1 MiB/load95. Each runs
DCQCN, HPCC-INT, CBAP Init-Only, frozen v1.3, and v1.4 once.

Correctness precedes performance. Handoff state, feedback/stability duration,
rate continuity, packet pacing, single-controller ownership, post-handoff grant
count, applied capacity, credit, and catch-up behavior are audited first. The
performance analyzer preserves all runs and only evaluates the preregistered
thresholds after all 30 are valid.
