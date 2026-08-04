# Experiment design

The scope regression contains six fixed-path, 100 Gbit/s scenarios and three
algorithms, totaling 18 seed-1 runs. Expected scoped outcomes are BYPASS for
`single_pending`, `two_pending_low_demand`, and `no_shared_link`; ENABLE for
`batch_incast`, `two_pending_overload`, and
`synchronous_parking_lot`.

The core deterministic scan contains 23 unique scenarios. The main 20 cross
fan-in 4/8/16/32/64 with 64 KiB/256 KiB/1 MiB/4 MiB at 80% pre-release load.
Three more use fan-in 16 and 1 MiB at 0%, 50%, and 95%. Seven formal algorithms
produce 161 runs. Three representative scenarios each add init-only,
rate-only-v1.1, and unscoped-Full-v1.1, producing nine ablations and 170 runs
overall.

All releases are strict common releases and all paths are fixed. This phase
does not add 200/400 Gbit/s, release skew, Clos, dynamic routing, or random
replicates. The analyzer treats each parameter combination once and rejects a
run when measured pre-release utilization is outside the requested load by
more than two percentage points.

Runtime scripts preserve failed runs, cap stdout at its last 10 MiB, disable
NS_LOG and core dumps, enforce a default 5 GiB free-space guard, default to
four jobs, and resume only by skipping outputs that pass the integrity checker.
