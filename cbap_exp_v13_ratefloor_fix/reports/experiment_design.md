# Experiment design

The semantic matrix contains five deterministic seed-1 runs: v1.2/v1.3 on
fan64 1 MiB, v1.3 on fan64 4 MiB, v1.3 on fan32 1 MiB, and one diagnostic
zero-grant pause/resume case. It validates execution semantics before any
performance matrix is allowed.

The reduced matrix contains five scenarios crossed with DCTCP, DCQCN,
HPCC-INT, v1.2, and v1.3, for 25 deterministic seed-1 runs. Its fixed gates
are encoded in the analyzer. It is a correctness/regression matrix, not a
multi-seed statistical experiment.

Every run copies its own topology, flow, trace, round and controlled-path
inputs, records their hashes, records algorithm/version/floor identity, and
writes the applied-rate and sender-pacing audit contracts.
