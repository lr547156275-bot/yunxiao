# S3 mean-FCT gap decomposition

## Arithmetic check (as specified)

```
CBAP  mean = 59.390868 ms   max = 59.406587 ms   min = 59.375150 ms   std = 0.009218 ms
DCQCN mean = 54.278454 ms   max = 58.372997 ms   min = 47.764170 ms   std = 2.509897 ms

d_mean               = 59.390868 - 54.278454 = 5.112414 ms
tail_component       = 59.406587 - 58.372997 = 1.033590 ms
dispersion_component = (58.372997-54.278454) - (59.406587-59.390868)
                     = 4.094543 - 0.015719   = 4.078824 ms
sum                  = 1.033590 + 4.078824   = 5.112414 ms   EXACT
```

The identity closes to the last digit: **20.22 % tail**, **79.78 % dispersion**.
Independent corroboration: W3_CBAP_TAIL measured from the flow records is
**1.033590 ms**, identical to tail_component.

## H1 - ~80 % of the gap is CBAP lock-step completion  ->  CONFIRMED, HIGH

Supporting:
- dispersion_component = 4.078824 ms = **79.78 %** of d_mean.
- CBAP FCT spread max-min = **0.031437 ms** over 64 flows; std 0.009218 ms;
  CV 0.000155.
- DCQCN FCT spread max-min = **10.608827 ms**; std 2.509897 ms; CV 0.046241.
- DCQCN min FCT 47.764170 ms is **11.611 ms earlier** than CBAP min 59.375150 ms.
- completion skew: CBAP 0.031437 ms vs DCQCN 10.608827 ms (**338x**).

Contradicting: none found.

Note: equal-size flows finishing together is the intended SBA behaviour, so
"dispersion" is a property of the arithmetic mean here, not evidence of DCQCN
unfairness.  No causal claim beyond the measured spread is made.

## H2 - ~20 % from service rate / utilisation / convergence  ->  CONFIRMED, HIGH

Supporting (W2 COMMON_OVERLAP, link 84:1, both arms DERIVED from tx_bytes_delta):
- served wire mean: CBAP **9.576401** vs DCQCN **9.878142** Gbps (-3.05 %).
- utilisation mean: CBAP **0.957640** vs DCQCN **0.987814**.
- samples below 95 % utilisation: CBAP **25.88 %** vs DCQCN **9.06 %** (2.86x).
- service deficit vs an ideal full link: CBAP **4.2245 %** vs DCQCN **1.2067 %**.
- served bytes in W2: CBAP 69,883,784 vs DCQCN 72,085,744 (**-2,201,960 B**).
- idle fraction **0.000000** for both arms: the shortfall is rate, not idleness.

Contradicting: in W3 the CBAP tail still runs at **0.958956** utilisation, so the
tail is not a stalled link - it is 1.03 ms of residual work at ~96 % of line rate.

## H3 - released background capacity not fully converted  ->  PARTLY, MEDIUM

Supporting:
- CBAP holds background flow 0 at MIN_RATE for **99.69 %** of W2; overlap mean
  rate **0.106291** Gbps.
- DCQCN holds it at MIN_RATE only **3.25 %** of W2; overlap mean **1.196825** Gbps.
- CBAP therefore frees ~1.09 Gbps more background capacity inside W2, yet its
  served rate is **0.301741 Gbps lower**.
- Controller state in W2: zone GREEN **100 %**, boost non-zero in **99.65 %** of
  epochs, boost mean **2.257327** Gbps, drain identically **0**.

Contradicting / limits:
- Both arms reach the same p95 served rate (**10.060800** Gbps), so the ceiling is
  identical; the difference lives in the lower tail of the rate distribution.
- The conversion loss cannot be closed from these outputs: DCQCN has no
  port_summary.csv, so arrival-vs-served accounting is unavailable for that arm.

Residual: the 0.301741 Gbps shortfall is **not fully explained**.  What is
established is that it is not idleness (idle=0) and not queue starvation
(CBAP queue mean 23,957 B).  Correlation is reported; causation is not claimed.

## Safety context (the trade-off, not part of the gap)

| metric (W2, link 84:1) | CBAP | DCQCN |
|---|---|---|
| queue mean | **23,957 B** | 960,441 B |
| queue p95 | **46,112 B** | 1,273,320 B |
| queue max | **54,496 B** | 1,279,608 B |
| queue delay max | **43.60 us** | 1023.69 us |
| queue max as % of Q_abs | **5.20 %** | **122.03 %** (over the hard bound) |
| ECN marks | **0** | 6,677 |
| PFC / drops / retx | 0 / 0 / 0 | 0 / 0 / 0 |

DCQCN buys its 5.11 ms with a queue exceeding Q_abs by 22 % and 6,677 ECN marks.
CBAP stays at 5.2 % of Q_abs with zero ECN.

## Section 7 check - UNDERUTILIZED_CONTROLLER

CBAP W2: utilisation mean 0.957640; below 95 % for 25.88 % of samples; queue mean
23,957 B, far under Q_low (524,288 B); boost already non-zero in 99.65 % of epochs
at mean 2.257 Gbps against MAX_BOOST 3.000 Gbps; drain 0.

=> **UNDERUTILIZED_CONTROLLER = TRUE for W2**: the queue sits deep in the safe
zone while the bottleneck runs ~4.2 % under line rate, and the controller is
boosting at only ~75 % of MAX_BOOST.  Headroom is real, so per the stated rule the
controller should continue to boost.
