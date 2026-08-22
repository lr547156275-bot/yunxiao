# D4v2 screening (S3, single seed, serial)

Single-seed rule: |diff| < 0.3% vs D1 = TIE_CANDIDATE; multi-seed
paired runs are required before any win/loss claim inside that band.
In-window background degradation is an explicit trade-off, NOT a
retention failure (D1 itself drops to ~3% in-window).

| metric | scr8_d1 | scr8_d3 | scr8_b005 | scr8_b010 | scr8_b020 | scr8_b040 | scr8_b080 |
|---|---|---|---|---|---|---|---|
| status | OK | OK | OK | OK | OK | OK | OK |
| BMAX ratio | - | - | 0.005 | 0.010 | 0.020 | 0.040 | 0.080 |
| CCT (ms) | 58.3730 | 58.4911 | 58.2011 | 58.2367 | 58.2217 | 56.8412 | 58.4757 |
| BCT (ms) | 58.3730 | 58.4862 | 58.1962 | 58.2317 | 58.2167 | 56.8362 | 58.4707 |
| FCT mean (ms) | 54.2785 | 58.4380 | 58.1479 | 58.1834 | 58.1687 | 56.7901 | 58.4226 |
| FCT p95 (ms) | 57.7539 | 58.4456 | 58.1553 | 58.1913 | 58.1769 | 56.8022 | 58.4312 |
| FCT p99 (ms) | 58.1925 | 58.4460 | 58.1556 | 58.1916 | 58.1773 | 56.8026 | 58.4316 |
| batch goodput (G) | 9.1972 | 9.1787 | 9.2244 | 9.2188 | 9.2212 | 9.4451 | 9.1811 |
| total system goodput (G) | 6.1331 | 6.1237 | 6.1246 | 6.1245 | 6.1245 | 6.1286 | 6.1237 |
| bg full (G) | 7.3980 | 7.3862 | 7.3873 | 7.3872 | 7.3872 | 7.3924 | 7.3863 |
| bg full /D1 | 1.0000 | 0.9984 | 0.9986 | 0.9985 | 0.9985 | 0.9992 | 0.9984 |
| bg in-window (G) | 0.2281 | 0.0996 | 0.0997 | 0.0996 | 0.0996 | 0.1001 | 0.0996 |
| bg in-window /D1 | 1.0000 | 0.4366 | 0.4369 | 0.4367 | 0.4367 | 0.4387 | 0.4368 |
| bg outside (G) | 7.6135 | 7.6057 | 7.6057 | 7.6057 | 7.6057 | 7.6057 | 7.6057 |
| bg outside /D1 | 1.0000 | 0.9990 | 0.9990 | 0.9990 | 0.9990 | 0.9990 | 0.9990 |
| bg recovery (ms) | 22.8870 | 0.0488 | 0.0389 | 0.0433 | 0.0383 | 0.0388 | 0.0443 |
| queue mean (B) | 18690 | 23 | 29 | 28 | 30 | 378 | 60 |
| queue p95 (B) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| queue p99 (B) | 967304 | 1048 | 1048 | 1048 | 1048 | 19912 | 2096 |
| queue max (B) | 1279608 | 9432 | 11528 | 13624 | 15720 | 26200 | 29344 |
| qdelay mean (us) | 14.95 | 0.02 | 0.02 | 0.02 | 0.02 | 0.30 | 0.05 |
| qdelay p99 (us) | 773.84 | 0.84 | 0.84 | 0.84 | 0.84 | 15.93 | 1.68 |
| qdelay max (us) | 1023.69 | 7.55 | 9.22 | 10.90 | 12.58 | 20.96 | 23.48 |
| over Q_low (ms) | 53.71 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| over Q_low longest (ms) | 53.71 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| over Q_high (ms) | 44.69 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| over Q_red (ms) | 25.07 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| over Q_abs (ms) | 18.33 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| boost duty (%) | - | - | 0.97 | 0.97 | 0.98 | 0.21 | 1.59 |
| boost mean (G) | - | - | 0.0500 | 0.0997 | 0.1955 | 0.0111 | 0.5457 |
| boost max (G) | - | - | 0.0500 | 0.1000 | 0.2000 | 0.4000 | 0.8000 |
| PFC | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drops | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| retx | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gates | FAIL: qmax=1279608>Q_abs | PASS | PASS | PASS | PASS | PASS | PASS |

## Decision vs D1 (order: completion, goodput, bg, queue)

- **scr8_d3** [PASS]
  - CCT TIE_CANDIDATE(+0.20%), BCT TIE_CANDIDATE(+0.19%), p99 FCT worse(+0.44%)
  - batch goodput TIE_CANDIDATE(-0.20%), total goodput TIE_CANDIDATE(-0.15%)
  - queue p99 1048.0 B vs D1 967304.0 B
- **scr8_b005** [PASS]
  - CCT TIE_CANDIDATE(-0.29%), BCT better(-0.30%), p99 FCT TIE_CANDIDATE(-0.06%)
  - batch goodput TIE_CANDIDATE(+0.30%), total goodput TIE_CANDIDATE(-0.14%)
  - queue p99 1048.0 B vs D1 967304.0 B
- **scr8_b010** [PASS]
  - CCT TIE_CANDIDATE(-0.23%), BCT TIE_CANDIDATE(-0.24%), p99 FCT TIE_CANDIDATE(-0.00%)
  - batch goodput TIE_CANDIDATE(+0.23%), total goodput TIE_CANDIDATE(-0.14%)
  - queue p99 1048.0 B vs D1 967304.0 B
- **scr8_b020** [PASS]
  - CCT TIE_CANDIDATE(-0.26%), BCT TIE_CANDIDATE(-0.27%), p99 FCT TIE_CANDIDATE(-0.03%)
  - batch goodput TIE_CANDIDATE(+0.26%), total goodput TIE_CANDIDATE(-0.14%)
  - queue p99 1048.0 B vs D1 967304.0 B
- **scr8_b040** [PASS]
  - CCT better(-2.62%), BCT better(-2.63%), p99 FCT better(-2.39%)
  - batch goodput better(+2.69%), total goodput TIE_CANDIDATE(-0.07%)
  - queue p99 19912.0 B vs D1 967304.0 B
- **scr8_b080** [PASS]
  - CCT TIE_CANDIDATE(+0.18%), BCT TIE_CANDIDATE(+0.17%), p99 FCT worse(+0.41%)
  - batch goodput TIE_CANDIDATE(-0.18%), total goodput TIE_CANDIDATE(-0.15%)
  - queue p99 2096.0 B vs D1 967304.0 B
