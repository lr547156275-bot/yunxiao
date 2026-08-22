# S3 EXECUTIVE SUMMARY

CBAP-SBA rho=0.90 (migration ON) vs DCQCN baseline, scenario S3,
same topology/flow/link/path/seed/PG, binary 290cb41f.

## Headline

| metric | CBAP rho=0.90 | DCQCN | delta |
|---|---|---|---|
| incast FCT mean (ms) | 59.3908684 | 54.2784536 | +5.1124 |
| incast FCT p95 (ms) | 59.4045909 | 57.669607 | +1.7350 |
| incast FCT p99 (ms) | 59.4060880 | 58.192546 | +1.2135 |
| incast FCT max / CCT (ms) | 59.4065869 | 58.3729970 | +1.0336 |
| incast FCT std (ms) | 0.00921800 | 2.50989655 | -2.5007 |
| completion skew (ms) | 0.03143699 | 10.6088269 | -10.5774 |

## W2 COMMON_OVERLAP (58.372997 ms, link 84:1)

| metric | CBAP | DCQCN |
|---|---|---|
| served wire mean (Gbps) | 9.5764006851 | 9.8781423775 |
| utilisation mean | 0.9576400685 | 0.9878142377 |
| frac samples <95% util | 0.2588215142 | 0.0906132237 |
| service deficit frac | 0.0422450435 | 0.0120672543 |
| idle fraction | 0.0 | 0.0 |
| queue mean (B) | 23956.798903 | 960441.22096 |
| queue max (B) | 54496.0 | 1279608.0 |
| queue max %% of Q_abs | 5.1971485110 | 122.03304484 |
| ECN marks | 0.0 | 6677.0 |

## Background flow 0

| metric | CBAP | DCQCN |
|---|---|---|
| full-run goodput (Gbps) | 7.38281845 | 7.397988 |
| overlap mean rate (Gbps) | 0.10629109 | 1.19682509 |
| overlap frac at MIN_RATE | 0.99691675 | 0.03254539 |

The full-run goodput differs by only 0.2 %, but inside the overlap
window CBAP pins the background flow at MIN_RATE for 99.69 % of the
time versus 3.25 % for DCQCN.  Reporting only the full-run average
would hide that.

## Gap

d_mean = 5.112414 ms = 1.033590 (tail, 20.22 %) + 4.078824
(dispersion, 79.78 %).  Identity closes exactly.  See
S3_GAP_DECOMPOSITION.md.

## Verdict

- CBAP is 9.42 % slower in mean FCT but 256x tighter in spread
  (0.0157 vs 4.0945 ms max-mean).
- CBAP keeps the queue at 5.20 % of Q_abs with zero ECN; DCQCN
  exceeds Q_abs by 22.03 % with 6,677 ECN marks.
- UNDERUTILIZED_CONTROLLER = TRUE in W2: ~4.2 % service deficit
  while the queue is deep in GREEN and boost is at 75 % of MAX_BOOST.
- 38 metrics are MISSING, all from the CBAP/DCQCN telemetry asymmetry;
  none was substituted or zeroed.