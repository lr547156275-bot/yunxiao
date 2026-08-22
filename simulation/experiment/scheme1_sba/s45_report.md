# S4/S5 held-out validation (b040 unmodified from S3)

Note: BCT improvement and batch-goodput improvement are the SAME effect
(fixed batch bytes), reported once, not as two contributions.

## S4
| metric | s4v_d1 | s4v_d3 | s4v_b040 |
|---|---|---|---|
| status | OK | OK | OK |
| incast done/expected | 64 | 64 | 64 |
| CCT (ms) | 59.0692 | 58.4925 | 56.8446 |
| BCT (ms) | 59.0692 | 58.4875 | 56.8396 |
| FCT mean (ms) | 54.3285 | 58.4388 | 56.7931 |
| FCT p95 (ms) | 58.1228 | 58.4468 | 56.8062 |
| FCT p99 (ms) | 58.4515 | 58.4473 | 56.8067 |
| batch goodput (G) | 9.0888 | 9.1785 | 9.4445 |
| utilisation of C | 0.908884 | 0.917846 | 0.944454 |
| total goodput (G) | 6.5074 | 6.5074 | 6.5074 |
| bg full (G) | 7.1111 | 7.1111 | 7.1111 |
| bg in-window (G) | 0.2001 | 0.1005 | 0.1011 |
| bg outside (G) | 7.2030 | 7.2034 | 7.2008 |
| bg recovery (ms) | 24.7508 | 0.0475 | 0.0354 |
| queue mean/p95/p99/max (B) | 10140 | 16 | 230 |
| queue p95 (B) | 0 | 0 | 0 |
| queue p99 (B) | 410792 | 0 | 17816 |
| queue max (B) | 1276464 | 12576 | 28296 |
| qdelay mean (us) | 8.11 | 0.01 | 0.18 |
| qdelay p95 (us) | 0.00 | 0.00 | 0.00 |
| qdelay p99 (us) | 328.63 | 0.00 | 14.25 |
| qdelay max (us) | 1021.17 | 10.06 | 22.64 |
| over Q_low (ms) | 54.43 | 0.00 | 0.00 |
| over Q_high (ms) | 36.34 | 0.00 | 0.00 |
| over Q_red (ms) | 30.19 | 0.00 | 0.00 |
| over Q_abs (ms) | 15.90 | 0.00 | 0.00 |
| zone GREEN/HOLD/DRAIN/RED (ms) | - | - | 4607.2 |
| zone HOLD (ms) | - | - | 0.0 |
| zone DRAIN (ms) | - | - | 0.0 |
| zone RED (ms) | - | - | 0.0 |
| boost duty (%) | - | - | 0.01 |
| boost mean (G) | - | - | 0.1333 |
| boost max (G) | - | - | 0.4000 |
| lease grants | - | - | 3 |
| veto counts | - | - | 3:3 |
| PFC | 0 | 0 | 0 |
| drops | 0 | 0 | 0 |
| retx | 0 | 0 | 0 |

- s4v_d1 [baseline, report-only] gates: FAIL: qmax>Q_abs
- s4v_d3 [candidate] gates: PASS
- s4v_b040 [candidate] gates: PASS
- b040 vs D1: CCT -3.77%, BCT -3.77%, p99 FCT -2.81% (|d|<0.3% = TIE_CANDIDATE)

## S5
| metric | s5v_d1 | s5v_d3 | s5v_b040 |
|---|---|---|---|
| status | OK | OK | OK |
| incast done/expected | 64 | 64 | 64 |
| CCT (ms) | 230.3722 | 233.9551 | 227.2639 |
| BCT (ms) | 230.3722 | 233.9501 | 227.2589 |
| FCT mean (ms) | 222.5064 | 233.9039 | 227.2194 |
| FCT p95 (ms) | 228.8488 | 233.9116 | 227.2375 |
| FCT p99 (ms) | 229.3606 | 233.9119 | 227.2378 |
| batch goodput (G) | 9.3218 | 9.1790 | 9.4493 |
| utilisation of C | 0.932180 | 0.917904 | 0.944930 |
| total goodput (G) | 6.2086 | 6.2086 | 6.2086 |
| bg full (G) | 6.4000 | 6.4000 | 6.4000 |
| bg in-window (G) | 0.1809 | 0.0965 | 0.0969 |
| bg outside (G) | 6.7004 | 6.7094 | 6.7001 |
| bg recovery (ms) | 20.9278 | 0.0449 | 0.0361 |
| queue mean/p95/p99/max (B) | 38759 | 42 | 1176 |
| queue p95 (B) | 0 | 0 | 0 |
| queue p99 (B) | 1064768 | 2096 | 37728 |
| queue max (B) | 1279608 | 9432 | 48208 |
| qdelay mean (us) | 31.01 | 0.03 | 0.94 |
| qdelay p95 (us) | 0.00 | 0.00 | 0.00 |
| qdelay p99 (us) | 851.81 | 1.68 | 30.18 |
| qdelay max (us) | 1023.69 | 7.55 | 38.57 |
| over Q_low (ms) | 222.59 | 0.00 | 0.00 |
| over Q_high (ms) | 210.91 | 0.00 | 0.00 |
| over Q_red (ms) | 186.78 | 0.00 | 0.00 |
| over Q_abs (ms) | 100.96 | 0.00 | 0.00 |
| zone GREEN/HOLD/DRAIN/RED (ms) | - | - | 5442.8 |
| zone HOLD (ms) | - | - | 0.0 |
| zone DRAIN (ms) | - | - | 0.0 |
| zone RED (ms) | - | - | 0.0 |
| boost duty (%) | - | - | 0.12 |
| boost mean (G) | - | - | 0.0111 |
| boost max (G) | - | - | 0.4000 |
| lease grants | - | - | 36 |
| veto counts | - | - | 3:36 |
| PFC | 0 | 0 | 0 |
| drops | 0 | 0 | 0 |
| retx | 0 | 0 | 0 |

- s5v_d1 [baseline, report-only] gates: FAIL: qmax>Q_abs
- s5v_d3 [candidate] gates: PASS
- s5v_b040 [candidate] gates: PASS
- b040 vs D1: CCT -1.35%, BCT -1.35%, p99 FCT -0.93% (|d|<0.3% = TIE_CANDIDATE)

## Aggregate verdict (frozen rule)
- candidate (b040) gates PASS in both scenarios: True
- baseline D1 s4: over Q_abs 15.90 ms, qmax 1276464 B -- baseline violation, reported in the open, never part of any PASS
- baseline D1 s5: over Q_abs 100.96 ms, qmax 1279608 B -- baseline violation, reported in the open, never part of any PASS
- degraded >0.3%: s4=False s5=False; improved >0.3%: s4=True s5=True
- per-scenario CCT deltas: s4=-3.77%, s5=-1.35% (reported separately; the mean below is descriptive only)
- mean CCT improvement: 2.56%

**VERDICT: HELD_OUT_S4_S5_PASS**  (GENERALIZES_ACROSS_SEEDS requires the multi-seed stage)
