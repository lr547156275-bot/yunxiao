# CBAP-v0 final feasibility report

## Unique decision

**STOP**

This is a simulation feasibility decision under the preregistered four minimal experiments. It is not a deployment claim.

## Integrity

- Valid formal runs: 147/147
- Invalid/missing: 0
- Capacity violations: 0
- Credit violations: 0

## Per-packet algorithm flow

At application readiness the coordinator registers the complete round group. QPs remain in PREPARE while a 5-us planning event uses only completed, delayed port summaries and explicit fixed paths. The batch becomes DATA-eligible at network release.

Before release, the coordinator jointly plans the pending batch from the last delivered port summaries. Per-link equal-weight progressive filling produces base and admission grants; each flow uses the minimum grant on its fixed path. Full CBAP additionally bounds startup excess bytes by one-shot queue credit. DATA carries no new CBAP header. Each packet still obeys the existing QP pacer; Full consumes accumulated base eligibility and then non-refillable batch credit.

## Increase, decrease, hold, and roots

During tracking, each 5-us epoch classifies controlled ports as CLEAR, STABLE, ROOT_CONGESTED, PROPAGATED, or MIXED_OR_UNCERTAIN. Increase is bounded by target, 10%, 2 Gbit/s and NIC rate. Decrease is once to the path-min grant, with a distinct severe-congestion recovery rule. Propagated congestion does not create a second multiplicative penalty. A target within 5% holds. Feedback is delivered after a modeled 5-us delay; stale feedback cannot increase rate or overwrite a newer batch. ROOT requires local overload/growth evidence; pure downstream pause becomes PROPAGATED and inherits the downstream root.

## Direct run means

| Scenario | Subcase | Algorithm | Mean group RCT us | New-batch CCT us | Peak queue B | Utilization | Goodput Gbit/s | ECN | PFC rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| e1_single_old_single_new | default | dcqcn | 6096.330 | 700.366 | 56592.0 | 1.0091 | 96.351 | 0.0 | 0.0 |
| e1_single_old_single_new | default | hpcc_int | 6786.912 | 829.945 | 61040.0 | 0.9466 | 86.888 | 0.0 | 0.0 |
| e1_single_old_single_new | default | bop_qb | 6389.937 | 733.920 | 61040.0 | 1.0014 | 91.923 | 0.0 | 0.0 |
| e1_single_old_single_new | default | independent_min_grant | 6696.784 | 837.002 | 1048.0 | 0.9244 | 88.185 | 0.0 | 0.0 |
| e1_single_old_single_new | default | cbap_init_only | 6101.330 | 705.366 | 56592.0 | 1.0096 | 96.309 | 0.0 | 0.0 |
| e1_single_old_single_new | default | cbap_rate_only | 6696.784 | 837.002 | 1048.0 | 0.9244 | 88.185 | 0.0 | 0.0 |
| e1_single_old_single_new | default | cbap_full | 8009.560 | 2607.738 | 1048.0 | 0.8654 | 82.564 | 0.0 | 0.0 |
| e2_batch_incast | default | dcqcn | 36003.266 | 5033.820 | 601552.0 | 0.7144 | 68.174 | 203.7 | 0.0 |
| e2_batch_incast | default | hpcc_int | 28543.162 | 4509.519 | 500310.0 | 0.9459 | 86.795 | 6.3 | 0.0 |
| e2_batch_incast | default | bop_qb | 27016.994 | 4402.840 | 627840.0 | 1.0020 | 91.946 | 1895.0 | 0.0 |
| e2_batch_incast | default | independent_min_grant | 27497.227 | 4557.637 | 10480.0 | 0.9483 | 90.478 | 0.0 | 0.0 |
| e2_batch_incast | default | cbap_init_only | 28196.427 | 9038.430 | 266192.0 | 1.0100 | 96.367 | 0.0 | 0.0 |
| e2_batch_incast | default | cbap_rate_only | 27497.227 | 4557.637 | 10480.0 | 0.9483 | 90.478 | 0.0 | 0.0 |
| e2_batch_incast | default | cbap_full | 39943.753 | 19494.047 | 11528.0 | 0.7919 | 75.561 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | dcqcn | 6968.745 | 2791.225 | 248376.0 | 0.5256 | 120.415 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | hpcc_int | 7736.864 | 3141.868 | 173310.0 | 0.4940 | 108.838 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | bop_qb | 7304.290 | 2925.461 | 110090.0 | 0.5214 | 114.882 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | independent_min_grant | 7397.309 | 2972.352 | 4192.0 | 0.4958 | 113.530 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | cbap_init_only | 6973.745 | 2796.225 | 248376.0 | 0.5256 | 120.361 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | cbap_rate_only | 7397.309 | 2972.352 | 4192.0 | 0.4958 | 113.530 | 0.0 | 0.0 |
| e3_victim_flow | pfc_off | cbap_full | 7405.931 | 2972.352 | 4192.0 | 0.4952 | 113.364 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | dcqcn | 6968.745 | 2791.225 | 248376.0 | 0.5256 | 120.415 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | hpcc_int | 7736.864 | 3141.868 | 173310.0 | 0.4940 | 108.838 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | bop_qb | 7304.290 | 2925.461 | 110090.0 | 0.5214 | 114.882 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | independent_min_grant | 7397.309 | 2972.352 | 4192.0 | 0.4958 | 113.530 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | cbap_init_only | 6973.745 | 2796.225 | 248376.0 | 0.5256 | 120.361 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | cbap_rate_only | 7397.309 | 2972.352 | 4192.0 | 0.4958 | 113.530 | 0.0 | 0.0 |
| e3_victim_flow | pfc_on | cbap_full | 7405.931 | 2972.352 | 4192.0 | 0.4952 | 113.364 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | dcqcn | 11146.185 | n/a | 0.0 | 0.4204 | 96.333 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | hpcc_int | 12331.340 | n/a | 0.0 | 0.3952 | 87.074 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | bop_qb | 11683.067 | n/a | 0.0 | 0.4172 | 91.906 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | independent_min_grant | 11822.265 | n/a | 0.0 | 0.3967 | 90.824 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | cbap_init_only | 11151.185 | n/a | 0.0 | 0.4205 | 96.289 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | cbap_rate_only | 11822.265 | n/a | 0.0 | 0.3967 | 90.824 | 0.0 | 0.0 |
| e3_victim_flow | victim_alone | cbap_full | 11839.510 | n/a | 0.0 | 0.3962 | 90.691 | 0.0 | 0.0 |
| e4_parking_lot | staggered | dcqcn | 10732.962 | n/a | 111088.0 | 1.0090 | 173.417 | 0.0 | 0.0 |
| e4_parking_lot | staggered | hpcc_int | 10490.990 | n/a | 113360.0 | 0.9463 | 156.303 | 0.0 | 0.0 |
| e4_parking_lot | staggered | bop_qb | 11254.518 | n/a | 112270.0 | 1.0014 | 165.447 | 0.0 | 0.0 |
| e4_parking_lot | staggered | independent_min_grant | 10642.817 | n/a | 1048.0 | 0.9302 | 159.720 | 0.0 | 0.0 |
| e4_parking_lot | staggered | cbap_init_only | 10737.962 | n/a | 113184.0 | 1.0097 | 173.355 | 0.0 | 0.0 |
| e4_parking_lot | staggered | cbap_rate_only | 10642.817 | n/a | 1048.0 | 0.9302 | 159.720 | 0.0 | 0.0 |
| e4_parking_lot | staggered | cbap_full | 21387.368 | n/a | 1048.0 | 0.5822 | 99.980 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | dcqcn | 11148.337 | n/a | 111088.0 | 1.0100 | 144.471 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | hpcc_int | 12368.294 | n/a | 113360.0 | 0.9467 | 130.221 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | bop_qb | 11685.233 | n/a | 107910.0 | 1.0020 | 137.833 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | independent_min_grant | 11824.313 | n/a | 1048.0 | 0.9520 | 136.212 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | cbap_init_only | 11153.337 | n/a | 114232.0 | 1.0092 | 144.406 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | cbap_rate_only | 11824.313 | n/a | 1048.0 | 0.9520 | 136.212 | 0.0 | 0.0 |
| e4_parking_lot | synchronous | cbap_full | 11841.808 | n/a | 1048.0 | 0.9504 | 136.011 | 0.0 | 0.0 |

## Preregistered threshold checks

| Experiment | Requirement | Measured | Status |
|---|---|---:|---|
| E1 | peak queue reduction vs DCQCN >=50% | 98.148% | **PASS** |
| E1 | new-flow FCT increase <=10% | 272.339% | **FAIL** |
| E1 | utilization reduction <=5 percentage points | 14.372 pp reduction | **FAIL** |
| E1 | old-flow drop and <=4 RTT recovery | not directly derivable from retained 20-us flow samples | **NOT_MEASURED** |
| E2 | peak queue reduction >=60% | 98.084% | **PASS** |
| E2 | queue AUC reduction >=50% | 95.279% | **PASS** |
| E2 | new-batch CCT increase <=10% | 287.262% | **FAIL** |
| E2 | old-flow worst throughput-drop improvement >=20 pp | not derivable from retained 20-us flow samples | **NOT_MEASURED** |
| E2 | PFC reduction >=90% or nonzero-to-zero | DCQCN 0; Full 0 events | **NOT_APPLICABLE** |
| E2 | utilization >=90% | 79.192% | **FAIL** |
| E2 | capacity and credit violations =0 | 0 | **PASS** |
| E2 | Full queue >=20% below Independent or removes violations | queue change 10.000%; max oversub 619.317->0.000 Gbit/s | **PASS** |
| E3 | DCQCN/PFC-on must create victim degradation | throughput ratio 0.999993; PFC rows 0 | **SCENARIO_NOT_STRESSFUL** |
| E4 synchronous | Jain >=0.95 | 1.000000 | **PASS** |
| E4 synchronous | both link utilization >=90% | 95.041% minimum mean | **PASS** |
| E4 synchronous | F0/min(F1,F2) >=0.90 | 0.999821 | **PASS** |
| E4 staggered | new F0 must not remain starved | F0/min(F1,F2) goodput 0.243611 | **FAIL** |
| E4 staggered | no long-lived >10% idle capacity | 58.220% minimum mean utilization | **FAIL** |
| Ablation | Full must add value beyond RateOnly | E2 FCT 327.730%, queue 10.000% (Full vs RateOnly) | **FAIL** |

## E1: one incumbent plus one arrival

- Full reduces peak queue by 98.148% versus DCQCN, but increases new-flow FCT by 272.339% and changes sampled utilization by -14.372 percentage points.
- Incumbent overall goodput changes from 93.431 to 80.092 Gbit/s. The predeclared worst 1/5/10/20-us drop and <=4-RTT recovery are not directly measurable from the retained host trace.

## E2: four incumbents plus eight arrivals

- Full reduces peak queue by 98.084% and queue AUC by 95.279%. The eight-flow new-batch CCT rises from 5033.820 to 19494.047 us (+287.262%), and Full utilization is 79.192%.
- Independent admission exceeds its reconstructed budget by up to 619.317 Gbit/s; Full removes it. Full's peak queue is nevertheless +10.000% above Independent.

## E3: victim flow

- DCQCN PFC-on victim throughput divided by victim-alone throughput is 0.999993, and both PFC-on/off have zero PFC events. This is `SCENARIO_NOT_STRESSFUL`; no victim-isolation result is inferred.

## E4: two-bottleneck parking lot

- Synchronous Full: Jain 1.000000, minimum-link utilization 95.041%, F0/min(F1,F2) 0.999821, and flow goodputs 45.356/45.364/45.364 Gbit/s.
- Staggered Full fails: later F0 goodput is 12.394 Gbit/s versus 50.875/50.875 for incumbents, ratio 0.243611; minimum-link utilization is 58.220%. Max group RCT is 21664.107 us versus DCQCN 13931.271 us.


## Ablations

Independent-Min-Grant isolates missing batch coordination; Init-Only hands off to unmodified DCQCN after the first fresh summary; Rate-Only removes one-shot queue credit; Full includes both rate and credit. E2 median new-flow FCT is 9038.332 us for Init-Only, 4557.539 us for Rate-Only, and 19493.949 us for Full. Full is +327.730% slower and has +10.000% higher peak queue than Rate-Only. Exact paired changes are in `processed/paired_comparisons.csv`.

## Control-plane and audits

- Planning and control delay are each 5 us. E2 Full records 4840256 logical control bytes per run on average.
- Capacity violations: 0; credit violations: 0; Full rate/freshness audit errors: 0.
- Full root-link audit: 6 detected true-link rows, 0 false-link rows, 0 propagated-as-root rows. Exact onset latency and epoch recall remain unmeasured.
- Seed-1 bounded traces exist for 49/49 runs. Missing host-side events are disclosed, not synthesized.

## Unfavorable results and limits

Full satisfies queue bounds in E1/E2 and synchronous fairness, but its short-flow cost, underutilization, credit interaction, and staggered starvation directly trigger STOP. All unfavorable values remain in the tables. The experiments cover fixed paths, four minimal topologies, logical out-of-band control and three seeds. They do not establish behavior under dynamic routing, packet spraying, production GPU/NCCL, arbitrary multi-root fabrics or unknown future background traffic.

## Measurement versus interpretation

CSV files contain direct simulation measurements and deterministic run-level derivations. Mechanism explanations above are causal hypotheses consistent with the implementation; the likely rate-plus-credit double gating is not promoted to a proven cause. The unique STOP decision is the preregistered candidate-level judgment, not an industry-wide impossibility result.
