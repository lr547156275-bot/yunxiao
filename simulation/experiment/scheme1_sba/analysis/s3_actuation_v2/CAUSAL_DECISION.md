# CAUSAL DECISION

## What the evidence supports

Permitted statement only:
> command cadence and end-to-end effect latency are scale-mismatched, and a
> large number of generations are replaced before taking effect.

## Item 4: D2 split -- the delay is physical, not controller loss

| sub-stage | n | mean | p95 | max | nature |
|---|---|---|---|---|---|
| D2a sender -> bottleneck arrival | 215 | **64,833 ns** | 78,393 | 84,998 | propagation + upstream queueing |
| D2b bottleneck queue -> egress | 215 | **19,689 ns** | 37,341 | 43,150 | egress queueing + serialization |
| D2 total | 215 | **84,522 ns** | 115,130 | 117,779 | |

D2a + D2b are both physical transport terms.  Neither is an
"optimisable control delay": D2a is flight time of data already in the network,
D2b is the bottleneck's own service time.  **76.7 % of D2 is D2a.**

For reference D1 (command -> sender) = 20,223 ns mean, the only stage that is
plausibly software-side.

## Item 5: supersession semantics -- 394 classified

| class | count | fraction of superseded |
|---|---|---|
| `redundant_same_direction` | **339** | 86.04 % |
| `indeterminate` (still pending at run end) | 54 | 13.71 % |
| `harmful_lost_decrease` | **1** | 0.25 % |
| **`harmful_lost_increase`** | **0** | **0.00 %** |
| `safety_correction` | 0 | 0 |

`harmful_lost_increase` -- a rate *increase* overwritten by a *lower* target
while the queue was in the safe zone -- occurs **zero times**.  Attributable
lost bytes from that class: **0 B**.

The 339 `redundant_same_direction` cases are commands superseded by a target in
the same or higher direction: the replacement did not withdraw the increase, so
no increase was lost.

## Item 6: effect-aligned tracking

Over all 11,675 W2 epochs, **every** epoch is `safe_green` (zone GREEN and
q0 < Q_low = 524,288 B).  Of those, **3,021 epochs (25.87 %)** have measured
served rate below 0.99 C.  Integrated shortfall in those epochs:
**6,839,164 B**.

That 6.84 MB exceeds the total measured `B_deficit` of 3.42 MB, because the
per-epoch threshold (0.99 C) is stricter than the deficit integral's (1.00 C
with only positive parts). Both point the same way: the link is persistently a
few percent under line rate while the queue is deep in the safe zone.

## Item 7: is a controller change justified?

The gate was: proceed only if `harmful_lost_increase` explains an observable
excess service deficit **and** aligns in direction and time with the 1.033590 ms
tail gap.

- `harmful_lost_increase` count = **0**
- attributable bytes = **0 B**
- therefore it explains **0 %** of the 2,118,556 B excess deficit

**Conclusion (required wording):**
> Supersession is frequent, but there is no evidence that it is harmful.

`actuator coalescing` is **NOT authorised** by this evidence.  Implementing it
would target a mechanism whose measured harm is zero.

## Where the deficit is NOT explained

Established negatives, so the next investigation does not repeat them:
- not idleness: idle fraction = 0.000000
- not queue starvation: queue mean 23,957 B, 100 % of epochs in GREEN
- not a byte-domain error: verified against the writer's own column
- not lost boost commands: harmful_lost_increase = 0
- not GREEN under-boosting per se: boost non-zero in 99.65 % of epochs

Remaining candidates, in the order the data favours:
1. **work conservation / burstiness at 10 us granularity** -- served rate max is
   1.00608 C and mean 0.9576 C with zero idle, which is the signature of
   packet-level gaps rather than a rate-setting error.
2. **per-QP pacing / packetization floor** -- 64 flows each paced at ~136 Mbps
   over 1048 B packets gives an inter-packet gap of ~61 us; sub-packet rate
   resolution cannot be realised inside a 10 us sample.
3. **arrival-side accounting** -- `applied_rate_audit.csv` has
   `actual_arrival_excess_bps` and `rate_clamp_delta_sum_bps` that were not
   examined this round.

None of these is claimed as the cause.

## E. Authorisation

**Not authorised** to implement actuator coalescing.  The evidence closes items
1, 3, 4, 5, 6 but returns a null result on harm, and item 2 leaves all
actuation -> performance links as CROSS_RUN_DIAGNOSTIC.
