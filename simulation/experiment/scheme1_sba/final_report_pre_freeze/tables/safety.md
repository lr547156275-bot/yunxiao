# Safety and bounded oversubscription

A run that exceeds Qmax is only a failure if the excess is unbounded or unrecoverable.  SAFE requires all of: no PFC, no drop, no retransmission, the queue draining back below Qmin, a finite recovery time, and no goodput regression.

| scenario | algorithm | >Qmax % | peak (B) | oversub peak (B) | oversub dur (ms) | drained | PFC | drops | retx | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | DCQCN | 0.00 | 316496 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S1 | DCTCP | 0.00 | 316496 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S1 | TIMELY | 0.00 | 317856 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S1 | HPCC | 0.00 | 282310 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S1 | CBAP-SBA | 0.00 | 14672 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S2 | DCQCN | 40.33 | 1272272 | 872272 | 68.750 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S2 | DCTCP | 40.33 | 1272272 | 872272 | 68.750 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S2 | TIMELY | 40.46 | 1280928 | 880928 | 69.120 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S2 | HPCC | 2.51 | 1291650 | 891650 | 2.890 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S2 | CBAP-SBA | 12.79 | 1263888 | 863888 | 15.700 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S3 | DCQCN | 73.36 | 1272272 | 872272 | 280.040 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S3 | DCTCP | 73.36 | 1272272 | 872272 | 280.040 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S3 | TIMELY | 73.46 | 1280928 | 880928 | 281.520 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S3 | HPCC | 1.80 | 1291650 | 891650 | 2.890 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S3 | CBAP-SBA | 44.67 | 1263888 | 863888 | 86.460 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S6 | DCQCN | 23.55 | 595264 | 195264 | 31.330 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S6 | DCTCP | 23.55 | 595264 | 195264 | 31.330 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S6 | TIMELY | 23.65 | 598752 | 198752 | 31.510 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S6 | HPCC | 0.59 | 591870 | 191870 | 0.630 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S6 | CBAP-SBA | 0.00 | 30392 | 0 | 0.000 | yes | 0 | 0 | 0 | never exceeded Qmax |
| S4 | DCQCN | 91.32 | 1275416 | 875416 | 1120.840 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S4 | DCTCP | 91.32 | 1275416 | 875416 | 1120.840 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S4 | TIMELY | 91.27 | 1285152 | 885152 | 1112.580 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S4 | HPCC | 1.80 | 1291650 | 891650 | 2.890 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S4 | CBAP-SBA | 50.49 | 1265984 | 865984 | 104.950 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S5 | DCQCN | 91.71 | 1272272 | 872272 | 1125.210 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S5 | DCTCP | 91.71 | 1272272 | 872272 | 1125.210 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S5 | TIMELY | 91.75 | 1280928 | 880928 | 1131.120 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S5 | HPCC | 0.85 | 1291650 | 891650 | 2.890 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
| S5 | CBAP-SBA | 77.53 | 1263888 | 863888 | 369.440 | yes | 0 | 0 | 0 | **BOUNDED (safe)** |
