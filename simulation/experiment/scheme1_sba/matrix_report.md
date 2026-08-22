# Final matrix (5 algorithms x 6 scenarios, single seed, standard baseline configs)

Baselines run their standard frozen parameters; no threshold was tuned
toward any target gap.  BCT and batch-goodput express one effect.

## S1
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 16 | 16 | 16 | 16 | 16 |
| CCT (ms) | 3.7778 | 3.7778 | 5.2079 | 4.1362 | 3.5839 |
| BCT (ms) | 3.7778 | 3.7778 | 5.2079 | 4.1362 | 3.5789 |
| FCT mean (ms) | 3.7153 | 3.7153 | 5.0218 | 3.9318 | 3.5715 |
| FCT p95 (ms) | 3.7777 | 3.7777 | 5.1727 | 4.1186 | 3.5766 |
| FCT p99 (ms) | 3.7778 | 3.7778 | 5.2079 | 4.1362 | 3.5768 |
| injection_end (s) | 2.003630 | 2.003630 | 2.005195 | 2.004123 | 2.003563 |
| batch goodput (G) | 8.8819 | 8.8819 | 6.4430 | 8.1123 | 9.3625 |
| utilisation | 0.888195 | 0.888195 | 0.644298 | 0.811235 | 0.936249 |
| total goodput (G) | 5.2576 | 5.2576 | 5.2108 | 5.0539 | 5.2529 |
| bg full (G) | 7.6170 | 7.6170 | 7.5488 | 7.3207 | 7.6100 |
| bg recovery (ms) | 0.0022 | 0.0022 | 0.4321 | 0.0238 | 0.0361 |
| queue p99 worst-link (B) | 0 | 0 | 0 | 0 | 0 |
| queue max worst-link (B) | 321736 | 321736 | 304128 | 285580 | 19912 |
| qdelay p99 (us) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| qdelay max (us) | 257.39 | 257.39 | 243.30 | 228.46 | 15.93 |
| samples over Q_abs | 0 | 0 | 0 | 0 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 2100.0/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.04 |
| lease grants | - | - | - | - | 5 |
| veto counts | - | - | - | - | 3:5 |

- mx_s1_dcqcn [baseline, report-only] gates: PASS
- mx_s1_dctcp [baseline, report-only] gates: PASS
- mx_s1_timely [baseline, report-only] gates: PASS
- mx_s1_hpcc [baseline, report-only] gates: PASS
- mx_s1_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: +0.00%
- timely vs dcqcn CCT: +37.85%
- hpcc vs dcqcn CCT: +9.49%
- cbapsba vs dcqcn CCT: -5.13%

## S2
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 64 | 64 | 64 | 64 | 64 |
| CCT (ms) | 15.6422 | 14.3456 | 14.5747 | 15.2073 | 14.2496 |
| BCT (ms) | 15.6422 | 14.3456 | 14.5747 | 15.2073 | 14.2446 |
| FCT mean (ms) | 14.1287 | 14.1492 | 14.2725 | 14.8107 | 14.2023 |
| FCT p95 (ms) | 14.7076 | 14.3335 | 14.4965 | 15.0809 | 14.2191 |
| FCT p99 (ms) | 15.1338 | 14.3413 | 14.5372 | 15.1629 | 14.2198 |
| injection_end (s) | 2.015629 | 2.014262 | 2.014562 | 2.015194 | 2.014237 |
| batch goodput (G) | 8.5805 | 9.3560 | 9.2090 | 8.8259 | 9.4190 |
| utilisation | 0.858047 | 0.935599 | 0.920896 | 0.882587 | 0.941903 |
| total goodput (G) | 5.7117 | 5.7443 | 5.6991 | 5.5224 | 5.7265 |
| bg full (G) | 7.5261 | 7.5696 | 7.5093 | 7.2737 | 7.5459 |
| bg recovery (ms) | 23.4578 | 0.0144 | 0.5853 | 0.0127 | 0.0304 |
| queue p99 worst-link (B) | 0 | 0 | 0 | 0 | 0 |
| queue max worst-link (B) | 1279608 | 1276464 | 1278816 | 1296010 | 20960 |
| qdelay p99 (us) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| qdelay max (us) | 1023.69 | 1021.17 | 1023.05 | 1036.81 | 16.77 |
| samples over Q_abs | 1298 | 1304 | 910 | 127 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 2500.0/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.21 |
| lease grants | - | - | - | - | 30 |
| veto counts | - | - | - | - | 3:30 |

- mx_s2_dcqcn [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s2_dctcp [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s2_timely [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s2_hpcc [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s2_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: -8.29%
- timely vs dcqcn CCT: -6.82%
- hpcc vs dcqcn CCT: -2.78%
- cbapsba vs dcqcn CCT: -8.90%

## S6
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 60 | 60 | 60 | 60 | 60 |
| CCT (ms) | 6.8529 | 6.8537 | 8.2396 | 7.3254 | 6.8652 |
| BCT (ms) | 6.8529 | 6.8537 | 8.2396 | 7.3254 | 6.8602 |
| FCT mean (ms) | 6.7788 | 6.7754 | 6.9900 | 7.1286 | 6.8356 |
| FCT p95 (ms) | 6.8516 | 6.8533 | 8.1987 | 7.2956 | 6.8400 |
| FCT p99 (ms) | 6.8528 | 6.8536 | 8.2175 | 7.3071 | 6.8406 |
| injection_end (s) | 2.006545 | 2.006561 | 2.008227 | 2.007312 | 2.006852 |
| batch goodput (G) | 18.3614 | 18.3592 | 15.2713 | 17.1771 | 18.3286 |
| utilisation | 1.836141 | 1.835917 | 1.527135 | 1.717710 | 1.832858 |
| total goodput (G) | 11.4419 | 11.4744 | 11.3778 | 11.0306 | 11.4369 |
| bg full (G) | 15.1720 | 15.2153 | 15.0865 | 14.6236 | 15.1653 |
| bg recovery (ms) | 8.1271 | 0.0063 | 0.5204 | 0.0146 | 0.0348 |
| queue p99 worst-link (B) | 0 | 0 | 0 | 0 | 0 |
| queue max worst-link (B) | 599456 | 599456 | 591360 | 598410 | 26200 |
| qdelay p99 (us) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| qdelay max (us) | 479.56 | 479.56 | 473.09 | 478.73 | 20.96 |
| samples over Q_abs | 0 | 0 | 0 | 0 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 5000.0/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.18 |
| lease grants | - | - | - | - | 503 |
| veto counts | - | - | - | - | 3:49 |

- mx_s6_dcqcn [baseline, report-only] gates: PASS
- mx_s6_dctcp [baseline, report-only] gates: PASS
- mx_s6_timely [baseline, report-only] gates: PASS
- mx_s6_hpcc [baseline, report-only] gates: PASS
- mx_s6_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: +0.01%
- timely vs dcqcn CCT: +20.23%
- hpcc vs dcqcn CCT: +6.89%
- cbapsba vs dcqcn CCT: +0.18%

## S3
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 64 | 64 | 64 | 64 | 64 |
| CCT (ms) | 58.3730 | 57.2474 | 57.8657 | 60.3267 | 56.8412 |
| BCT (ms) | 58.3730 | 57.2474 | 57.8657 | 60.3267 | 56.8362 |
| FCT mean (ms) | 54.2785 | 56.5838 | 57.2745 | 59.7339 | 56.7901 |
| FCT p95 (ms) | 57.7539 | 57.2032 | 57.8303 | 60.1813 | 56.8022 |
| FCT p99 (ms) | 58.1925 | 57.2402 | 57.8535 | 60.2272 | 56.8026 |
| injection_end (s) | 2.058359 | 2.057194 | 2.057851 | 2.060312 | 2.056820 |
| batch goodput (G) | 9.1972 | 9.3781 | 9.2779 | 8.8994 | 9.4451 |
| utilisation | 0.919725 | 0.937808 | 0.927788 | 0.889939 | 0.944510 |
| total goodput (G) | 6.1331 | 6.1564 | 6.1088 | 5.9181 | 6.1286 |
| bg full (G) | 7.3980 | 7.4270 | 7.3675 | 7.1292 | 7.3924 |
| bg recovery (ms) | 22.8870 | 0.0126 | 0.4943 | 0.0133 | 0.0388 |
| queue p99 worst-link (B) | 967304 | 1218824 | 100320 | 14170 | 19912 |
| queue max worst-link (B) | 1279608 | 1276464 | 1278816 | 1296010 | 26200 |
| qdelay p99 (us) | 773.84 | 975.06 | 80.26 | 11.34 | 15.93 |
| qdelay max (us) | 1023.69 | 1021.17 | 1023.05 | 1036.81 | 20.96 |
| samples over Q_abs | 1833 | 5507 | 910 | 127 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 3000.0/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.21 |
| lease grants | - | - | - | - | 36 |
| veto counts | - | - | - | - | 3:36 |

- mx_s3_dcqcn [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s3_dctcp [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s3_timely [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s3_hpcc [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s3_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: -1.93%
- timely vs dcqcn CCT: -0.87%
- hpcc vs dcqcn CCT: +3.35%
- cbapsba vs dcqcn CCT: -2.62%

## S4
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 64 | 64 | 64 | 64 | 64 |
| CCT (ms) | 59.0692 | 57.3078 | 57.8999 | 60.3407 | 56.8446 |
| BCT (ms) | 59.0692 | 57.3078 | 57.8999 | 60.3407 | 56.8396 |
| FCT mean (ms) | 54.3285 | 56.6146 | 57.2667 | 59.7060 | 56.7931 |
| FCT p95 (ms) | 58.1228 | 57.1672 | 57.8278 | 60.2281 | 56.8062 |
| FCT p99 (ms) | 58.4515 | 57.2067 | 57.8491 | 60.3035 | 56.8067 |
| injection_end (s) | 4.596594 | 4.584171 | 4.612942 | 4.727295 | 4.607152 |
| batch goodput (G) | 9.0888 | 9.3682 | 9.2724 | 8.8973 | 9.4445 |
| utilisation | 0.908884 | 0.936821 | 0.927240 | 0.889733 | 0.944454 |
| total goodput (G) | 6.5074 | 6.5074 | 6.5074 | 6.5074 | 6.5074 |
| bg full (G) | 7.1111 | 7.1111 | 7.1111 | 7.1111 | 7.1111 |
| bg recovery (ms) | 24.7508 | 0.0122 | 0.3801 | 0.0193 | 0.0354 |
| queue p99 worst-link (B) | 410792 | 1134912 | 22176 | 2180 | 17816 |
| queue max worst-link (B) | 1276464 | 1276464 | 1278816 | 1296010 | 28296 |
| qdelay p99 (us) | 328.63 | 907.93 | 17.74 | 1.74 | 14.25 |
| qdelay max (us) | 1021.17 | 1021.17 | 1023.05 | 1036.81 | 22.64 |
| samples over Q_abs | 1590 | 5532 | 911 | 127 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 4607.2/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.01 |
| lease grants | - | - | - | - | 3 |
| veto counts | - | - | - | - | 3:3 |

- mx_s4_dcqcn [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s4_dctcp [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s4_timely [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s4_hpcc [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s4_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: -2.98%
- timely vs dcqcn CCT: -1.98%
- hpcc vs dcqcn CCT: +2.15%
- cbapsba vs dcqcn CCT: -3.77%

## S5
| metric | dcqcn | dctcp | timely | hpcc | cbapsba |
|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK |
| incast done | 64 | 64 | 64 | 64 | 64 |
| CCT (ms) | 230.3722 | 228.6891 | 231.0021 | 241.1236 | 227.2639 |
| BCT (ms) | 230.3722 | 228.6891 | 231.0021 | 241.1236 | 227.2589 |
| FCT mean (ms) | 222.5064 | 227.7395 | 229.8164 | 239.8086 | 227.2194 |
| FCT p95 (ms) | 228.8488 | 228.6120 | 230.9377 | 240.9215 | 227.2375 |
| FCT p99 (ms) | 229.3606 | 228.6360 | 230.9892 | 240.9704 | 227.2378 |
| injection_end (s) | 5.418589 | 5.412007 | 5.446033 | 5.592363 | 5.442822 |
| batch goodput (G) | 9.3218 | 9.3904 | 9.2964 | 8.9062 | 9.4493 |
| utilisation | 0.932180 | 0.939041 | 0.929638 | 0.890615 | 0.944930 |
| total goodput (G) | 6.2086 | 6.2086 | 6.2086 | 6.2086 | 6.2086 |
| bg full (G) | 6.4000 | 6.4000 | 6.4000 | 6.4000 | 6.4000 |
| bg recovery (ms) | 20.9278 | 0.0109 | 0.3779 | 0.0164 | 0.0361 |
| queue p99 worst-link (B) | 1064768 | 1270176 | 119328 | 18530 | 37728 |
| queue max worst-link (B) | 1279608 | 1276464 | 1278816 | 1296010 | 48208 |
| qdelay p99 (us) | 851.81 | 1016.14 | 95.46 | 14.82 | 30.18 |
| qdelay max (us) | 1023.69 | 1021.17 | 1023.05 | 1036.81 | 38.57 |
| samples over Q_abs | 10096 | 22616 | 910 | 127 | 0 |
| PFC | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 |
| zones G/H/D/R (ms) | - | - | - | - | 5442.8/0.0/0.0/0.0 |
| boost duty (%) | - | - | - | - | 0.12 |
| lease grants | - | - | - | - | 36 |
| veto counts | - | - | - | - | 3:36 |

- mx_s5_dcqcn [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s5_dctcp [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s5_timely [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s5_hpcc [baseline, report-only] gates: FAIL: qmax>Q_abs
- mx_s5_cbapsba [candidate] gates: PASS
- dctcp vs dcqcn CCT: -0.73%
- timely vs dcqcn CCT: +0.27%
- hpcc vs dcqcn CCT: +4.67%
- cbapsba vs dcqcn CCT: -1.35%

## Twin byte-regression (slimming must be behaviour-neutral)
- mx_s1_dcqcn vs sh_s1_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s1_cbapsba vs sh_s1_b040: identical (5 files)
- mx_s2_dcqcn vs sh_s2_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s2_cbapsba vs sh_s2_b040: identical (5 files)
- mx_s6_dcqcn vs sh_s6_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s6_cbapsba vs sh_s6_b040: identical (5 files)
- mx_s3_dcqcn vs scr8_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s3_cbapsba vs scr8_b040: identical (5 files)
- mx_s3_hpcc vs hp_s3: identical (5 files)
- mx_s4_dcqcn vs s4v_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s4_cbapsba vs s4v_b040: identical (5 files)
- mx_s5_dcqcn vs s5v_d1: DIFFERS: flow_summary.csv,flow_timing.csv,round_summary.csv
- mx_s5_cbapsba vs s5v_b040: identical (5 files)
