# INVALID: queue-credit wiring bug — DO NOT USE THESE RESULTS

These 8 cells were produced by a first implementation of the queueing-delay
credit that had three wiring defects. They are retained as evidence of the
defect only, and must not be used for any conclusion about whether the
mechanism works.

Defects, all traceable to one wrong insertion point:

1. Phase latch fired immediately. At the first replan the measured queue was 0,
   which satisfies q <= q_hard_normal (19 000 B), so the link latched into
   NORMAL before the synchronous first-packet burst had formed. The SYNC_BURST
   allowance (86 072 B) was therefore never used, and the burst that followed
   was charged as a NORMAL-phase violation.

2. Drain never took effect. Rows with q = 49 416 B against q_target = 4 749 B
   logged drain_bps = 0 and total_budget/C = 1.0000. The credit/drain result was
   computed inside the handover branch of ReplanCbapSbaMigrationTargets, which
   only runs while a migration is in progress, so the per-epoch capacity path
   (effectiveCapacityBps) continued to use the unmodified capacity.

3. Queue ran away as a direct consequence of (2): with no working drain, the
   granted credit accumulated. S3 peak went 56 592 -> 136 240 B (7.17 RTT),
   exceeding both q_hard_normal (1.00 RTT) and q_hard_startup (4.53 RTT).

What these runs do establish, and what carries forward: the credit path is
reachable and does fill the capacity hole. S3 target=0.25 RTT against legacy
showed mean FCT 87.900 -> 67.470 ms (-23.2%), p99 87.917 -> 67.488 ms (-23.2%),
incast goodput 6.108 -> 7.957 Gbps (+30.3%), with sum(target) > C observed and
credit = 2.000 Gbps (exactly the 0.20*C cap), untruncated. That is why the fix
is to wire the control loop correctly rather than to abandon the mechanism.

No parameter was changed to obtain or to hide any of this: hard_limit, eta,
R_min, MAX_OVERSUB_RATIO, topology, flow files and seed are all as configured.
