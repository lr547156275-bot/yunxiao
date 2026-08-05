# CBAP-SBA 容量迁移机制设计（Capacity Migration）

状态：设计稿，待实现。本文档描述"switch-assisted batch admission +
RTT-synchronized capacity handover + nonlinear rate transition"的实现方案。

## 1. 要解决的问题

现有 CBAP-SBA 只是一个 admission gate：它决定新批次能拿多少，但对已经
handoff 给 DCQCN 的旧流没有任何影响力。实测（S1 场景）后果：

- 旧背景流被应用层 cap 钉在 8Gbps，不会因新批次到达而让步；
- 新批次被批次权重限制到 residual(2G) 的 50% = 1G；
- 链路上出现约 1G 悬空容量：既不属于新流，也没有被旧流用掉。

问题不是"新流为什么慢"，而是 **SBA 只控制新流准入、不控制旧流让渡**。

## 2. 设计原则

1. **决策同步、执行渐进**：迁移目标（旧流降到多少、新流升到多少）在一个
   RTT 内一次性算好并同步下发；实际速率变化通过非线性函数在若干 RTT 内
   收敛，不要求瞬时硬切。
2. **不修改 DCQCN 核心函数**：DCQCN 的 CNP/AI/HAI 逻辑继续直写
   `q->m_rate`。SBA 在其之上叠加一层 envelope（rate cap），实际发送速率为
   `min(DCQCN_rate, SBA_envelope)`。
3. **独立 epoch 纠正**：每个 `CbapEpochTick`（默认 5us）检查一次，把超出
   当前 envelope 的速率拉回。迁移目标是多 RTT 收敛，epoch 级纠正的精度
   足够。
4. **队列作为交接缓冲池**：迁移期间允许受控的短时超配，核心约束不是
   "任意时刻 ΣR ≤ C"，而是 **Q(t) ≤ Qmax**。

## 3. 迁移目标计算（决策同步阶段）

新批次到达时（`PlanCbapSbaBatch`），对每条被新批次触及的 link：

```
R_old        = 该 link 上所有旧流（非 FINISHED/HOLD、batchId 不同）的当前聚合速率
R_old*       = (1 - eta) * R_old              // eta = migrationReleaseRatio，默认 0.5
R_new*       = C_effective - R_old*            // C_effective 来自动态预算（RED 三区间）
```

- 旧流内部：以 `R_old*` 为容量上限跑 `ProgressiveFill`，得到每条旧流的目标；
- 新流内部：以 `R_new*` 为容量上限跑 `ProgressiveFill`，得到每条新流的目标。

**不采用**逐流 max-min（会让旧流降幅过大），**也不采用**固定 old:new=1:1
分饼。释放比例 eta 是唯一的分配旋钮。

## 4. 非线性速率迁移（执行阶段）

每个 epoch，对处于迁移状态的流更新 envelope：

```
旧流（降速）：E(t+1) = E(t) - f_dec * (E(t) - R_old_target)
新流（升速）：E(t+1) = E(t) + f_inc * (R_new_target - E(t))
```

`f_dec` / `f_inc` 是 [0,1] 的收敛系数（指数趋近，每步走掉剩余差距的固定
比例）。**它们不是全程固定值，而随队列在 Qmin~Qmax 中的位置连续变化**，
与第 5 节的队列容忍约束贯彻同一套思想：

```
u = clamp((Q - Qmin) / (Qmax - Qmin), 0, 1)      // 队列压力，0=空闲 1=触顶

f_dec = migrationDecayBase                        // 旧流释放速度：恒定
f_inc = migrationRiseBase * (1 + skew * (1 - 2u)) // 新流升速：随 u 衰减
```

- `u = 0`（Q < Qmin，队列空闲）：`f_inc > f_dec`，新流升速快于旧流释放，
  主动填补悬空容量，短时超配由队列吸收；
- `u = 0.5`（Q 在区间中点）：`f_inc == f_dec`，增量与释放量持平，不再新增
  超配；
- `u = 1`（Q >= Qmax）：`f_inc < f_dec`，旧流释放快于新流吸收，净排空队列。

默认 `migrationDecayBase = 0.3`、`migrationRiseBase = 0.3`、`skew = 0.35`，
即 `f_inc` 在 0.405（空闲）到 0.195（触顶）之间连续变化。

收敛判定：`|E(t) - target| < 收敛阈值` 时迁移结束，envelope 解除，恢复
DCQCN 主导。

**`migrationMaxRtt` 到期不解除 cap**：超时只意味着"当前目标没能在预期时
间内收敛"，此时**重新计算迁移目标**（用当前实际速率和当前 C_effective
重跑第 3 节的目标计算）并重置计时，而不是简单放开 envelope——直接解除会
让旧流瞬间弹回、重现悬空/超配问题。

## 5. 队列容忍区间约束超配

迁移期间每个 epoch，对每条 link 检查：

```
I_k <= D_k + 8 * (Qmax - Q_k) / T_k
```

- `I_k`：该 link 上所有新流本 epoch 的增量总和
- `D_k`：该 link 上所有旧流本 epoch 的释放量总和
- `8*(Qmax - Q_k)/T_k`：当前可借用的队列空间折算成速率（Q 越高越少，
  Q >= Qmax 时为 0，此时新流增量不得超过旧流释放量）

若 `I_k` 超出，按比例缩放该 link 上所有新流的本次增量。

## 6. 需要新增的状态

`RdmaQueuePair::cbap` 新增：

| 字段 | 含义 |
|---|---|
| `migrationActive` | 是否处于迁移状态 |
| `migrationTargetBps` | 迁移目标速率 |
| `migrationEnvelopeBps` | 当前 envelope（实际 cap） |
| `migrationStartNs` | 迁移开始时刻（用于超时兜底） |
| `migrationIsOldFlow` | 是旧流（降速）还是新流（升速） |

`CbapConfig` 新增：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `migrationEnabled` | false | feature flag，默认关闭不影响现有基线 |
| `migrationReleaseRatio` | 0.5 | eta，旧流释放当前速率的比例 |
| `migrationDecayBase` | 0.3 | f_dec（恒定） |
| `migrationRiseBase` | 0.3 | f_inc 的基准值 |
| `migrationRiseSkew` | 0.35 | f_inc 随队列压力摆动的幅度 |
| `migrationMaxRtt` | 5 | 多少个 RTT 未收敛则重算目标（不解除 cap） |

## 7. 反向索引

按 link 聚合旧流/新流速率需要"给定 linkId 找出所有经过它的 flow"。现有
`s_cbapFlowPaths` 只有 flow→link 正向索引，反查需线性扫全部 flow。S1-S6
规模（≤100 flow）下线性扫描可接受，第一版不引入反向索引，但在
`EvaluateCbapSbaMigration` 里集中做一次扫描、复用结果，避免每条 link 重复扫。

## 8. 不变量检查

- envelope 不得为 0（否则触发 `UpdateNextAvail` 里的非零断言）；下限为
  `MIN_RATE`。
- `migrationActive` 的流不得同时被 `ReadmitHeld` 处理（后者断言
  `!qp->cbap.handedOff`，迁移中的旧流是 handedOff 状态）。
- 迁移结束必须清理状态，避免残留 envelope 永久压制流速。
- feature flag 关闭时，所有新增代码路径不得执行，S1 结果须与迁移前完全一致。

## 9. 有界误差：epoch 间的 envelope 突破

envelope 是 epoch 级纠正，不是即时拦截：DCQCN 在两次 epoch 之间可以短暂
超过 envelope。这是"不改 DCQCN 核心函数"的直接代价，**但它是一个有界
误差，不是不受控的漂移**：

```
突破窗口     <= 一个 epoch（默认 5us）
额外入队字节 <= (实际速率 - envelope) * epoch / 8
```

由于迁移目标本身是多 RTT 收敛（RTT 通常十几到几百 us），5us 的突破窗口
相对收敛周期很小。第二道防线是队列容忍区间：突破产生的额外入队会抬高 Q，
进而通过第 4 节的 `u` 压低 `f_inc`、通过第 5 节的约束削减新流增量，形成
负反馈。

**必须统计并输出**（迁移日志字段）：

- 每次 epoch 纠正时的突破量 `actual_rate - envelope`（>0 才记）；
- 突破折算的额外入队字节；
- 全程最大 Q 与 Qmax 的距离（验证"始终受 Qmax 约束"这个不变量是否成立）。

若实测发现最大 Q 触及或超过 Qmax，说明有界误差的假设在该场景下不成立，
需要回到"修改 DCQCN 核心函数做即时拦截"的方案。

## 10. 其他已知局限

- 只覆盖 flow-consistent ECMP（已确认本平台是 5-tuple 哈希，逐流路径固定）。
  packet spraying 下 per-flow path 记账不成立，需另设计。
- eta 是静态配置，不随场景/队列状态自适应。
