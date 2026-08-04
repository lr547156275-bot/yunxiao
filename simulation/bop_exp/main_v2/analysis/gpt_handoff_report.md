# BOP-QB 研究总体报告与下一步决策材料

## 1. 执行摘要

当前最终候选算法是 **BOP-QB（Barrier-Optimal Pacing with Queue
Budget）**，CC_MODE=15。它面向固定 ECMP、同步 barrier、单共享瓶颈的
周期通信，核心目标不是无条件取得最低 RCT，而是在保持较小 RCT 代价的
同时显著降低拥塞队列、ECN 风险和 barrier 拖尾。

现有 main-v1 数据经过 main-v2 重新分类与复用审计：

- 正式结果共 273 次：
  - 主实验：15 场景 × 5 算法 × 3 seed = 225；
  - 消融：5 场景 × 2 算法 × 3 seed = 30；
  - Wire-Equalized 公平性：18。
- 273/273 个正式运行通过输入、算法、CC_MODE 和结果完整性复用检查。
- 历史 `pfc_only` 不再作为正式基线，改称
  `open_loop_no_endhost_cc`，45 次历史结果仅进入附录 tradeoff。
- 正式外部基线仅为 DCTCP、DCQCN、TIMELY、HPCC-INT。

修正后的主要结果：

- BOP-QB 在 15/15 场景中都降低峰值队列；
- 13/15 场景的峰值队列下降约 66%–92%；
- 1/15 场景同时改善 RCT 和队列；
- 4/15 场景满足“RCT 代价不超过 3%，队列下降至少 50%”；
- BOP-QB 在所有 15 个场景中均位于 RCT—queue Pareto 前沿；
- 相对 TIMELY，13/15 场景 RCT 更低；
- 相对 HPCC-INT，14/15 场景 RCT 更低；
- 相对 DCQCN，8/15 场景 RCT 更低；
- 相对 DCTCP，1/15 场景 RCT 更低。

因此最合理的论文主张是：

> BOP-QB 利用 barrier workload 的已知当前轮工作量，在固定路径共享
> 瓶颈中执行 group 级基础配速和严格有界的启动队列预算，从而形成明显
> 更优的 RCT—queue Pareto 权衡；它不是所有场景中的最低 RCT 算法。

当前还不能宣称实验完全定稿。唯一审计判定为：

**`DCQCN_REVIEW_REQUIRED`**

原因是 n32 DCQCN 当前结果与早期 final-validation 报告存在无法解释的
跨版本差异。此外，main-v2 的事件级 PFC 语义审计尚未运行。

---

## 2. 算法定义

### 2.1 BOP 基础配速

每个 global-barrier group 的当前轮开始时，根据当前轮每条流字节数、
固定路径、链路容量与 release 前可获得的队列观测，计算统一完成目标：

```text
work_l = q_l + sum(B_f for flows using link l)
available_l = rho * C_l - background_l
T_link_l = 8 * work_l / available_l
T_line_f = 8 * B_f / Rmax_f
T_star = max(max_f T_line_f, max_l T_link_l)
r_base_f = min(Rmax_f, 8 * B_f / T_star)
```

当前正式场景为显式单共享瓶颈；算法不进行动态路由。

### 2.2 BOP-QB 启动信用

正式 BOP-QB 使用固定的 0.5×ECN 队列目标：

```text
Q_target = 0.5 * Q_ECN
packet_margin = N * packet_bytes
queue_room = max(Q_target - q0 - packet_margin, 0)
group_credit = min(queue_room, total_group_round_bytes)
```

group credit 按当前轮字节比例确定性分配给各 QP。信用范围内以 NIC/QP
最大速率发送，信用耗尽后每轮最多一次切换回 BOP base rate。本轮不执行
HPCC 实时速率修改；INT 只服务后续轮次观测。

### 2.3 冻结边界

正式算法冻结为：

- algorithm_name=`bop_qb`；
- CC_MODE=15；
- queue target=0.5×ECN；
- 保留 global barrier、同一 QP 跨轮、连续序列号、固定 ECMP；
- 保留原 BOP `T_star` 和 base-rate 公式；
- 保留 phase stagger；
- 不采用 QB-Max、PRT、Oracle-q0 或 BOP-WC。

---

## 3. 实验环境与统计口径

- 平台：ns-3 仿真，不是真实 GPU/NCCL 或生产部署；
- 链路：统一 100 Gbit/s；
- 拓扑：固定 ECMP、单共享瓶颈；
- payload：1000 B；
- 通信：同一 QP 多轮、连续 `snd_nxt/snd_una`；
- 同步：global barrier，下一轮在上一轮所有 QP ACK 完成后释放；
- seed：1、2、3；同 scenario+seed 跨算法输入哈希一致；
- 统计单位：scenario+seed，不把 round 当作独立 seed；
- 95% CI：三 seed 配对 t 区间，df=2，仅反映有限 seed；
- RCT：最后一个组内 ACK 完成时间减 common release；
- 正式 CC 基线：DCTCP、DCQCN、TIMELY、HPCC-INT；
- proposed：BOP-QB；
- ablation：CRFM-Gate、BOP；
- diagnostic-only：DCQCN-Wire-Equalized；
- Open-loop：只进入附录，不参与 best formal CC baseline。

---

## 4. 主实验结果

以下比较均使用每个场景 RCT 最低的正式 CC 基线。负的 RCT/queue 变化
表示 BOP-QB 更好。

| 场景 | 最佳正式基线 | BOP-QB RCT变化 | BOP-QB queue变化 | Goodput变化 |
|---|---|---:|---:|---:|
| msg_16k_n16_g50 | DCQCN | +6.70% | -1.24% | -6.26% |
| msg_64k_n16_g50 | DCTCP | +5.39% | -68.50% | -5.11% |
| msg_256k_n16_g50 | DCTCP | **-4.24%** | **-90.27%** | **+4.42%** |
| msg_1m_n16_g50 | DCTCP | +1.51% | -90.18% | -1.49% |
| msg_4m_n16_g50 | DCTCP | +3.85% | -90.25% | -3.71% |
| n8_64k_g50 | DCQCN | +5.76% | -40.79% | -5.45% |
| n32_64k_g50 | DCTCP | +5.16% | -84.67% | -4.91% |
| n64_64k_g50 | DCTCP | +5.21% | -91.84% | -4.95% |
| gap_0us_n16_64k | DCTCP | +4.79% | -66.34% | -4.57% |
| gap_20us_n16_64k | DCQCN | +5.22% | -68.88% | -4.96% |
| gap_50us（msg_64k） | DCTCP | +5.39% | -68.50% | -5.11% |
| gap_100us_n16_64k | DCTCP | +5.39% | -69.24% | -5.11% |
| gap_500us_n16_64k | DCQCN | +5.38% | -68.79% | -5.10% |
| hetero_equal | DCTCP | +4.88% | -84.46% | -4.65% |
| hetero_mild | DCTCP | +0.09% | -82.42% | -0.11% |
| hetero_strong | DCTCP | +0.24% | -79.78% | -0.29% |

### 4.1 同时改善

唯一同时改善 RCT、队列和 goodput 的主场景是 256 KiB：

- RCT：降低 4.24%；
- 峰值队列：降低 90.27%；
- goodput：提高 4.42%。

### 4.2 低代价队列改善

以下四个场景满足“RCT 代价≤3%，queue 下降≥50%”：

- msg_256k_n16_g50；
- msg_1m_n16_g50；
- hetero_mild；
- hetero_strong。

### 4.3 明显不利场景

- 16 KiB：RCT 慢 6.70%，队列仅下降 1.24%，不支持使用 BOP-QB；
- n8 64 KiB：RCT 慢 5.76%，队列下降 40.79%，未达到 50%；
- 64 KiB 与大多数 gap/participant 场景：通常用约 4.8%–5.4% RCT
  代价换取约 66%–92% 队列下降。

不能把这些结果写成“BOP-QB 全面降低 RCT”。

---

## 5. 分基线结果

跨 15 场景进行非加权描述：

| 正式基线 | BOP-QB RCT更低场景数 | RCT相对变化的跨场景算术平均 | queue更低场景数 |
|---|---:|---:|---:|
| DCTCP | 1/15 | +3.69% | 15/15 |
| DCQCN | 8/15 | -14.60% | 15/15 |
| TIMELY | 13/15 | -40.02% | 15/15 |
| HPCC-INT | 14/15 | -26.60% | 15/15 |

这里的跨场景平均只是描述，不是按流量权重计算的总体性能，也不能代替
逐场景配对结果。

---

## 6. 四类扫描

### 6.1 消息大小

- 16 KiB：固定协议与启动开销占主导，BOP-QB 没有实质队列优势；
- 64 KiB：队列下降 68.50%，但 RCT 慢 5.39%；
- 256 KiB：当前最佳点，同时改善 RCT、queue 与 goodput；
- 1 MiB：RCT 代价 1.51%，queue 下降 90.18%；
- 4 MiB：queue 下降 90.25%，但 RCT 代价增至 3.85%。

### 6.2 参与者

- n8：queue 收益不足 50%，RCT 代价 5.76%；
- n32：queue 下降 84.67%，RCT 慢 5.16%；
- n64：queue 下降 91.84%，RCT 慢 5.21%。

队列收益随 incast 强度显著增加，但 RCT 优势没有同步出现。

### 6.3 Compute gap

gap=0、20、50、100、500 us 的 BOP-QB RCT 代价均约
4.79%–5.39%，queue 下降约 66.34%–69.24%。在当前 same-QP/global
barrier 场景中，它对非零 gap 较不敏感，但不能外推到任意跨轮状态。

### 6.4 异构性

- equal：RCT +4.88%，queue -84.46%；
- mild：RCT +0.09%，queue -82.42%；
- strong：RCT +0.24%，queue -79.78%。

异构场景是论文中较强的结果：工作量比例配速使不同大小流更接近共同
完成，同时保持显著低队列。

---

## 7. 消融结果

比较链条为 CRFM-Gate → BOP → BOP-QB：

1. Gate→BOP：隔离工作量比例基础配速；
2. BOP→BOP-QB：隔离有界启动信用；
3. Gate→BOP-QB：完整机制差异。

代表性结果：

| 场景 | Gate→BOP-QB RCT变化 | Gate→BOP-QB queue变化 | Goodput变化 |
|---|---:|---:|---:|
| 64 KiB | +0.76% | -71.45% | -0.75% |
| 256 KiB | -30.41% | -90.13% | +43.70% |
| 4 MiB | -6.95% | -90.14% | +7.47% |
| n32 64 KiB | +0.54% | -85.47% | -0.53% |
| hetero_strong | -39.47% | -80.22% | +65.18% |

消融显示 BOP 基础配速承担主要的队列控制作用；QB 信用回收部分短消息
启动损失，但会把 BOP 极低的队列提高到仍受限的目标范围。该变化不是
“信用无成本改善”。

---

## 8. Wire-Equalized 公平性

BOP-QB/HPCC-INT DATA 每包比原生 DCQCN 多 42 B。诊断模式只为 DCQCN
添加相同线上 padding，不改变应用 payload、包数或 DCQCN 控制。

| 场景 | 42 B解释原RCT差距 | BOP-QB对Equalized RCT | queue变化 |
|---|---:|---:|---:|
| gap20 | 88.66% | +0.57% | -70.88% |
| msg64k | 86.95% | +0.67% | -71.42% |
| single-round | 86.88% | +0.64% | -68.06% |
| n32 | 不适用，BOP-QB原本更快 | -26.86% | -85.47% |

这表明短消息中原生 DCQCN 的大部分 RCT 优势来自 DATA 线上字节差异，
但 Wire-Equalized 只能作为仿真诊断，不能替代论文主表中的原生 DCQCN。

---

## 9. Open-loop 与 PFC 语义

历史 `pfc_only` 的真实语义是：

- CC_MODE=0；
- 无端侧拥塞控制；
- QP 按最大速率开环发送；
- 交换机配置了 PFC；
- 历史日志不能证明 pause 生成、接收和发送端实际暂停的完整路径；
- 论文 queue 指标与 PFC 判断来自不同的记账对象。

因此统一改称：

`open_loop_no_endhost_cc`

并给出限定：

> PFC configured but runtime pause behavior not verified.

当前 main-v2 事件级语义审计完成 **0/9**，所以：

- PFC 主结论：`OPEN_LOOP_NOT_PFC_BASELINE`；
- PFC count 与 pause duration 在正式报告中标记 NA；
- 不声明 BOP-QB 降低 PFC；
- Open-loop 不进入 best formal CC baseline。

---

## 10. n32 DCQCN 重现性问题

当前 main-v1：

- n32 DCQCN 三-seed mean group RCT：262.024 us。

早期 final-validation 报告：

- n32 DCQCN mean group RCT：213.184 us。

差异：

- +48.840 us；
- +22.91%。

当前 273 次正式运行的哈希与配置检查有效，但旧归档只保留报告和源码
补丁，没有完整的旧：

- `run_meta.json`；
- `config.txt`；
- `topology.txt`；
- `flow.txt`；
- `rounds.txt`；
- `fixed_paths.txt`。

因此：

- `legacy_config_unavailable=true`；
- DCQCN 结论为 `DCQCN_DRIFT_UNRESOLVED`；
- 重复运行当前配置不能恢复或解释旧配置；
- task 28 要求 `reuse_allowed=true` 的正式运行不得重跑，所以当前
  `rerun_manifest.csv` 只有表头；
- 总体唯一判定为 `DCQCN_REVIEW_REQUIRED`，不是 MAIN_V2_READY。

---

## 11. 论文可支持的主张

### 可以支持

1. 在固定路径同步 barrier 单瓶颈中，BOP-QB 能显著降低峰值队列；
2. BOP-QB 在全部已测主场景处于 RCT—queue Pareto 前沿；
3. 在中等消息和异构 workload 中，可以用很小 RCT 代价换取约
   80%–90% 队列下降；
4. 256 KiB 场景中可同时改善 RCT、goodput 和 queue；
5. 相比 TIMELY/HPCC-INT，BOP-QB 在多数场景的 RCT 也更低；
6. Gate→BOP→BOP-QB 消融能够区分基础配速与启动信用的作用；
7. 42 B Wire-Equalized 诊断解释了大部分短消息 DCQCN RCT 差距。

### 不能支持

1. BOP-QB 在所有场景都降低 RCT；
2. BOP-QB 全面击败 DCTCP 或 DCQCN；
3. BOP-QB 已证明降低 PFC；
4. Open-loop 是正式 PFC-only 基线；
5. 三个 seed 已证明广泛统计稳定性；
6. 结果可直接外推到真实 GPU、NCCL 或生产网络；
7. 已覆盖动态路由、多瓶颈或强背景流；
8. n32 DCQCN 跨版本结果已经解释。

---

## 12. 建议论文定位

建议标题和摘要围绕以下关键词：

- barrier-aware congestion control；
- collective communication pacing；
- workload-proportional rate allocation；
- bounded queue budget；
- RCT—queue Pareto efficiency；
- predictable synchronized completion。

不建议将论文包装为：

- universal low-latency congestion control；
-全面替代 DCQCN/HPCC；
- 所有消息大小均获得最低 FCT/RCT；
- 已验证 PFC 消除。

论文的核心问题可以定义为：

> 对已知当前轮工作量的同步 collective，是否可以在不依赖动态反馈收敛
> 的情况下，通过一次性 group 计划降低队列，并保持接近最快正式基线的
> barrier RCT？

---

## 13. 下一步需要 GPT 作出的决策

请基于上述证据，只选择一个下一步路线：

### 路线 A：先解决审计，再完成当前论文

最低工作：

1. 判断是否必须找回或重建旧 n32 DCQCN 配置证据；
2. 决定是否执行已经实现但尚未运行的 9 次 PFC 语义审计；
3. 审计完成后重新判断 `MAIN_V2_READY`；
4. 保持算法和参数冻结，不继续发明算法变体。

这是当前最稳妥的路线。

### 路线 B：补充有限外部有效性实验

在不调参的前提下，只增加少量：

- 背景流；
- 第二种瓶颈容量；
- 一个多瓶颈固定路径场景；
- 更多 seed。

目的不是寻找有利场景，而是确定低队列收益是否能超出当前单瓶颈模型。
此路线工作量较高，且必须先冻结新增实验矩阵。

### 路线 C：按当前证据写一篇范围严格限定的论文

明确声明：

- 只研究固定 ECMP、同步 barrier、单瓶颈；
- 主贡献是 queue/RCT Pareto，而不是普遍 RCT 胜出；
- PFC 不作为核心结果；
- n32 DCQCN 漂移列为 reproducibility limitation。

如果目标是尽快形成初稿，此路线可行，但投稿前仍建议解决 n32 审计。

---

## 14. 建议向 GPT 提问

请 GPT 回答：

1. 上述结果是否足以形成以 RCT—queue Pareto 为主线的论文？
2. 1/15 同时改善、4/15 低代价大幅降队列，是否足以构成系统论文贡献？
3. n32 DCQCN 漂移应作为阻塞问题、局限，还是删除该场景？
4. 是否必须执行 9 次 PFC 语义审计，或者应彻底移除 PFC claim？
5. 下一步应该优先补背景流/多瓶颈/更多 seed 中的哪一项？
6. 如何避免把 Open-loop 或 Wire-Equalized 误用为正式基线？
7. 最合理的论文 claim、标题、摘要和章节结构是什么？
8. 在不修改冻结 BOP-QB 的前提下，最小补充实验矩阵应是什么？

---

## 15. 关键文件

- 修正主报告：
  `bop_exp/main_v2/analysis/corrected_main_report.md`
- 正式最佳基线比较：
  `bop_exp/main_v2/analysis/best_cc_baseline_comparison.csv`
- BOP-QB 对四个正式基线：
  `bop_exp/main_v2/analysis/pairwise_bop_vs_cc.csv`
- Open-loop 附录：
  `bop_exp/main_v2/analysis/open_loop_tradeoff.csv`
- PFC 语义状态：
  `bop_exp/main_v2/analysis/pfc_semantic_audit.csv`
- n32 DCQCN 审计：
  `bop_exp/main_v2/analysis/dcqcn_n32_reproducibility.csv`
- 复用摘要：
  `bop_exp/main_v2/analysis/reuse_summary.csv`
- 最小重跑清单：
  `bop_exp/main_v2/config/rerun_manifest.csv`
- 论文实验章节：
  `paper/experiments/chapter_5_experiments_results.md`

本报告没有修改算法、参数或仿真输入，也没有运行任何仿真实验。
