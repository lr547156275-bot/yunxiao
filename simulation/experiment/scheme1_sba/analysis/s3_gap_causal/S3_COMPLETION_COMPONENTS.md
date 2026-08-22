# S3 COMPLETION COMPONENTS

Same-run pair, W2 = 58.372997 ms.

| component | value | what it is | evidence |
|---|---|---|---|
| tail / CCT component | **1.033590 ms** | `CBAP_max_FCT - DCQCN_max_FCT`, and independently the measured W3 window duration | MEASURED |
| per-flow completion dispersion component | **4.078824 ms** | `(DCQCN_max-DCQCN_mean) - (CBAP_max-CBAP_mean)` = 4.094543 - 0.015719 | DERIVED (identity) |
| physical idle excess | **1.694845 ms** | `8 * (CBAP_deficit - DCQCN_deficit) / C`, deficits 3,420,068 B and 1,301,512 B | DERIVED |
| sum of the first two | **5.112414 ms** | equals the measured mean-FCT gap exactly | DERIVED |

## Permitted statements

- The physical idle excess (1.694845 ms) is **of sufficient magnitude to cover
  the tail component (1.033590 ms)** -- ratio 1.6398, same window, same
  direction.
- Independent corroboration of the idle excess: nanosecond gap time
  2.497446 ms (CBAP) vs 0.736947 ms (DCQCN), difference **1.760499 ms**, within
  4 % of the 1.694845 ms computed from the byte deficit.

## Explicitly NOT claimed

- The physical idle excess does **not** explain the 4.078824 ms dispersion
  component.  That term is an arithmetic property of taking a mean over
  lock-step completions: CBAP finishes all 64 flows within 0.031437 ms of each
  other, DCQCN spreads them over 10.608827 ms, so DCQCN's mean is pulled down by
  early finishers.  It is not a control-delay effect and no idle time is
  attributed to it.
- Covering the tail component in magnitude is not the same as causing it.  No
  causal attribution is made in this round.
