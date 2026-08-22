# CORRECTION: random re-phase counterfactual withdrawn

The previous bundle (`analysis/s3_gap_causal/S3_GAP_CAUSAL_DECISION.md`, item 4)
reported an offline counterfactual that preserved per-packet sizes, packet count,
total bytes and window while re-drawing all 66,676 arrival instants uniformly at
random, and reported busy_fraction 0.616275 vs the real 0.957198.

**That conclusion is withdrawn and must not support any statement in the
thesis.**  Reasons:

1. The model is invalid for a saturated serializer.  The real schedule is already
   98.40 % back-to-back; uniform re-drawing destroys the queueing that keeps it
   busy, so the comparison measures the defect in the counterfactual, not a
   property of the scheduler.
2. This round's event-level data supersedes the question it was asked to answer.
   98.74 % of CBAP gap time occurs with an **empty** bottleneck queue, so the
   relevant quantity is arrival timing at the sender, which an offline re-phase
   of bottleneck arrivals cannot represent.

Action taken: `S3_PHASE_COUNTERFACTUAL.csv` and item 4 of the previous decision
document are marked `WITHDRAWN_INVALID_MODEL`.  The raw file is retained for
provenance, not for inference.  No phase-staggering claim -- positive or negative
-- is made anywhere in the current reports.
