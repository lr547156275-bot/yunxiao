# Preregistered experiment design

The formal matrix contains 1408 runs: 560 single-bottleneck, 420 release-skew,
56 two-link parking-lot, 140 Clos collective, 210 randomized robustness and 22
additional ablations. The seven formal algorithms are DCTCP, DCQCN, TIMELY,
HPCC-INT, BOP-QB, Independent-Min-Grant and frozen CBAP-v1.3.

Deterministic combinations run once. The robustness matrix uses five seeds that
materially change background timing, newcomer release jitter and the recorded
ECMP hash seed. The seed is not treated as replication unless it changes input.

Primary classification is the preregistered queue–CCT Pareto rule. All-work,
incumbent, utilization, capacity, credit, pacing and control-overhead metrics
must also be reported. Missing or incomplete work is censored, never replaced
with zero.

Clos workloads are deterministic synthetic communication schedules, not GPU,
NCCL or production traces. The framework does not claim dynamic routing or
arbitrary background traffic coverage.
