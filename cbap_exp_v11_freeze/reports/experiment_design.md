# CBAP-v1.1 freeze experiment design

The semantic matrix contains 11 seed-1 runs and gates all later formal runs.
The formal matrix contains 63 run-level samples: E1 18, E2 18, E4 staggered
18, and E4 synchronous 9. Each run is uniquely identified by scenario,
algorithm and seed; packet and epoch rows are never independent samples.

The paired identities are Rate-Only/Full v1 (`legacy_min`) and Rate-Only/Full
v1.1 (`adaptive_max`). DCQCN and HPCC remain external baselines. Three seeds
are summarized only by mean, median, minimum, maximum and paired percentage
difference, with deterministic repetition explicitly flagged.

Victim calibration is independent: contributor count 4/8/16, access rate
50/100 Gbit/s, message 8/32/64 MiB, and three diagnostic identities for 54
seed-1 runs. Every combination is retained. Lowest pressure is selected only
if PFC occurs, victim degradation is at least 10%, PFC-off improves it, the
hot receiver link is the root, and SA–SB is not a capacity bottleneck.
