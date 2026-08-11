# Control mechanism engagement

ENGAGED = the mechanism demonstrably acted.  EXPECTED_NOT_ENGAGED = the scenario keeps this controller's input absent by construction (queue below KMIN), which is a property of the scenario, not a failure.

ECN-active scenarios (ECN/CNP required from DCQCN and DCTCP): s3, s4, s5

| scenario | algorithm | verdict | ECN | CNP | alpha moved | rate reduced | rate increased | INT/feedback rounds |
|---|---|---|---|---|---|---|---|---|
| S1 | DCQCN | EXPECTED_NOT_ENGAGED | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | DCTCP | EXPECTED_NOT_ENGAGED | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | TIMELY | ENGAGED | 0 | 0 | 0 | 16 | 0 | 0 |
| S1 | HPCC | ENGAGED | 0 | 0 | 0 | 16 | 0 | 16 |
| S1 | CBAP-SBA | ENGAGED | 0 | 0 | 16 | 0 | 16 | 0 |
| S2 | DCQCN | ENGAGED | 2271 | 2271 | 64 | 64 | 0 | 0 |
| S2 | DCTCP | ENGAGED | 2271 | 0 | 0 | 64 | 0 | 0 |
| S2 | TIMELY | ENGAGED | 2296 | 0 | 0 | 64 | 0 | 0 |
| S2 | HPCC | ENGAGED | 274 | 0 | 0 | 64 | 0 | 64 |
| S2 | CBAP-SBA | ENGAGED | 1095 | 1095 | 64 | 0 | 64 | 0 |
| S3 | DCQCN | ENGAGED | 9542 | 9542 | 64 | 64 | 0 | 0 |
| S3 | DCTCP | ENGAGED | 9542 | 0 | 0 | 64 | 0 | 0 |
| S3 | TIMELY | ENGAGED | 9655 | 0 | 0 | 64 | 0 | 0 |
| S3 | HPCC | ENGAGED | 274 | 0 | 0 | 64 | 0 | 64 |
| S3 | CBAP-SBA | ENGAGED | 8253 | 8253 | 64 | 0 | 64 | 0 |
| S6 | DCQCN | ENGAGED | 451 | 451 | 60 | 60 | 0 | 0 |
| S6 | DCTCP | ENGAGED | 451 | 0 | 0 | 60 | 0 | 0 |
| S6 | TIMELY | ENGAGED | 454 | 0 | 0 | 60 | 0 | 0 |
| S6 | HPCC | ENGAGED | 24 | 0 | 0 | 61 | 0 | 61 |
| S6 | CBAP-SBA | ENGAGED | 0 | 0 | 60 | 1 | 60 | 0 |
| S4 | DCQCN | ENGAGED | 9582 | 9582 | 64 | 64 | 0 | 0 |
| S4 | DCTCP | ENGAGED | 9582 | 0 | 0 | 64 | 0 | 0 |
| S4 | TIMELY | ENGAGED | 9694 | 0 | 0 | 64 | 0 | 0 |
| S4 | HPCC | ENGAGED | 274 | 0 | 0 | 64 | 0 | 64 |
| S4 | CBAP-SBA | ENGAGED | 8983 | 8983 | 64 | 0 | 64 | 0 |
| S5 | DCQCN | ENGAGED | 38410 | 38410 | 64 | 64 | 0 | 0 |
| S5 | DCTCP | ENGAGED | 38410 | 0 | 0 | 64 | 0 | 0 |
| S5 | TIMELY | ENGAGED | 38862 | 0 | 0 | 64 | 0 | 0 |
| S5 | HPCC | ENGAGED | 274 | 0 | 0 | 64 | 0 | 64 |
| S5 | CBAP-SBA | ENGAGED | 36891 | 36891 | 64 | 0 | 64 | 0 |
