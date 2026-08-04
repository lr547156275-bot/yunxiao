# Chapter 5 corrected main-v2 result tables

Open-loop is excluded. Best baseline means best formal CC baseline.

| Scenario | Best formal CC | Baseline RCT us | BOP-QB RCT us | RCT change % | Queue change % |
|---|---|---:|---:|---:|---:|
| msg_16k_n16_g50 | DCQCN | 25.79 | 27.52 | 6.70 | -1.24 |
| msg_64k_n16_g50 | DCTCP | 90.99 | 95.90 | 5.39 | -68.50 |
| msg_256k_n16_g50 | DCTCP | 385.70 | 369.35 | -4.24 | -90.27 |
| msg_1m_n16_g50 | DCTCP | 1442.52 | 1464.27 | 1.51 | -90.18 |
| msg_4m_n16_g50 | DCTCP | 5631.23 | 5848.24 | 3.85 | -90.25 |
| n8_64k_g50 | DCQCN | 47.70 | 50.45 | 5.76 | -40.79 |
| n32_64k_g50 | DCTCP | 177.90 | 187.08 | 5.16 | -84.67 |
| n64_64k_g50 | DCTCP | 351.86 | 370.18 | 5.21 | -91.84 |
| gap_0us_n16_64k | DCTCP | 95.61 | 100.19 | 4.79 | -66.34 |
| gap_20us_n16_64k | DCQCN | 91.32 | 96.09 | 5.22 | -68.88 |
| gap_100us_n16_64k | DCTCP | 90.77 | 95.66 | 5.39 | -69.24 |
| gap_500us_n16_64k | DCQCN | 91.01 | 95.90 | 5.38 | -68.79 |
| hetero_equal | DCTCP | 178.81 | 187.54 | 4.88 | -84.46 |
| hetero_mild | DCTCP | 187.39 | 187.56 | 0.09 | -82.42 |
| hetero_strong | DCTCP | 187.28 | 187.73 | 0.24 | -79.78 |

Simultaneous RCT+queue improvements: 1/15.
RCT cost <=3% with queue reduction >=50%: 4/15.
PFC metrics: NA pending event-level audit.