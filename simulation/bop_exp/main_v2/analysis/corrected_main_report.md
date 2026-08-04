# Corrected BOP-QB main-v2 report

## 唯一判定：`DCQCN_REVIEW_REQUIRED`

正式 273 次运行的哈希与配置复用审计为 273/273 通过，但该判定不能升级为 MAIN_V2_READY：旧 final-validation 的 n32 DCQCN 原始输入未保留，当前 262.024 us 与旧报告 213.184 us 的漂移无法解释。

PFC 主结论为 `OPEN_LOOP_NOT_PFC_BASELINE`。历史模式统一称为 `open_loop_no_endhost_cc`；PFC configured but runtime pause behavior not verified。它不属于正式 CC 基线，也不进入主胜负统计。

## 完整性与最小重跑

- 正式语料：225 主实验 + 30 消融 + 18 wire fairness = 273。
- `reuse_allowed=true`：273/273；Open-loop 历史结果 45 次另表。
- main-v2 事件级语义审计完成 0/9，缺失事件没有补成 0。
- `rerun_manifest.csv` 只有表头。当前正式运行均可复用；再次运行当前 n32 配置不能恢复缺失的旧配置或解释跨版本漂移。
- 需要的最小非仿真工作是找回旧 topology/config/flow/round/fixed-path/run_meta，或独立审查为何旧归档未保留它们。

## 正式比较口径

正式基线仅包括 DCTCP、DCQCN、TIMELY、HPCC-INT。每个场景的 best formal CC baseline 是其中 mean group RCT 最低者。Open-loop、Wire-Equalized DCQCN、Gate 与 BOP 均不参与该选择。

## BOP-QB 与 best formal CC baseline

| 场景 | 正式基线 | 基线 RCT us | BOP-QB RCT us | RCT变化 | queue变化 | Pareto |
|---|---|---:|---:|---:|---:|---:|
| msg_16k_n16_g50 | DCQCN | 25.789 | 27.518 | 6.70% | -1.24% | yes |
| msg_64k_n16_g50 | DCTCP | 90.995 | 95.897 | 5.39% | -68.50% | yes |
| msg_256k_n16_g50 | DCTCP | 385.705 | 369.351 | -4.24% | -90.27% | yes |
| msg_1m_n16_g50 | DCTCP | 1442.516 | 1464.268 | 1.51% | -90.18% | yes |
| msg_4m_n16_g50 | DCTCP | 5631.232 | 5848.237 | 3.85% | -90.25% | yes |
| n8_64k_g50 | DCQCN | 47.702 | 50.451 | 5.76% | -40.79% | yes |
| n32_64k_g50 | DCTCP | 177.897 | 187.078 | 5.16% | -84.67% | yes |
| n64_64k_g50 | DCTCP | 351.859 | 370.178 | 5.21% | -91.84% | yes |
| gap_0us_n16_64k | DCTCP | 95.611 | 100.189 | 4.79% | -66.34% | yes |
| gap_20us_n16_64k | DCQCN | 91.324 | 96.094 | 5.22% | -68.88% | yes |
| gap_100us_n16_64k | DCTCP | 90.771 | 95.661 | 5.39% | -69.24% | yes |
| gap_500us_n16_64k | DCQCN | 91.008 | 95.902 | 5.38% | -68.79% | yes |
| hetero_equal | DCTCP | 178.813 | 187.540 | 4.88% | -84.46% | yes |
| hetero_mild | DCTCP | 187.392 | 187.556 | 0.09% | -82.42% | yes |
| hetero_strong | DCTCP | 187.281 | 187.730 | 0.24% | -79.78% | yes |

BOP-QB 同时改善 RCT 与峰值队列的场景为 **1/15**；以不超过 3% RCT 代价换取至少 50% 峰值队列下降的场景为 **4/15**。
这替代旧报告错误地以 Open-loop 作为最佳基线所得的 0/15 结论。

## 四类扫描

### Message size

| 场景 | BOP-QB RCT us | 相对正式最佳RCT变化 | 相对正式最佳queue变化 |
|---|---:|---:|---:|
| msg_16k_n16_g50 | 27.518 | 6.70% | -1.24% |
| msg_64k_n16_g50 | 95.897 | 5.39% | -68.50% |
| msg_256k_n16_g50 | 369.351 | -4.24% | -90.27% |
| msg_1m_n16_g50 | 1464.268 | 1.51% | -90.18% |
| msg_4m_n16_g50 | 5848.237 | 3.85% | -90.25% |

### Participants

| 场景 | BOP-QB RCT us | 相对正式最佳RCT变化 | 相对正式最佳queue变化 |
|---|---:|---:|---:|
| n8_64k_g50 | 50.451 | 5.76% | -40.79% |
| n32_64k_g50 | 187.078 | 5.16% | -84.67% |
| n64_64k_g50 | 370.178 | 5.21% | -91.84% |

### Compute gap

| 场景 | BOP-QB RCT us | 相对正式最佳RCT变化 | 相对正式最佳queue变化 |
|---|---:|---:|---:|
| msg_64k_n16_g50 | 95.897 | 5.39% | -68.50% |
| gap_0us_n16_64k | 100.189 | 4.79% | -66.34% |
| gap_20us_n16_64k | 96.094 | 5.22% | -68.88% |
| gap_100us_n16_64k | 95.661 | 5.39% | -69.24% |
| gap_500us_n16_64k | 95.902 | 5.38% | -68.79% |

### Heterogeneity

| 场景 | BOP-QB RCT us | 相对正式最佳RCT变化 | 相对正式最佳queue变化 |
|---|---:|---:|---:|
| hetero_equal | 187.540 | 4.88% | -84.46% |
| hetero_mild | 187.556 | 0.09% | -82.42% |
| hetero_strong | 187.730 | 0.24% | -79.78% |

## Gate → BOP → BOP-QB 消融

| 场景 | 比较 | RCT变化 | queue变化 | goodput变化 |
|---|---|---:|---:|---:|
| msg_64k_n16_g50 | gate_to_bop | 9.43% | -99.23% | -8.61% |
| msg_64k_n16_g50 | bop_to_bop_qb | -7.93% | 3591.67% | 8.61% |
| msg_64k_n16_g50 | gate_to_bop_qb | 0.76% | -71.45% | -0.75% |
| msg_256k_n16_g50 | gate_to_bop | -28.69% | -99.69% | 40.22% |
| msg_256k_n16_g50 | bop_to_bop_qb | -2.42% | 3035.71% | 2.48% |
| msg_256k_n16_g50 | gate_to_bop_qb | -30.41% | -90.13% | 43.70% |
| msg_4m_n16_g50 | gate_to_bop | -6.71% | -99.71% | 7.19% |
| msg_4m_n16_g50 | bop_to_bop_qb | -0.27% | 3284.62% | 0.27% |
| msg_4m_n16_g50 | gate_to_bop_qb | -6.95% | -90.14% | 7.47% |
| n32_64k_g50 | gate_to_bop | 5.49% | -99.36% | -5.20% |
| n32_64k_g50 | bop_to_bop_qb | -4.69% | 2175.00% | 4.92% |
| n32_64k_g50 | gate_to_bop_qb | 0.54% | -85.47% | -0.53% |
| hetero_strong | gate_to_bop | -36.91% | -99.31% | 58.47% |
| hetero_strong | bop_to_bop_qb | -4.07% | 2746.67% | 4.24% |
| hetero_strong | gate_to_bop_qb | -39.47% | -80.22% | 65.18% |

## Wire-Equalized 公平性

该模式仅为诊断，不是正式基线。既有结果保持不变：

| 场景 | 每DATA额外字节 | RCT差距解释比例 | BOP-QB对Equalized RCT | BOP-QB对Equalized queue |
|---|---:|---:|---:|---:|
| gap_20us_n16_64k | 42.0 | 88.65808277572988 | 0.57% | -70.88% |
| msg_64k_n16_g50 | 42.0 | 86.95385767535272 | 0.67% | -71.42% |
| n32_64k_g50 | 42.0 | NA | -26.86% | -85.47% |
| single_round_n16_64k | 42.0 | 86.88042660832697 | 0.64% | -68.06% |

## PFC 与 Open-loop 处理

- 主结论：`OPEN_LOOP_NOT_PFC_BASELINE`。
- 事件级审计 0/9；历史 PFC 数字在本报告中标记 NA，不声明 BOP-QB 改善 PFC。
- Open-loop 仅在 `open_loop_tradeoff.csv` 和附录使用。

## DCQCN 跨版本审计

- 结论：`DCQCN_DRIFT_UNRESOLVED`。
- 当前 main-v1 n32 DCQCN 三-seed mean RCT：262.024 us；旧报告：213.184 us；差值 48.840 us（22.91%）。
- 当前 273 次正式运行并未因此被判定为哈希无效，但在解释该漂移前不能完成正式论文结论。

## 不能得出的结论

- 不能称 Open-loop 为 PFC-only 正式基线。
- 不能从旧的零计数宣称 PFC 未触发或 BOP-QB 降低 PFC。
- 不能用三 seed 外推生产网络、动态路由或多瓶颈。
- 不能解释 n32 DCQCN 的跨版本漂移，直到旧输入证据恢复。
