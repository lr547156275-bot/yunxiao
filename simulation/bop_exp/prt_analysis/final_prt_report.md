# BOP-QB-PRT final analysis

## 唯一判定

**`BOP_PRT_REDESIGN_REQUIRED`**

30/30 运行完整且实现审计全部通过，但 residual 场景中的第二个 probe 从未在
release 前返回，实际运行始终退化为单 probe 保守估计。该估计在
`residual_64k` 反而使 q0 绝对误差增加 25.43%，两个 residual 场景合并后的
误差下降只有 56.16%，未达到要求的 70%。因此不能冻结当前 PRT。

## 数据完整性与实现审计

- 运行矩阵：30/30；所有 `exit_status=0`、所有流完成、无日志截断。
- 同一 scenario+seed 跨算法的 topology、flow、round、fixed-path SHA256
  完全相同；每个场景 seed 1/2/3 的 round hash 均不同。
- 从逐流 ACK completion 重算的 barrier 和 group RCT 与
  `group_round_summary.csv` 一致；不存在跨轮重叠。
- 所有被采用的 probe 满足
  `send <= queue_sample <= ACK < release`；每 group 不超过 2 个。
- 30 次运行中的全部 PRT group 均通过 q_hat、target clamp、group credit
  以及 flow-credit 求和重放；初始估计不可行时只允许零信用。
- 所有算法、所有 seed 的 PFC 均为 0。
- 无效运行：0。详见 `invalid_runs.csv`。

## 三 seed 结果

| 场景 | 算法 | q0绝对误差 B | mean RCT us | queue max B | total ECN | PRT primer/collective ECN | probe返回率 |
|---|---|---:|---:|---:|---:|---:|---:|
| residual_64k | BOP-QB | 71,940 | 109.500 | 323,003 | 0 | 未记录owner | — |
| residual_64k | Oracle | 0 | 109.500 | 231,296 | 0 | 未记录owner | — |
| residual_64k | PRT | 90,231 | 109.507 | 160,701 | 0 | 0 / 0 | 50% |
| residual_160k | BOP-QB | 179,850 | 134.562 | 640,130 | 28.333 | 未记录owner | — |
| residual_160k | Oracle | 0 | 134.562 | 430,637 | 1.333 | 未记录owner | — |
| residual_160k | PRT | 20,150 | 134.569 | 444,807 | 5.667 | 3.000 / 2.667 | 50% |
| gap_50us | BOP-QB | 0 | 95.856 | 160,230 | 0 | 未记录owner | — |
| gap_50us | PRT | 7,406 | 95.907 | 159,867 | 0 | 0 / 0 | 90.48% |
| n32_64k | BOP-QB | 0 | 187.210 | 168,587 | 0 | 未记录owner | — |
| n32_64k | PRT | 0 | 187.210 | 168,587 | 0 | 0 / 0 | 85.71% |

PRT 最新有效 queue sample 的平均年龄为：`residual_64k` 12.974 us、
`residual_160k` 21.543 us、`gap_50us` 约 7.296 us、`n32_64k`
7.313 us。

## PRT 对原 BOP-QB

### residual_64k

- q0 误差：71,940 B → 90,231 B，**恶化 25.43%**，3/3 seed 同向。
- queue max：323,003 B → 160,701 B，降低 **50.25%**；
  配对差值 95% CI 为 `[-162,767, -161,837] B`。
- mean RCT：增加 0.007 us（+0.0064%），3/3 seed 均为同一固定增量；
  远低于 3% 限制。
- group credit：183,616 B → 21,445 B，降低 88.32%。
- ECN、PFC：均为 0。

queue 改善来自显著减少信用，而不是更准确的 q0 估计。

### residual_160k

- q0 误差：179,850 B → 20,150 B，改善 **88.80%**，3/3 seed 同向。
- queue max：640,130 B → 444,807 B，降低 **30.51%**；
  配对差值 95% CI 为 `[-196,241, -194,405] B`。
- mean RCT：增加 0.007 us（+0.0052%）。
- group credit：183,616 B → 0。
- 总 ECN：28.333 → 5.667，降低 80%；PRT 的 5.667 中 primer 为 3.000、
  collective 为 2.667。

原版没有 owner 拆分，因此“collective ECN 相对原版降低 80%”不能严格重算。
若仅把原版总 ECN 当作 collective 的上界，PRT collective 相对该上界低
90.59%；这不是 owner-to-owner 证明。

## PRT 对 Oracle

- `residual_64k`：PRT queue 比 Oracle 低 30.52%，RCT 仅高 0.007 us；
  但 PRT q0 误差为 90,231 B，Oracle 为 0，且 PRT 信用低 80.80%。
- `residual_160k`：PRT queue 比 Oracle高 3.29%，满足 10% queue gap；
  RCT 高 0.007 us。PRT 总 ECN均值 5.667，Oracle 为 1.333。

PRT 的 queue 接近或低于 Oracle，不等价于估计接近 Oracle：
`residual_64k` 是过度保守信用造成的低 queue。

## Control 场景

- `gap_50us`：PRT mean RCT 相对原版增加 0.051 us（+0.0532%），
  配对 95% CI `[-0.168, 0.270] us`；queue 下降 0.23%。
- `n32_64k`：RCT、queue、credit 与原版逐 seed 完全相同。
- 两个 control 场景均远低于 3% 退化限制，且无 ECN/PFC。

## 判定门槛

| 条件 | 结果 |
|---|---|
| residual q_hat误差降低≥70% | **失败**：64k 恶化25.43%；160k改善88.80%；合并仅改善56.16% |
| residual queue降低≥20% | 通过：50.25%、30.51% |
| collective ECN降低≥80% | 无法严格证明：原版缺少owner拆分 |
| RCT退化≤3% | 通过：两个 residual 均约+0.006% |
| 与Oracle queue差距≤10% | 通过（一侧上限）：64k低30.52%，160k高3.29% |
| gap50/n32退化≤3% | 通过：+0.053%、0% |
| 无因果/公式/barrier/PFC问题 | 通过 |

## 结论与下一步

当前 PRT 证明了“在 release 前获得更保守的队列信息可以显著压低 queue，且
几乎不影响 RCT”，但没有证明当前 probe 调度和单样本外推能可靠估计
post-release residual work。最小下一步应只针对 probe 可返回性和单样本
uncertainty 模型重新设计；在获得 residual 双样本趋势之前，不应冻结
`bop_qb_prt_v1`，也不应把总 ECN包装成 collective ECN。
