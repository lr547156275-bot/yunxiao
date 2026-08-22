# S3 CAUSAL DECISION (same-run)

## Item 1: canonical ledger, corrected semantics

```
total                   = 609
APPLIED                 = 215
SUPERSEDED              = 340
RIGHT_CENSORED_PENDING  =  54
sum                     = 609   PASS
```

`RIGHT_CENSORED_PENDING` = a command with no sender effect and **no successor**:
the run ended before either could happen.  These are no longer mislabelled as
`SUPERSEDED_BEFORE_EFFECT`.  The 340 now matches the writer counter
(`superseded=340`) and 54 matches `pending=54`, by construction rather than by
coincidence.

## Item 1b: the 340 supersessions by MAGNITUDE

| magnitude class | count | attributable bytes (upper) |
|---|---|---|
| `redundant_dominated` (successor at least as aggressive) | **339** | 0 |
| `lost_decrease` | 1 | ~0 |
| **`lost_increase`** | **0** | **0 B** |

Not one increase was overwritten by a lower successor target.  Supersession
carries **zero attributable lost throughput**.

## Item 3: bottleneck physical busy/idle, per-packet TX_BEGIN/TX_END

Nanosecond union of transmit intervals over the identical W2 window:

| arm | packets | busy_fraction | gap_fraction | gaps | gap mean | served wire |
|---|---|---|---|---|---|---|
| **CBAP** | 66,676 | **0.957198** | **0.042784** | **1,065** | 2,345 ns | 9.576544 Gbps |
| **DCQCN** | 68,800 | **0.987318** | **0.012625** | **497** | 1,482.8 ns | 9.877891 Gbps |

This supersedes the earlier `idle_fraction = 0` statement, which only meant "no
sample window had zero bytes".  At nanosecond resolution the CBAP serializer is
**genuinely idle 4.28 %** of W2, versus 1.26 % for DCQCN: **2.44 ms of real gap
time vs 0.74 ms**, in 1,065 vs 497 separate gaps.

The busy fractions agree with the independently derived served rates to 4
decimals (0.957198 vs 0.957640 utilisation), so the two methods corroborate.

## Item 4: same-window deficit closure

| arm | deficit bytes | deficit frac | mean served |
|---|---|---|---|
| CBAP | 3,420,068 B | 4.6872 % | 9.577550 Gbps |
| DCQCN | 1,301,512 B | 1.7837 % | 9.879327 Gbps |

```
excess_deficit = 3,420,068 - 1,301,512 = 2,118,556 B
excess * 8 / C = 1.694845 ms
tail gap (W3)  = 1.033590 ms
ratio          = 1.6398
```

The excess deficit is **1.64x larger** than the tail gap, i.e. it is more than
sufficient to account for it in magnitude, and it sits in the same window and the
same direction.  Compared **only** against the 1.033590 ms tail component, as
instructed.  No comparison is made against the 4.078824 ms dispersion component,
which is an arithmetic identity of the mean over lock-step completions.

## Item 5: branch decision

- **Branch A** -- CBAP busy_fraction significantly below DCQCN with real TX gaps:
  **TRUE.** 0.957198 vs 0.987318; 1,065 real gaps totalling 2.4972 ms with mean
  2,345 ns. Per the stated rule this localises to **per-QP pacing / packet
  phase**, not to the rate-setting law.
- **Branch B** -- busy fractions equal: **FALSE**, so the residual mean-FCT gap
  is *not* purely lock-step semantics.
- **Branch C** -- unexplained target -> sender/arrival loss in the same run:
  **NOT SUPPORTED.** `lost_increase = 0`, and D1 (command -> sender) is
  20,223 ns mean against a D2 of 84,522 ns that is physical transport.

### Gap-size signature

Mean gap 2,345 ns at 10 Gbps = 2,931 bytes ~= 2.8 packets of 1048 B.  With 64
incast flows each paced near 136 Mbps, one 1048 B packet per flow every ~61 us,
the aggregate is a superposition of 64 independent pacing timers.  Gaps of a few
packet-times are the expected signature of pacing-phase misalignment rather than
of a controller that is asking for too little: the controller's own target was
above C in 100 % of W2 epochs.

**This is a correlation with a mechanism-consistent signature, not a proven
cause.**  No code change is authorised by this round.

## What remains unproven

- That closing the pacing gaps would recover the 1.033590 ms.  The 1.694845 ms
  is an upper bound on what the deficit *could* explain, not a predicted gain.
- The exact split of the 1,065 gaps between per-QP pacing quantisation, packet
  phase alignment, and end-of-batch effects.  `applied_rate_audit.csv` columns
  `rate_clamp_delta_sum_bps` and `actual_arrival_excess_bps` were not examined.

## Prohibitions honoured

No control law, parameter, rho, MAX_BOOST, queue boundary, ECN/PFC threshold,
topology, traffic or seed was modified.  No GREEN deficit-saturation and no
actuator coalescing were implemented.
