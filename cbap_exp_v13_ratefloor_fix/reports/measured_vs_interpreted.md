# Measured versus interpreted

Measured directly: flow completion timestamps, queue samples, QP applied rates, packet gaps, sender byte progress, control messages, ECN/PFC outputs.

Interpreted metrics: pending-collective CCT, queue AUC from 10-us samples, incumbent injection rate from sampled `snd_nxt`, and relative differences.

The reduced matrix has one deterministic seed. It verifies the execution fix and exposes performance tradeoffs, but does not establish statistical generality. `actual_tx_rate_sum_bps` may exceed the applied constraint in a short measurement window because whole packets are counted; it is not substituted for the applied-rate constraint.
