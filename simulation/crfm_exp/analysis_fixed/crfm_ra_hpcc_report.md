# Fixed CRFM / RA-HPCC screening audit

## 1. 唯一判定

**INCONCLUSIVE**

这是完整的 fixed screening（8 场景 × 4 算法），但只有 seed=1。运行和
遥测已经有效，HPCC 中也出现了明显的迟到反馈、OFF 阶段速率修改和后续轮次
低起始速率。可是性能代价并不一致：只有 `gap_20us` 的后续轮次平均 RCT
高于第一轮，其他 gap 的后续 RCT 反而降低。严格问题标准也并非全部满足：
`gap_20us` 的
actionable-byte ratio 为 0.169，高于 0.10；并且没有多 seed 方向一致性证据。

算法筛选层面不支持 RA-HPCC 直接进入确认实验：三个主要短 gap 中只有
`gap_20us` 的 P95 改善超过 10%，RA 在 gap 场景中没有明显优于 Gate，并在
`size_256k` 和 long-burst control 中退化。由于禁止把单 seed 写成稳定结论，
正式类别仍是 `INCONCLUSIVE`，不能提升为稳定的算法失败判定。

## 2. 数据完整性

- 32/32 fixed runs 存在；全部流和轮次完成： **True**。
- exit status 全为 0、无 NaN/Inf、无零速率死锁： **True**。
- 无日志截断： **True**。
- 四种算法均记录非零 INT hop： **True**。
- 同场景 seed=1 跨算法输入 plan SHA256 相同： **True**。
- 所有后续 release 均晚于上一轮 ACK completion： **True**。
- ACK-relative gap 与 `compute_gap+jitter` 最大误差： **0 ns**。
- PFC 事件总数： **0**。
- 只有 seed=1，不能计算跨 seed 标准差或 95% CI。

## 3. 同一 QP、序列与轮次调度

全部运行中，每个逻辑 flow 的 `qp_id` 跨轮保持不变，round sequence interval
连续，采样的 `snd_nxt/snd_una/released_bytes` 不回退。Round completion 使用
累计 ACK completion。第 k+1 轮实际 release 严格等于第 k 轮 ACK completion
加输入 plan 的 compute gap 和 jitter；所有 injection-relative gap 也为正。

## 4. HPCC 反馈时序

| 场景 | late ratio | actionable ratio | actionable bytes | late action | mean RCT us | P95 RCT us | R1/R2/R3/R4 start Gbit/s |
|---|---:|---:|---:|---:|---:|---:|---|
| gap_20us | 0.590 | 0.410 | 0.169 | 0.544 | 90.2 | 242.5 | 100.0/20.8/5.5/5.4 |
| gap_50us | 0.757 | 0.243 | 0.080 | 0.679 | 59.5 | 92.0 | 100.0/28.1/25.6/19.0 |
| gap_100us | 0.855 | 0.145 | 0.046 | 0.655 | 43.2 | 89.5 | 100.0/29.2/36.4/44.7 |
| gap_500us | 0.935 | 0.065 | 0.020 | 0.553 | 41.1 | 92.2 | 100.0/32.3/65.3/64.8 |
| size_16k | 1.000 | 0.000 | 0.000 | 0.290 | 13.5 | 21.2 | 100.0/77.5/98.0/99.6 |
| size_256k | 0.040 | 0.960 | 0.412 | 0.014 | 369.4 | 524.0 | 100.0/8.4/7.1/13.6 |
| long_burst_control | 0.002 | 0.998 | 0.498 | 0.002 | 5927.2 | 7205.5 | 100.0/6.3/6.2/6.2 |
| single_round_control | 1.000 | 0.000 | 0.000 | 0.985 | 74.0 | 91.8 | 100.0 |

`gap_20us`/`gap_50us` 的 late-feedback ratio 分别为 0.590/0.757，
HPCC 确实在 OFF 阶段修改实时速率；后续 start rate 明显低于第一轮。
`gap_50us` 的 actionable-byte ratio 为 0.080，满足严格阈值，但
`gap_20us` 为 0.169，不满足。

## 5. Gap 趋势与跨轮污染

| 场景 | late ratio | actionable bytes | HPCC start Gbit/s | later-round mean RCT penalty % | ACK gap us | injection gap us |
|---|---:|---:|---|---:|---:|---:|
| gap_20us | 0.590 | 0.169 | 100.0/20.8/5.5/5.4 | 57.5 | 19.9 | 59.4 |
| gap_50us | 0.757 | 0.080 | 100.0/28.1/25.6/19.0 | -25.3 | 49.9 | 89.4 |
| gap_100us | 0.855 | 0.046 | 100.0/29.2/36.4/44.7 | -51.3 | 99.9 | 134.4 |
| gap_500us | 0.935 | 0.020 | 100.0/32.3/65.3/64.8 | -59.9 | 500.0 | 537.0 |

随 gap 增大，actionable-byte ratio 从 0.169/0.080 降到 0.046/0.020；
500 us 时后续轮次仍保留较低起始速率，但 RCT penalty 已反向为改善。
这说明“跨轮速率状态保留”存在，却没有在多个 gap 中形成一致的性能代价，
因此不能确认稳定相变或普遍 CRFM 性能问题。

## 6. Burst-size 趋势

| 场景 | 大小 | injection us | feedback loop us | actionable ratio | queue max B | mean RCT us |
|---|---|---:|---:|---:|---:|---:|
| size_16k | 16 KiB | 1.5 | 10.1 | 0.000 | 97674 | 13.5 |
| gap_50us | 64 KiB | 26.9 | 17.9 | 0.243 | 519348 | 59.5 |
| size_256k | 256 KiB | 360.9 | 15.1 | 0.960 | 1593580 | 369.4 |
| long_burst_control | 4 MiB | 5918.8 | 14.6 | 0.998 | 1609930 | 5927.2 |

actionable-feedback ratio 从 16 KiB 的 0 增加到 256 KiB 的 0.960，
long-burst control 达到 0.998。修复后的 long-burst 所有轮次均有正 gap，
因此该 control 现在形成了预期的“反馈可作用于当前轮”条件。

## 7. RA-HPCC、Gate、Reset 对比

| 场景 | HPCC P95 us | RA P95 us | RA vs HPCC P95 | RA vs Gate P95 | RA vs HPCC goodput | RA vs HPCC queue max |
|---|---:|---:|---:|---:|---:|---:|
| gap_20us | 242.5 | 88.0 | -63.70% | +0.00% | +37.84% | +36.02% |
| gap_50us | 92.0 | 89.5 | -2.69% | +0.00% | +43.08% | +0.00% |
| gap_100us | 89.5 | 88.9 | -0.64% | +0.00% | +20.18% | +0.00% |
| gap_500us | 92.2 | 92.2 | +0.00% | +0.00% | +3.43% | +0.00% |
| size_16k | 21.2 | 21.2 | +0.00% | +0.00% | +0.55% | +0.00% |
| size_256k | 524.0 | 794.4 | +51.62% | +42.56% | -13.71% | +0.00% |
| long_burst_control | 7205.5 | 7900.2 | +9.64% | +10.31% | -5.03% | +0.00% |
| single_round_control | 91.8 | 91.8 | +0.00% | +0.00% | +0.00% | +0.00% |

核心数值：

- `gap_20us`：RA P95 相对 HPCC **-63.70%**，但 queue max **+36.02%**；
- `gap_50us`：RA P95 **-2.69%**，未达到 10%；
- `gap_100us`：RA P95 **-0.64%**；
- `size_256k`：RA P95 **+51.62%**、goodput **-13.71%**；
- `long_burst_control`：RA P95 **+9.64%**、goodput **-5.03%**；
- RA 与 Gate 在四个 gap 场景的 P95 基本相同，未证明完整 carry 优于简单 Gate；
- single-round 四种模式完全相同，没有引入单轮性能代价；
- Reset 将四个 gap 的每轮 start rate 都恢复到 100 Gbit/s；相对 HPCC 的
  mean RCT 变化依次为 **-25.58%/-20.55%/-18.29%/-12.16%**。
  这支持“保留低速率状态会影响均值”，但它是诊断 oracle，不能视为
  可部署算法；P95 证据除 gap20 外并不强。

## 8. Goodput、queue、PFC 和控制代价

所有 32 次运行均无 PFC 事件。RA 在大部分场景没有提高 queue max；
`gap_20us` 是明显例外，相对 HPCC 增加 36.02%。RA 在 `size_256k` 和
long-burst 中降低 active utilization/goodput，说明其较高下一轮初始速率并
未转换为更好的完成时间，反而形成吞吐/RCT 退化。

## 9. 能得出和不能得出的结论

可以得出：

1. INT 缺失和负 gap 已修复，fixed 数据可用于算法比较。
2. seed=1 中 HPCC 存在明显跨轮低速率状态；性能代价只在 `gap_20us`
   明确出现，在其余 gap 中不一致。
3. burst-size control 呈现预期 actionability 增长。
4. 当前 RA-HPCC 在 screening 上没有显示出相对 Gate 的增量价值。

不能得出：

1. CRFM 性能代价在不同 gap 或不同 seed 下稳定成立；
2. RA-HPCC 稳定失败或稳定优于 HPCC；
3. 95% CI 或多 seed 方向一致性；
4. 参数调整后是否可能改善——本审计没有也不允许调参。

## 10. 下一步最小工作

不要先做 96 次 confirm。当前最小必要工作是把这份 seed=1 screening 交给
研究决策者，决定是否因 `size_256k`/long-burst 退化和 RA≈Gate 而停止
RA-HPCC；若仍要求统计确认，只应原样补 seed=2/3，不修改参数。

## Figures

- [Feedback arrival relative to injection](figures/feedback_arrival_relative_injection.svg)
- [Late feedback ratio vs gap](figures/late_feedback_ratio_vs_gap.svg)
- [Next-round start rate vs round](figures/next_round_start_rate_vs_round.svg)
- [Round completion vs round](figures/round_completion_vs_round.svg)
- [Pollution penalty vs gap](figures/pollution_penalty_vs_gap.svg)
- [Burst size vs actionable ratio](figures/burst_size_vs_actionable_ratio.svg)
- [Algorithm comparison](figures/algorithm_comparison.svg)
- [Queue trajectory](figures/queue_trajectory.svg)
- [Selected-flow rate trajectory](figures/selected_flow_rate_trajectory.svg)
