# Round-Safe HPCC

## Feedback semantics

RS-HPCC reuses the persistent-QP round machinery and mode 13. An ACK is
assigned to its origin round using `ack.seq - 1` and the QP's contiguous
sequence intervals.

- `ACTIONABLE_CURRENT` invokes the original `HandleAckHp` and also updates the
  read-only RS estimator.
- `LATE_SAME_ROUND` updates the estimator but cannot update live rate.
- `STALE_OLDER_ROUND` is diagnostic only and cannot update live rate or the
  estimator used by a later release.

At release of round `k`, an estimator sample is eligible only when its origin
is exactly `k-1` and its arrival precedes the release event. Round zero starts
at the same line rate as original HPCC.

## State and units

The selected INT bottleneck hop supplies queue bytes, capacity in bit/s,
normalized load, and a wrapped nanosecond sample timestamp. Selection follows
HPCC's maximum normalized-load hop; queue breaks a tie. The timestamp is
unwrapped to the most recent value not later than ACK arrival.

Feedback delay is ACK arrival minus the origin round's actual release time.
The per-QP EWMA uses `RS_FEEDBACK_EWMA_ALPHA`. Delay fallback order is EWMA,
base RTT, then `RS_DEFAULT_FEEDBACK_US`, with its source recorded.

For release time `t`, the residual queue is:

```text
background = RS_BACKGROUND_LOAD_FRACTION * capacity
age        = max(t - queue_sample_time, 0)
q0         = max(q_last - (capacity-background)*age/8, 0)
```

Time is converted to seconds before multiplying by bit/s; division by eight
produces bytes.

## Safety model and solver

The lower ECN threshold and conservative dynamic-PFC threshold are in bytes:

```text
Qsafe = Qecn + RS_QUEUE_SAFE_FRACTION * (Qpfc-Qecn)
```

The generator and runtime require `0 <= Qecn < Qsafe < Qpfc`.
For candidate per-QP rate `r`:

```text
Tinjection(r) = B*8/r
Topen(r)      = min(feedback_delay, Tinjection(r))
excess(r)     = max(N*r + background - capacity, 0)
Qpred(r)      = q0 + excess(r)*Topen(r)/8
```

`B` and `N` come from the current round plan. `N` is an explicit synchronized
collective-runtime prior, not a network inference.

The implementation checks `Qpred` at the minimum, midpoint, and maximum rate
for monotonic nondecrease. It returns line rate when safe, the configured
minimum with an infeasible marker when even that is unsafe, or the largest
safe lower bound after `RS_BISECTION_ITERS` iterations. All fallback and
infeasible decisions remain visible in `rs_round_decisions.csv`.

The selected rate is applied exactly once in `RdmaHw::ReleaseRound`. The live
pacing rate, HPCC current rate, and per-hop HPCC rate states are aligned to
that start rate; HPCC load/history state is retained. Later actionable
feedback uses the unchanged original HPCC controller.
