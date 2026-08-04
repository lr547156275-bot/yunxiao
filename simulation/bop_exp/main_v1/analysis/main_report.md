# BOP-QB 主实验分析报告

## 唯一完整性判定

**MAIN_EXPERIMENT_VALID**

该判定只评价数据完整性，不以 BOP-QB 是否获胜为标准。

## 数据完整性

- Manifest：318 个唯一 run；实际完成并审计：318/318。
- 三个 seed 各 106 个 run；主实验 270、消融 30、wire fairness 18。
- exit、flow/round 完成、CC_MODE、global barrier、NaN/Inf、日志截断、输入哈希、seed 哈希、BOP/BOP-QB 公式和 wire fairness 均逐 run 检查。
- PRT、QB-Max、Oracle 未进入 `main_v1` 矩阵。
- 无效 run 数：0；详情见 `invalid_runs.csv`。

## 统计口径

统计单位是 scenario+seed。每个 run 内的 round 只用于形成该 seed 的工作负载汇总，不作为独立 seed。报告三 seed 均值、样本标准差、p50/p95/p99、最大值及配对差值；95% t 区间使用 df=2、t=4.30265。三个 seed 的区间只反映当前有限 seed，不能解释为广泛统计稳定性。

## 实验问题、平台和场景

本实验回答五个问题：BOP-QB 的 group RCT、队列/拥塞代价、消息大小与参与者扩展性、Gate→BOP→BOP-QB 的机制贡献，以及 42 B DATA 线上开销对短消息比较的影响。平台是 ns-3 仿真而非真实 GPU：固定 ECMP、100 Gbit/s 单共享瓶颈、1000 B 应用 packet payload、PFC/ECN 开启，使用同一 QP 连续序列空间和 global barrier。INT 只在相应算法模式中启用。

正式外部基线为 PFC-only、DCTCP、DCQCN、TIMELY、HPCC-INT；CRFM-Gate 与 BOP 仅用于消融，DCQCN-Wire-Equalized 仅用于线上字节诊断。主场景覆盖 16 KiB–4 MiB、8–64 参与者、0–500 us compute gap 以及 equal/mild/strong 异构性；所有跨算法比较共享同一 scenario+seed 输入哈希。

## 指标定义

- group RCT = 最后一个组内 ACK 完成时间 − common release；
- payload goodput = 所有 group payload bits / group active-window RCT 总和；active utilization = payload goodput / 100 Gbit/s；
- 物理下界 = 8×group payload bytes / bottleneck capacity；lower-bound efficiency = 下界总和 / RCT 总和；
- completion skew = 同一 group 最晚与最早 flow ACK 完成时间差；
- barrier-p75 tail = barrier 完成时间 − flow ACK 完成时间 p75；
- queue p95/max、ECN、PFC 来自每 run 的冻结汇总输出；缺失字段保持 `NA`，不补零。

## 主实验：BOP-QB 与最优外部基线

| 场景 | 最优RCT基线 | 基线RCT (us) | BOP-QB RCT (us) | RCT变化 | 基线queue max (KiB) | BOP-QB queue max (KiB) | queue变化 |
|---|---:|---:|---:|---:|---:|---:|---:|
| msg_16k_n16_g50 | PFC-only | 25.79 | 27.52 | 6.70% | 111.72 | 110.33 | -1.24% |
| msg_64k_n16_g50 | PFC-only | 90.93 | 95.90 | 5.46% | 498.84 | 157.18 | -68.49% |
| msg_256k_n16_g50 | PFC-only | 352.02 | 369.35 | 4.92% | 1600.72 | 155.76 | -90.27% |
| msg_1m_n16_g50 | PFC-only | 1396.51 | 1464.27 | 4.85% | 1600.66 | 157.18 | -90.18% |
| msg_4m_n16_g50 | PFC-only | 5574.02 | 5848.24 | 4.92% | 1600.66 | 156.12 | -90.25% |
| n8_64k_g50 | PFC-only | 47.70 | 50.45 | 5.76% | 236.69 | 140.15 | -40.79% |
| n32_64k_g50 | PFC-only | 177.61 | 187.08 | 5.33% | 1061.57 | 161.44 | -84.79% |
| n64_64k_g50 | PFC-only | 351.72 | 370.18 | 5.25% | 2119.39 | 173.51 | -91.81% |
| gap_0us_n16_64k | PFC-only | 95.59 | 100.19 | 4.81% | 515.54 | 173.51 | -66.34% |
| gap_20us_n16_64k | PFC-only | 91.28 | 96.09 | 5.27% | 500.44 | 156.47 | -68.73% |
| gap_100us_n16_64k | PFC-only | 90.71 | 95.66 | 5.46% | 506.47 | 155.76 | -69.24% |
| gap_500us_n16_64k | PFC-only | 90.98 | 95.90 | 5.41% | 496.31 | 155.06 | -68.76% |
| hetero_equal | PFC-only | 178.26 | 187.54 | 5.20% | 1028.71 | 159.31 | -84.51% |
| hetero_mild | PFC-only | 178.49 | 187.56 | 5.08% | 977.54 | 162.15 | -83.41% |
| hetero_strong | PFC-only | 177.66 | 187.73 | 5.67% | 759.67 | 151.51 | -80.06% |

在 15 个主场景中，BOP-QB 同时降低最优 RCT 基线的 RCT 和峰值队列的场景为 0/15（0.0%）；以不超过 3% RCT 代价换取至少 50% 峰值队列下降的场景为 0/15（0.0%）。这些是数据描述，不是预设胜负门槛。

完整的 BOP-QB 对 PFC-only、DCTCP、DCQCN、TIMELY、HPCC-INT 的配对数字、方向和置信区间位于 `pairwise_bop_vs_baselines.csv`。主表使用标准 DCQCN，不以 Wire-Equalized 诊断替代。

## 四类扫描

### 消息大小

16 KiB 到 4 MiB 中，BOP-QB 相对各场景最优外部 RCT 基线的代价为 4.85%–6.70%；峰值队列下降 1.24%–90.27%。16 KiB 场景的队列仅下降 1.24%，而 256 KiB、1 MiB、4 MiB 均下降约 90%。BOP-QB 的物理下界效率由 16 KiB 的 0.762 增至 4 MiB 的 0.918。短消息结果包含启动和协议固定开销；中大消息体现持续注入。没有逐消息大小调参。

### 参与者

参与者从 8 增至 64 时，BOP-QB group RCT 从 50.45 us 增至 370.18 us，峰值队列从 140.15 KiB 增至 173.51 KiB；PFC 始终为 0，ECN marks/1000 DATA 也为 0。n64 相对其最优 RCT 基线慢 5.25%，但峰值队列低 91.81%；completion skew 为 6.85 us，而 PFC-only 为 255.13 us。n64 不被排除。

### Compute gap

BOP-QB 的平均 group RCT 在五个 gap 上为 95.66–100.19 us；gap=0 最高，gap=20–500 us 的变化小于 0.5 us。相对最优外部 RCT 基线的代价为 4.81%–5.46%，峰值队列下降 66.34%–69.24%。这说明在当前 same-QP/global-barrier 输入中，非零 gap 上 BOP-QB 对 gap 较不敏感，但不能外推为所有跨轮状态均无影响。

### 异构性

equal→strong 时，PFC-only completion skew 从 39.37 us 增至 170.24 us；BOP-QB 从 3.60 us 增至 15.84 us。strong 场景中 BOP-QB 的 barrier-p75 tail 为 1.26 us，PFC-only 为 7.15 us；其 RCT 仍比最优外部基线慢 5.67%。因此工作量比例配速显著改善完成对齐，但没有消除 RCT 代价。该结果不代表动态路径或多瓶颈。

## 消融：Gate → BOP → BOP-QB

| 场景 | 比较 | RCT变化 | queue max变化 | goodput变化 |
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

Gate→BOP 隔离工作量比例基础配速；BOP→BOP-QB 隔离有界启动信用；Gate→BOP-QB 表示完整机制差异。消融不包含 QB-Max、PRT 或 Oracle。

## 线上字节公平性

| 场景 | 每DATA平均额外字节 | Equalized解释RCT差距 | BOP-QB对Equalized RCT差距 | BOP-QB对Equalized queue变化 |
|---|---:|---:|---:|---:|
| gap_20us_n16_64k | 42.00 | 88.66% | 0.57% | -70.88% |
| msg_64k_n16_g50 | 42.00 | 86.95% | 0.67% | -71.42% |
| n32_64k_g50 | 42.00 | NA | -26.86% | -85.47% |
| single_round_n16_64k | 42.00 | 86.88% | 0.64% | -68.06% |

Wire-Equalized DCQCN 是 diagnostic-only：应用 payload、DATA 包数与 BOP-QB 相同，只用于估计线上字节差异。它不替代主实验中的标准 DCQCN。

## RCT—队列权衡

`pareto_points.csv` 给出每个主场景的 RCT/queue Pareto 标记。BOP-QB 的主要可观察特征是以有界队列预算换取不同程度的 RCT 代价；所有不利场景均保留在上表和图中。

## 不利结果与解释边界

最优外部 RCT 基线在 15/15 主场景中都是 PFC-only；BOP-QB 相对它慢 4.81%–6.70%，payload goodput 相应降低 4.59%–6.26%。这意味着正式数据不支持“BOP-QB 无代价降低 RCT”的表述。与此同时，除 16 KiB 外，BOP-QB 大幅降低峰值队列并在所有主场景记录到 0 ECN、0 PFC；所有算法的 PFC 均为 0，因此本矩阵不能证明 PFC 改善。

在 gap20、64 KiB 和 single-round 中，42 B 等线上字节诊断分别解释原生 DCQCN 与 BOP-QB RCT 差距的约 88.66%、86.95% 和 86.88%；等字节后 BOP-QB 仍慢 0.57%、0.67% 和 0.64%。n32 中 BOP-QB 已经比原生及等字节 DCQCN 更快，因此不存在可定义的“DCQCN 优势解释比例”，报告为 NA。该诊断支持协议线上开销解释，但不是生产部署因果证明。

## 局限与不能得出的结论

- 结果来自 ns-3，不是真实 GPU、NCCL 或生产部署测量。
- 仅覆盖固定 ECMP、100 Gbit/s、单共享瓶颈、global barrier 和当前 PFC/ECN/INT 配置。
- 不覆盖动态路由、动态多瓶颈、强背景流或部署开销。
- 三个 seed 不足以支撑广泛的统计稳定性声明。
- 零 ECN/PFC 只能说明这些场景中的记录结果，不能外推到未测负载。

## 输出索引

所有聚合表、配对表、扫描表、Pareto 点、异常清单及 12 张 SVG/PDF 图均位于本目录；每张图的数据位于 `figures/data/`。
