# S3 ACTUATION DECOMPOSITION

Window: W2 COMMON_OVERLAP = [2.000000000, 2.058372997] s (58.372997 ms).
Units: ns for delays, bytes for deficits, Gbps for rates.

## Two prior conclusions, corrected

1. **"GREEN acceleration is insufficient"** - already withdrawn.  Additionally,
   the evidence I cited for it was itself misstated: `sumR_effective` is
   `link_capacity + boost_effective`, a target ceiling, **not** an aggregate
   sender rate.  "Controller asks for 122 % of line rate" was the wrong reading
   of that field.  See S3_ACTUATION_FIELD_DEFINITIONS.md.

2. **"89.5 us actuation lag is the main cause"** - NOT SUPPORTED and withdrawn.
   That number was `pending_generation` lifetime, not a stage delay.  With real
   stage timestamps the command-to-bottleneck delay is **D3 mean 104,744 ns**,
   and the decomposition below shows the actuation chain is not the binding
   constraint on the service deficit.

## B. Stage timestamps: AVAILABLE

All three stages are present with real per-generation deltas.  No
MISSING_ACTUATION_STAGE_TIMESTAMPS condition.

## C. Stage delays (MEASURED, n = 215 APPLIED generations)

| delay | n | mean | p50 | p95 | max |
|---|---|---|---|---|---|
| **D1** command -> sender effect | 215 | **20,223 ns** | 13,644 | 52,144 | 67,756 |
| **D2** sender -> bottleneck | 215 | **84,522 ns** | 88,449 | 115,130 | 117,779 |
| **D3** command -> bottleneck | 215 | **104,744 ns** | 107,824 | 160,705 | 169,923 |

D2 / D3 = **80.7 %**: the chain is dominated by propagation and queueing of
in-flight data, not by the sender-side command path.

D3 max 169,923 ns < H_guard 175,000 ns: the whole chain fits inside the
configured guard horizon.

## Generation classification (MEASURED, 609 generations)

| class | count | fraction |
|---|---|---|
| APPLIED | 215 | 0.3530 |
| **SUPERSEDED_BEFORE_EFFECT** | **394** | **0.6470** |
| SUPERSEDED_AFTER_EFFECT | 0 | 0 |
| NEVER_OBSERVED | 0 | 0 |
| EXPIRED | 0 | 0 |

Writer end-of-run counters agree: `pending_54`, `inflight_0`,
`unmatched_0`, `superseded_340`, `negative_0`.

## E. Missing-byte integral and counterfactual bounds

`B_deficit = integral(max(0, C - served_wire_rate) dt)` over W2, from real
`tx_bytes_delta`:

| arm | B_deficit | mean served |
|---|---|---|
| CBAP | **3,420,068 B** | 9.5764 Gbps |
| DCQCN | **1,301,512 B** | 9.8781 Gbps |
| **excess (CBAP - DCQCN)** | **2,118,556 B** | |

Serving that excess at line rate takes **1.694845 ms** -- a COUNTERFACTUAL upper
bound on the CCT component attributable to the service shortfall.  For
reference, the measured tail component is 1.033590 ms, i.e. the deficit is large
enough to cover it, but that is a bound, not an attribution.

### Counterfactual ceilings (COUNTERFACTUAL, not predicted gains)

| factor set to zero | upper-bound bytes | as fraction of CBAP B_deficit |
|---|---|---|
| D1 | 5,435,000 | **1.589** |
| D2 | 22,715,000 | **6.642** |

Both exceed 1.0, which means these ceilings are **not binding** and cannot be
used to attribute the deficit.  The construction assumes every nanosecond of
delay is a full-line-rate hole; the measured **idle fraction is 0.000000**, so
that assumption is false and the true recoverable share is far smaller.  These
rows are reported for completeness and must not be read as "D1 explains 159 % of
the gap".

## F. Verdict against the stated decision rules

- D1 explains >= 70 % of missing bytes? **NO.** D1 is only 19.3 % of D3, and its
  counterfactual bound is non-binding.
- D2 dominant and within H_guard? **YES.** D2/D3 = 80.7 %, D3 max 169,923 ns <
  H_guard 175,000 ns.  Per the stated rule this is **not an execution bug**;
  it points at prediction compensation / control lead time.
- SUPERSEDED_BEFORE_EFFECT dominant? **YES, and this is the strongest single
  finding**: 394/609 = **64.70 %** of commands are replaced before they ever
  reach the sender.  The stated rule for this case is to examine update
  frequency, generation replacement, and whether a one-outstanding-target
  discipline is needed.
- Actuation chain explains < 30 %? **Cannot be closed from these data.**  The
  counterfactual bounds are non-binding, so no percentage attribution is
  defensible.  What IS established: the deficit is not idleness (idle = 0) and
  not queue starvation (queue mean 23,957 B, deep inside GREEN).

**Two rules fire simultaneously** (D2-dominant and superseded-dominant).  They
are consistent: commands are issued every 5 us epoch while the chain needs
~105 us to land, so ~2/3 of them are overwritten in flight.

## What is NOT claimed

- No causal attribution of the 0.4236 Gbps service gap to any single stage.
- No claim about the 4.078824 ms dispersion component; that is an arithmetic
  identity of the mean over lock-step completions, not a control-delay effect.
- The 1.033590 ms tail component is *bounded* by the deficit (1.694845 ms) but
  not *explained* by it.
