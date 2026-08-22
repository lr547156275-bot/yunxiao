# S3 FULL METRICS

Total rows: 612 (AVAILABLE 574, MISSING 38)

Canonical machine-readable form: `S3_FULL_METRICS.csv`.

## background (35 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `F.bg.fullrun.goodput` | CBAP | W0 | flow 0 | mean | 7.382818457046 | Gbps | MEASURED |
| `F.bg.fullrun.acked` | CBAP | W0 | flow 0 | sum | 1845700000.0 | B | MEASURED |
| `F.bg.completed` | CBAP | W0 | flow 0 | flag | 0 | bool | MEASURED |
| `F.bg.fullrun.goodput` | DCQCN | W0 | flow 0 | mean | 7.397988 | Gbps | MEASURED |
| `F.bg.fullrun.acked` | DCQCN | W0 | flow 0 | sum | 1849497000.0 | B | MEASURED |
| `F.bg.completed` | DCQCN | W0 | flow 0 | flag | 0 | bool | MEASURED |
| `F.bg.old_side.start_rate` | CBAP | W2 | flow0 | value | 8.0 | Gbps | MEASURED |
| `F.bg.old_side.end_rate` | CBAP | W2 | flow0 | value | 0.100096119 | Gbps | MEASURED |
| `F.bg.suppression_depth` | CBAP | W2 | flow0 | ratio | 79.92317863992 | x | DERIVED |
| `F.bg.overlap.rate.min` | CBAP | W2 | flow0 | min | 0.100817014 | Gbps | MEASURED |
| `F.bg.overlap.rate.mean` | CBAP | W2 | flow0 | mean | 0.106291094456 | Gbps | MEASURED |
| `F.bg.overlap.rate.p50` | CBAP | W2 | flow0 | p50 | 0.100817014 | Gbps | MEASURED |
| `F.bg.overlap.rate.p95` | CBAP | W2 | flow0 | p95 | 0.100817014 | Gbps | MEASURED |
| `F.bg.overlap.rate.max` | CBAP | W2 | flow0 | max | 8.0 | Gbps | MEASURED |
| `F.bg.overlap.rate.p5` | CBAP | W2 | flow0 | p5 | 0.100817014 | Gbps | DERIVED |
| `F.bg.overlap.frac_at_min_rate` | CBAP | W2 | flow0 | fraction | 0.996916752312 | ratio | DERIVED |
| `F.bg.overlap.suppression_ratio` | CBAP | W2 | flow0 | ratio | 79.35168561925 | x | DERIVED |
| `F.incast.overlap.rate.min` | CBAP | W2 | incast_flows | min | 0.136593511 | Gbps | MEASURED |
| `F.incast.overlap.rate.mean` | CBAP | W2 | incast_flows | mean | 0.148016874516 | Gbps | MEASURED |
| `F.incast.overlap.rate.p50` | CBAP | W2 | incast_flows | p50 | 0.148041082 | Gbps | MEASURED |
| `F.incast.overlap.rate.p95` | CBAP | W2 | incast_flows | p95 | 0.148041082 | Gbps | MEASURED |
| `F.incast.overlap.rate.max` | CBAP | W2 | incast_flows | max | 0.148041082 | Gbps | MEASURED |
| `F.bg.overlap.rate.min` | DCQCN | W2 | flow0 | min | 0.1 | Gbps | MEASURED |
| `F.bg.overlap.rate.mean` | DCQCN | W2 | flow0 | mean | 1.196825099394 | Gbps | MEASURED |
| `F.bg.overlap.rate.p50` | DCQCN | W2 | flow0 | p50 | 0.263708121 | Gbps | MEASURED |
| `F.bg.overlap.rate.p95` | DCQCN | W2 | flow0 | p95 | 7.460307801 | Gbps | MEASURED |
| `F.bg.overlap.rate.max` | DCQCN | W2 | flow0 | max | 10.0 | Gbps | MEASURED |
| `F.bg.overlap.rate.p5` | DCQCN | W2 | flow0 | p5 | 0.102966438 | Gbps | DERIVED |
| `F.bg.overlap.frac_at_min_rate` | DCQCN | W2 | flow0 | fraction | 0.032545392257 | ratio | DERIVED |
| `F.bg.overlap.suppression_ratio` | DCQCN | W2 | flow0 | ratio | 100.0 | x | DERIVED |
| `F.incast.overlap.rate.min` | DCQCN | W2 | incast_flows | min | 0.1 | Gbps | MEASURED |
| `F.incast.overlap.rate.mean` | DCQCN | W2 | incast_flows | mean | 0.583454604100 | Gbps | MEASURED |
| `F.incast.overlap.rate.p50` | DCQCN | W2 | incast_flows | p50 | 0.154429049 | Gbps | MEASURED |
| `F.incast.overlap.rate.p95` | DCQCN | W2 | incast_flows | p95 | 2.344383941 | Gbps | MEASURED |
| `F.incast.overlap.rate.max` | DCQCN | W2 | incast_flows | max | 10.0 | Gbps | MEASURED |

## completion (44 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `B.incast.count` | CBAP | W1 | incast | count | 64 | flows | MEASURED |
| `B.incast.completed` | CBAP | W1 | incast | count | 64 | flows | MEASURED |
| `B.fct.min` | CBAP | W1 | incast | min | 59.37515000000 | ms | MEASURED |
| `B.fct.mean` | CBAP | W1 | incast | mean | 59.39086849999 | ms | MEASURED |
| `B.fct.p50` | CBAP | W1 | incast | p50 | 59.390619 | ms | MEASURED |
| `B.fct.p90` | CBAP | W1 | incast | p90 | 59.40309399999 | ms | MEASURED |
| `B.fct.p95` | CBAP | W1 | incast | p95 | 59.40459099999 | ms | MEASURED |
| `B.fct.p99` | CBAP | W1 | incast | p99 | 59.40608800000 | ms | MEASURED |
| `B.fct.max` | CBAP | W1 | incast | max | 59.40658699999 | ms | MEASURED |
| `B.fct.std` | CBAP | W1 | incast | std | 0.009218003647 | ms | MEASURED |
| `B.fct.cv` | CBAP | W1 | incast | cv | 0.000155209106 | ratio | DERIVED |
| `B.fct.max_minus_mean` | CBAP | W1 | incast | spread | 0.015718500000 | ms | DERIVED |
| `B.fct.max_minus_min` | CBAP | W1 | incast | spread | 0.031436999999 | ms | DERIVED |
| `B.cct` | CBAP | W1 | incast | batch_completion_time | 59.40658699999 | ms | DERIVED |
| `B.first_finish` | CBAP | W1 | incast | time_s | 2.05937515 | s | MEASURED |
| `B.last_finish` | CBAP | W1 | incast | time_s | 2.059406587 | s | MEASURED |
| `B.completion_skew` | CBAP | W1 | incast | skew_ms | 0.031436999999 | ms | DERIVED |
| `B.goodput.payload` | CBAP | W1 | incast | aggregate | 9.037228683075 | Gbps | DERIVED |
| `B.goodput.wire` | CBAP | W1 | incast | aggregate | 9.471015659862 | Gbps | DERIVED |
| `B.acked_bytes` | CBAP | W1 | incast | sum | 67108864.0 | B | MEASURED |
| `B.jain.goodput` | CBAP | W1 | incast | index | 0.999999975910 | ratio | DERIVED |
| `B.jain.fct` | CBAP | W1 | incast | index | 0.999999975910 | ratio | DERIVED |
| `B.incast.count` | DCQCN | W1 | incast | count | 64 | flows | MEASURED |
| `B.incast.completed` | DCQCN | W1 | incast | count | 64 | flows | MEASURED |
| `B.fct.min` | DCQCN | W1 | incast | min | 47.76417 | ms | MEASURED |
| `B.fct.mean` | DCQCN | W1 | incast | mean | 54.27845368750 | ms | MEASURED |
| `B.fct.p50` | DCQCN | W1 | incast | p50 | 54.301793 | ms | MEASURED |
| `B.fct.p90` | DCQCN | W1 | incast | p90 | 57.130128 | ms | MEASURED |
| `B.fct.p95` | DCQCN | W1 | incast | p95 | 57.669607 | ms | MEASURED |
| `B.fct.p99` | DCQCN | W1 | incast | p99 | 58.192546 | ms | MEASURED |
| `B.fct.max` | DCQCN | W1 | incast | max | 58.37299700000 | ms | MEASURED |
| `B.fct.std` | DCQCN | W1 | incast | std | 2.509896559218 | ms | MEASURED |
| `B.fct.cv` | DCQCN | W1 | incast | cv | 0.046241121268 | ratio | DERIVED |
| `B.fct.max_minus_mean` | DCQCN | W1 | incast | spread | 4.094543312499 | ms | DERIVED |
| `B.fct.max_minus_min` | DCQCN | W1 | incast | spread | 10.60882700000 | ms | DERIVED |
| `B.cct` | DCQCN | W1 | incast | batch_completion_time | 58.37299700000 | ms | DERIVED |
| `B.first_finish` | DCQCN | W1 | incast | time_s | 2.04776417 | s | MEASURED |
| `B.last_finish` | DCQCN | W1 | incast | time_s | 2.058372997 | s | MEASURED |
| `B.completion_skew` | DCQCN | W1 | incast | skew_ms | 10.60882699999 | ms | DERIVED |
| `B.goodput.payload` | DCQCN | W1 | incast | aggregate | 9.197247693141 | Gbps | DERIVED |
| `B.goodput.wire` | DCQCN | W1 | incast | aggregate | 9.638715582412 | Gbps | DERIVED |
| `B.acked_bytes` | DCQCN | W1 | incast | sum | 67108864.0 | B | MEASURED |
| `B.jain.goodput` | DCQCN | W1 | incast | index | 0.997699959170 | ratio | DERIVED |
| `B.jain.fct` | DCQCN | W1 | incast | index | 0.997866321024 | ratio | DERIVED |

## controller (27 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `E.zone.fraction` | CBAP | W2 | zone GREEN | fraction | 1.0 | ratio | MEASURED |
| `E.boost.min` | CBAP | W2 | link0 | min | 0.0 | Gbps | MEASURED |
| `E.boost.mean` | CBAP | W2 | link0 | mean | 2.257326632779 | Gbps | MEASURED |
| `E.boost.p95` | CBAP | W2 | link0 | p95 | 2.378284387 | Gbps | MEASURED |
| `E.boost.max` | CBAP | W2 | link0 | max | 2.483244509 | Gbps | MEASURED |
| `E.boost.frac_nonzero` | CBAP | W2 | link0 | fraction | 0.996488222698 | ratio | DERIVED |
| `E.drain.min` | CBAP | W2 | link0 | min | 0.0 | Gbps | MEASURED |
| `E.drain.mean` | CBAP | W2 | link0 | mean | 0.0 | Gbps | MEASURED |
| `E.drain.p95` | CBAP | W2 | link0 | p95 | 0.0 | Gbps | MEASURED |
| `E.drain.max` | CBAP | W2 | link0 | max | 0.0 | Gbps | MEASURED |
| `E.drain.frac_nonzero` | CBAP | W2 | link0 | fraction | 0.0 | ratio | DERIVED |
| `E.sumR.min` | CBAP | W2 | link0 | min | 10.0 | Gbps | MEASURED |
| `E.sumR.mean` | CBAP | W2 | link0 | mean | 12.25732663277 | Gbps | MEASURED |
| `E.sumR.p95` | CBAP | W2 | link0 | p95 | 12.378284387 | Gbps | MEASURED |
| `E.sumR.max` | CBAP | W2 | link0 | max | 12.483244509 | Gbps | MEASURED |
| `E.sumR.frac_nonzero` | CBAP | W2 | link0 | fraction | 1.0 | ratio | DERIVED |
| `E.pending.frac_nonzero` | CBAP | W2 | link0 | fraction | 0.999657387580 | ratio | MEASURED |
| `E.sumR.frac_above_C` | CBAP | W2 | link0 | fraction | 0.996488222698 | ratio | DERIVED |
| `E.zone.fraction` | DCQCN | W2 | link0 | value |  | various | UNAVAILABLE |
| `E.boost.mean` | DCQCN | W2 | link0 | value |  | various | UNAVAILABLE |
| `E.drain.mean` | DCQCN | W2 | link0 | value |  | various | UNAVAILABLE |
| `E.pending.frac_nonzero` | DCQCN | W2 | link0 | value |  | various | UNAVAILABLE |
| `E.sumR.mean` | DCQCN | W2 | link0 | value |  | various | UNAVAILABLE |
| `E.migration.events` | CBAP | W0 | link0 | count | 674 | count | MEASURED |
| `E.migration.replans` | CBAP | W0 | link0 | count | 376 | count | MEASURED |
| `E.migration.convergence_time` | CBAP | W4_MIGRATION_CONVERGENCE | link0 | duration_ms | 1059.439999999 | ms | DERIVED |
| `E.migration.events` | DCQCN | W0 | link0 | count |  | count | UNAVAILABLE |

## identity (68 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `A.sha.binary` | BOTH | W0 | toolchain | sha256 | 290cb41fec981b | hex | MEASURED |
| `A.sha.libns3` | BOTH | W0 | toolchain | sha256 | c643f5cc332e02 | hex | MEASURED |
| `A.sha.third_cc` | BOTH | W0 | toolchain | sha256 | dd54dee455cbe9 | hex | MEASURED |
| `A.sha.recorder_ml` | BOTH | W0 | toolchain | sha256 | 4b9a4098a6d316 | hex | MEASURED |
| `A.sha.config_cbap` | CBAP | W0 | config | sha256 | 69dbc4159577fc | hex | MEASURED |
| `A.sha.config_dcqcn` | DCQCN | W0 | config | sha256 | 1d936f5b8ec9a8 | hex | MEASURED |
| `A.sha.input.topology.txt` | BOTH | W0 | input | sha256 | 6091d5ec28c391 | hex | MEASURED |
| `A.sha.input.s3_flow.txt` | BOTH | W0 | input | sha256 | 6b922c67e56c04 | hex | MEASURED |
| `A.sha.input.s3_round_schedule.txt` | BOTH | W0 | input | sha256 | 8a40b3d13abe22 | hex | MEASURED |
| `A.sha.input.s3_cbap_link.txt` | BOTH | W0 | input | sha256 | 70903775ca1922 | hex | MEASURED |
| `A.sha.input.s3_cbap_path.txt` | BOTH | W0 | input | sha256 | 1557487d29e7ef | hex | MEASURED |
| `A.cfg.CBAP_MIGRATION_ENABLE` | CBAP | W0 | config | value | 1 | text | MEASURED |
| `A.cfg.CBAP_MIGRATION_ENABLE` | DCQCN | W0 | config | value | ABSENT | text | MEASURED |
| `A.cfg.CBAP_CORE_INITIAL_RELEASE` | CBAP | W0 | config | value | 1 | text | MEASURED |
| `A.cfg.CBAP_CORE_INITIAL_RELEASE` | DCQCN | W0 | config | value | ABSENT | text | MEASURED |
| `A.cfg.CBAP_INITIAL_RELEASE_RATIO` | CBAP | W0 | config | value | 0.90 | text | MEASURED |
| `A.cfg.CBAP_INITIAL_RELEASE_RATIO` | DCQCN | W0 | config | value | ABSENT | text | MEASURED |
| `A.cfg.CBAP_MIGRATION_TRACE` | CBAP | W0 | config | value | 1 | text | MEASURED |
| `A.cfg.CBAP_MIGRATION_TRACE` | DCQCN | W0 | config | value | ABSENT | text | MEASURED |
| `A.cfg.CC_MODE` | CBAP | W0 | config | value | 30 | text | MEASURED |
| `A.cfg.CC_MODE` | DCQCN | W0 | config | value | 1 | text | MEASURED |
| `A.cfg.CBAP_ENABLE` | CBAP | W0 | config | value | 1 | text | MEASURED |
| `A.cfg.CBAP_ENABLE` | DCQCN | W0 | config | value | 0 | text | MEASURED |
| `A.cfg.SIM_SEED` | CBAP | W0 | config | value | 2 | text | MEASURED |
| `A.cfg.SIM_SEED` | DCQCN | W0 | config | value | 2 | text | MEASURED |
| `A.cfg.SIMULATOR_STOP_TIME` | CBAP | W0 | config | value | 3.0 | text | MEASURED |
| `A.cfg.SIMULATOR_STOP_TIME` | DCQCN | W0 | config | value | 3.0 | text | MEASURED |
| `A.cfg.MIN_RATE` | CBAP | W0 | config | value | 100Mb/s | text | MEASURED |
| `A.cfg.MIN_RATE` | DCQCN | W0 | config | value | 100Mb/s | text | MEASURED |
| `A.cfg.CBAP_QC_MAX_BOOST_RATIO` | CBAP | W0 | config | value | 0.30 | text | MEASURED |
| `A.cfg.CBAP_QC_MAX_BOOST_RATIO` | DCQCN | W0 | config | value | 0.30 | text | MEASURED |
| `A.cfg.CBAP_QC_H_GUARD_US` | CBAP | W0 | config | value | 175 | text | MEASURED |
| `A.cfg.CBAP_QC_H_GUARD_US` | DCQCN | W0 | config | value | 175 | text | MEASURED |
| `A.cfg.CBAP_QC_APP_HARD_DELAY_US` | CBAP | W0 | config | value | 838.86 | text | MEASURED |
| `A.cfg.CBAP_QC_APP_HARD_DELAY_US` | DCQCN | W0 | config | value | 838.86 | text | MEASURED |
| `A.cfg.CBAP_QC_SAFETY_MARGIN_BYTES` | CBAP | W0 | config | value | 67072 | text | MEASURED |
| `A.cfg.CBAP_QC_SAFETY_MARGIN_BYTES` | DCQCN | W0 | config | value | 67072 | text | MEASURED |
| `A.cfg.PACKET_PAYLOAD_SIZE` | CBAP | W0 | config | value | 1000 | text | MEASURED |
| `A.cfg.PACKET_PAYLOAD_SIZE` | DCQCN | W0 | config | value | 1000 | text | MEASURED |
| `A.cfg.CBAP_MAX_WIRE_PACKET_BYTES` | CBAP | W0 | config | value | 1064 | text | MEASURED |
| `A.cfg.CBAP_MAX_WIRE_PACKET_BYTES` | DCQCN | W0 | config | value | 1064 | text | MEASURED |
| `A.parsed.realloc` | CBAP | W0 | runtime | echo | CBAP_REALLOC_P | text | MEASURED |
| `A.parsed.realloc` | DCQCN | W0 | runtime | echo | ABSENT | text | MEASURED |
| `A.wall` | CBAP | W0 | run | wall_seconds | 966.475 | s | MEASURED |
| `A.wall` | DCQCN | W0 | run | wall_seconds | 1030.37 | s | MEASURED |
| `A.pg.dist` | BOTH | W0 | traffic | distribution | pg3=65 | count | MEASURED |
| `A.const.C_link` | BOTH | W0 | constant | value | 10000000000.0 | bps/B/us | DERIVED |
| `A.const.payload_packet_bytes` | BOTH | W0 | constant | value | 1000.0 | bps/B/us | DERIVED |
| `A.const.wire_packet_bytes` | BOTH | W0 | constant | value | 1048.0 | bps/B/us | DERIVED |
| `A.const.Q_abs` | BOTH | W0 | constant | value | 1048575.0 | bps/B/us | DERIVED |
| `A.const.Q_red` | BOTH | W0 | constant | value | 981503.0 | bps/B/us | DERIVED |
| `A.const.Q_low` | BOTH | W0 | constant | value | 524287.5 | bps/B/us | DERIVED |
| `A.const.M_safe` | BOTH | W0 | constant | value | 67072.0 | bps/B/us | DERIVED |
| `A.const.MAX_BOOST` | BOTH | W0 | constant | value | 3000000000.0 | bps/B/us | DERIVED |
| `A.const.MIN_RATE_payload` | BOTH | W0 | constant | value | 100000000.0 | bps/B/us | DERIVED |
| `A.const.base_rtt_us` | BOTH | W0 | constant | value | 15.2 | bps/B/us | DERIVED |
| `A.window.W1_CBAP` | BOTH | W1_CBAP | window | start_s | 2.0 | s | DERIVED |
| `A.window.W1_CBAP.end` | BOTH | W1_CBAP | window | end_s | 2.059406587 | s | DERIVED |
| `A.window.W1_CBAP.dur` | BOTH | W1_CBAP | window | duration_ms | 59.40658699999 | ms | DERIVED |
| `A.window.W1_DCQCN` | BOTH | W1_DCQCN | window | start_s | 2.0 | s | DERIVED |
| ... 8 more rows in the CSV | | | | | | | |

## queue (176 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `D.queue.bytes.min` | CBAP | W0 | link84:1 | min | 0.0 | B | MEASURED |
| `D.queue.delay.min` | CBAP | W0 | link84:1 | min | 0.0 | us | DERIVED |
| `D.queue.bytes.mean` | CBAP | W0 | link84:1 | mean | 474.2043273477 | B | MEASURED |
| `D.queue.delay.mean` | CBAP | W0 | link84:1 | mean | 0.379363461878 | us | DERIVED |
| `D.queue.bytes.p50` | CBAP | W0 | link84:1 | p50 | 0.0 | B | MEASURED |
| `D.queue.delay.p50` | CBAP | W0 | link84:1 | p50 | 0.0 | us | DERIVED |
| `D.queue.bytes.p90` | CBAP | W0 | link84:1 | p90 | 0.0 | B | MEASURED |
| `D.queue.delay.p90` | CBAP | W0 | link84:1 | p90 | 0.0 | us | DERIVED |
| `D.queue.bytes.p95` | CBAP | W0 | link84:1 | p95 | 0.0 | B | MEASURED |
| `D.queue.delay.p95` | CBAP | W0 | link84:1 | p95 | 0.0 | us | DERIVED |
| `D.queue.bytes.p99` | CBAP | W0 | link84:1 | p99 | 24104.0 | B | MEASURED |
| `D.queue.delay.p99` | CBAP | W0 | link84:1 | p99 | 19.28319999999 | us | DERIVED |
| `D.queue.bytes.max` | CBAP | W0 | link84:1 | max | 54496.0 | B | MEASURED |
| `D.queue.delay.max` | CBAP | W0 | link84:1 | max | 43.5968 | us | DERIVED |
| `D.queue.bytes.std` | CBAP | W0 | link84:1 | std | 3937.738084184 | B | MEASURED |
| `D.queue.delay.std` | CBAP | W0 | link84:1 | std | 3.150190467347 | us | DERIVED |
| `D.queue.pct_Qabs.max` | CBAP | W0 | link84:1 | max | 5.197148511074 | % | DERIVED |
| `D.queue.rtt_mult.max` | CBAP | W0 | link84:1 | max | 2.868210526315 | xRTT | DERIVED |
| `D.queue.frac_above_Q_low` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_high` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_red` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_abs` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.bytes.min` | CBAP | W1 | link84:1 | min | 0.0 | B | MEASURED |
| `D.queue.delay.min` | CBAP | W1 | link84:1 | min | 0.0 | us | DERIVED |
| `D.queue.bytes.mean` | CBAP | W1 | link84:1 | mean | 23945.60242383 | B | MEASURED |
| `D.queue.delay.mean` | CBAP | W1 | link84:1 | mean | 19.15648193906 | us | DERIVED |
| `D.queue.bytes.p50` | CBAP | W1 | link84:1 | p50 | 24104.0 | B | MEASURED |
| `D.queue.delay.p50` | CBAP | W1 | link84:1 | p50 | 19.28319999999 | us | DERIVED |
| `D.queue.bytes.p90` | CBAP | W1 | link84:1 | p90 | 45064.0 | B | MEASURED |
| `D.queue.delay.p90` | CBAP | W1 | link84:1 | p90 | 36.0512 | us | DERIVED |
| `D.queue.bytes.p95` | CBAP | W1 | link84:1 | p95 | 46112.0 | B | MEASURED |
| `D.queue.delay.p95` | CBAP | W1 | link84:1 | p95 | 36.8896 | us | DERIVED |
| `D.queue.bytes.p99` | CBAP | W1 | link84:1 | p99 | 47160.0 | B | MEASURED |
| `D.queue.delay.p99` | CBAP | W1 | link84:1 | p99 | 37.728 | us | DERIVED |
| `D.queue.bytes.max` | CBAP | W1 | link84:1 | max | 54496.0 | B | MEASURED |
| `D.queue.delay.max` | CBAP | W1 | link84:1 | max | 43.5968 | us | DERIVED |
| `D.queue.bytes.std` | CBAP | W1 | link84:1 | std | 14864.35569642 | B | MEASURED |
| `D.queue.delay.std` | CBAP | W1 | link84:1 | std | 11.89148455713 | us | DERIVED |
| `D.queue.pct_Qabs.max` | CBAP | W1 | link84:1 | max | 5.197148511074 | % | DERIVED |
| `D.queue.rtt_mult.max` | CBAP | W1 | link84:1 | max | 2.868210526315 | xRTT | DERIVED |
| `D.queue.frac_above_Q_low` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_high` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_red` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.frac_above_Q_abs` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `D.queue.bytes.min` | CBAP | W2 | link84:1 | min | 0.0 | B | MEASURED |
| `D.queue.delay.min` | CBAP | W2 | link84:1 | min | 0.0 | us | DERIVED |
| `D.queue.bytes.mean` | CBAP | W2 | link84:1 | mean | 23956.79890373 | B | MEASURED |
| `D.queue.delay.mean` | CBAP | W2 | link84:1 | mean | 19.16543912298 | us | DERIVED |
| `D.queue.bytes.p50` | CBAP | W2 | link84:1 | p50 | 24104.0 | B | MEASURED |
| `D.queue.delay.p50` | CBAP | W2 | link84:1 | p50 | 19.28319999999 | us | DERIVED |
| `D.queue.bytes.p90` | CBAP | W2 | link84:1 | p90 | 45064.0 | B | MEASURED |
| `D.queue.delay.p90` | CBAP | W2 | link84:1 | p90 | 36.0512 | us | DERIVED |
| `D.queue.bytes.p95` | CBAP | W2 | link84:1 | p95 | 46112.0 | B | MEASURED |
| `D.queue.delay.p95` | CBAP | W2 | link84:1 | p95 | 36.8896 | us | DERIVED |
| `D.queue.bytes.p99` | CBAP | W2 | link84:1 | p99 | 47160.0 | B | MEASURED |
| `D.queue.delay.p99` | CBAP | W2 | link84:1 | p99 | 37.728 | us | DERIVED |
| `D.queue.bytes.max` | CBAP | W2 | link84:1 | max | 54496.0 | B | MEASURED |
| `D.queue.delay.max` | CBAP | W2 | link84:1 | max | 43.5968 | us | DERIVED |
| `D.queue.bytes.std` | CBAP | W2 | link84:1 | std | 14868.38663800 | B | MEASURED |
| `D.queue.delay.std` | CBAP | W2 | link84:1 | std | 11.89470931040 | us | DERIVED |
| ... 116 more rows in the CSV | | | | | | | |

## safety (18 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `G.ecn.marks` | CBAP | W0 | link84:1 | sum | 0.0 | packets | MEASURED |
| `G.ecn.marks` | CBAP | W1 | link84:1 | sum | 0.0 | packets | MEASURED |
| `G.ecn.marks` | CBAP | W2 | link84:1 | sum | 0.0 | packets | MEASURED |
| `G.ecn.marks` | CBAP | W3 | link84:1 | sum | 0.0 | packets | MEASURED |
| `G.ecn.marks` | DCQCN | W0 | link84:1 | sum | 6677.0 | packets | MEASURED |
| `G.ecn.marks` | DCQCN | W1 | link84:1 | sum | 6677.0 | packets | MEASURED |
| `G.ecn.marks` | DCQCN | W2 | link84:1 | sum | 6677.0 | packets | MEASURED |
| `G.ecn.marks` | DCQCN | W3 | link84:1 | sum | 0.0 | packets | MEASURED |
| `G.pfc.events` | CBAP | W0 | all | count | 0 | count | MEASURED |
| `G.drops` | CBAP | W0 | all | count | 0 | count | MEASURED |
| `G.retx.bytes` | CBAP | W0 | all | sum | 0.0 | B | MEASURED |
| `G.retx.events` | CBAP | W0 | all | sum | 0.0 | count | MEASURED |
| `G.cnp.count` | CBAP | W0 | all | count |  | count | UNAVAILABLE |
| `G.pfc.events` | DCQCN | W0 | all | count | 0 | count | MEASURED |
| `G.drops` | DCQCN | W0 | all | count | 0 | count | MEASURED |
| `G.retx.bytes` | DCQCN | W0 | all | sum | 0.0 | B | MEASURED |
| `G.retx.events` | DCQCN | W0 | all | sum | 0.0 | count | MEASURED |
| `G.cnp.count` | DCQCN | W0 | all | count |  | count | UNAVAILABLE |

## service (244 rows)

| metric_id | arm | window | scope | stat | value | unit | evidence |
|---|---|---|---|---|---|---|---|
| `C.served.wire.mean` | CBAP | W0 | link84:1 | mean | 5.345670490918 | Gbps | DERIVED |
| `C.served.payload.mean` | CBAP | W0 | link84:1 | mean | 5.100830621105 | Gbps | DERIVED |
| `C.served.wire.p50` | CBAP | W0 | link84:1 | p50 | 7.545599999950 | Gbps | DERIVED |
| `C.served.payload.p50` | CBAP | W0 | link84:1 | p50 | 7.199999999952 | Gbps | DERIVED |
| `C.served.wire.p95` | CBAP | W0 | link84:1 | p95 | 8.384000000131 | Gbps | DERIVED |
| `C.served.payload.p95` | CBAP | W0 | link84:1 | p95 | 8.000000000125 | Gbps | DERIVED |
| `C.served.wire.p99` | CBAP | W0 | link84:1 | p99 | 10.06079999993 | Gbps | DERIVED |
| `C.served.payload.p99` | CBAP | W0 | link84:1 | p99 | 9.599999999937 | Gbps | DERIVED |
| `C.served.wire.max` | CBAP | W0 | link84:1 | max | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.max` | CBAP | W0 | link84:1 | max | 9.600000000363 | Gbps | DERIVED |
| `C.utilization.mean` | CBAP | W0 | link84:1 | mean | 0.534567049089 | ratio | DERIVED |
| `C.utilization.p50` | CBAP | W0 | link84:1 | p50 | 0.754559999995 | ratio | DERIVED |
| `C.utilization.p95` | CBAP | W0 | link84:1 | p95 | 0.838400000013 | ratio | DERIVED |
| `C.utilization.max` | CBAP | W0 | link84:1 | max | 1.006080000038 | ratio | DERIVED |
| `C.util.frac_below_90` | CBAP | W0 | link84:1 | fraction | 0.983699945666 | ratio | DERIVED |
| `C.util.frac_below_95` | CBAP | W0 | link84:1 | fraction | 0.985333284444 | ratio | DERIVED |
| `C.util.frac_below_99` | CBAP | W0 | link84:1 | fraction | 0.985336617788 | ratio | DERIVED |
| `C.util.frac_above_C` | CBAP | W0 | link84:1 | fraction | 0.014656715522 | ratio | DERIVED |
| `C.util.frac_above_1.05C` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `C.util.frac_above_1.10C` | CBAP | W0 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `C.idle.fraction` | CBAP | W0 | link84:1 | fraction | 0.333337777792 | ratio | DERIVED |
| `C.busy.fraction` | CBAP | W0 | link84:1 | fraction | 0.666662222207 | ratio | DERIVED |
| `C.served.total_bytes` | CBAP | W0 | link84:1 | sum | 2004619752.0 | B | MEASURED |
| `C.served.wire.mean` | CBAP | W1 | link84:1 | mean | 9.576628850362 | Gbps | DERIVED |
| `C.served.payload.mean` | CBAP | W1 | link84:1 | mean | 9.138004628208 | Gbps | DERIVED |
| `C.served.wire.p50` | CBAP | W1 | link84:1 | p50 | 10.06079999993 | Gbps | DERIVED |
| `C.served.payload.p50` | CBAP | W1 | link84:1 | p50 | 9.599999999937 | Gbps | DERIVED |
| `C.served.wire.p95` | CBAP | W1 | link84:1 | p95 | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.p95` | CBAP | W1 | link84:1 | p95 | 9.600000000363 | Gbps | DERIVED |
| `C.served.wire.p99` | CBAP | W1 | link84:1 | p99 | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.p99` | CBAP | W1 | link84:1 | p99 | 9.600000000363 | Gbps | DERIVED |
| `C.served.wire.max` | CBAP | W1 | link84:1 | max | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.max` | CBAP | W1 | link84:1 | max | 9.600000000363 | Gbps | DERIVED |
| `C.utilization.mean` | CBAP | W1 | link84:1 | mean | 0.957662885036 | ratio | DERIVED |
| `C.utilization.p50` | CBAP | W1 | link84:1 | p50 | 1.006079999993 | ratio | DERIVED |
| `C.utilization.p95` | CBAP | W1 | link84:1 | p95 | 1.006080000038 | ratio | DERIVED |
| `C.utilization.max` | CBAP | W1 | link84:1 | max | 1.006080000038 | ratio | DERIVED |
| `C.util.frac_below_90` | CBAP | W1 | link84:1 | fraction | 0.176906244739 | ratio | DERIVED |
| `C.util.frac_below_95` | CBAP | W1 | link84:1 | fraction | 0.259383942097 | ratio | DERIVED |
| `C.util.frac_below_99` | CBAP | W1 | link84:1 | fraction | 0.259552263928 | ratio | DERIVED |
| `C.util.frac_above_C` | CBAP | W1 | link84:1 | fraction | 0.740111092408 | ratio | DERIVED |
| `C.util.frac_above_1.05C` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `C.util.frac_above_1.10C` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `C.idle.fraction` | CBAP | W1 | link84:1 | fraction | 0.0 | ratio | DERIVED |
| `C.busy.fraction` | CBAP | W1 | link84:1 | fraction | 1.0 | ratio | DERIVED |
| `C.served.total_bytes` | CBAP | W1 | link84:1 | sum | 71118440.0 | B | MEASURED |
| `C.served.wire.mean` | CBAP | W2 | link84:1 | mean | 9.576400685166 | Gbps | DERIVED |
| `C.served.payload.mean` | CBAP | W2 | link84:1 | mean | 9.137786913327 | Gbps | DERIVED |
| `C.served.wire.p50` | CBAP | W2 | link84:1 | p50 | 10.06079999993 | Gbps | DERIVED |
| `C.served.payload.p50` | CBAP | W2 | link84:1 | p50 | 9.599999999937 | Gbps | DERIVED |
| `C.served.wire.p95` | CBAP | W2 | link84:1 | p95 | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.p95` | CBAP | W2 | link84:1 | p95 | 9.600000000363 | Gbps | DERIVED |
| `C.served.wire.p99` | CBAP | W2 | link84:1 | p99 | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.p99` | CBAP | W2 | link84:1 | p99 | 9.600000000363 | Gbps | DERIVED |
| `C.served.wire.max` | CBAP | W2 | link84:1 | max | 10.06080000038 | Gbps | DERIVED |
| `C.served.payload.max` | CBAP | W2 | link84:1 | max | 9.600000000363 | Gbps | DERIVED |
| `C.utilization.mean` | CBAP | W2 | link84:1 | mean | 0.957640068516 | ratio | DERIVED |
| `C.utilization.p50` | CBAP | W2 | link84:1 | p50 | 1.006079999993 | ratio | DERIVED |
| `C.utilization.p95` | CBAP | W2 | link84:1 | p95 | 1.006080000038 | ratio | DERIVED |
| `C.utilization.max` | CBAP | W2 | link84:1 | max | 1.006080000038 | ratio | DERIVED |
| ... 184 more rows in the CSV | | | | | | | |
