# CBAP-SBA 理论与算法证据补丁(v3)

依据:仓库 `lr547156275-bot/yunxiao`,分支 `cbap-queue-delay-credit`,
HEAD `f0557692e7121ffeaecb675f51999b92f26d5446`。
全部公式、常量与伪代码逐项对照源码提取;行号以该提交为准。
本文件不修改任何实验数据;适用范围与边界见第 11 节。

---

## 1 符号表

| 符号 | 含义 | 单位 | 代码对应 |
|---|---|---|---|
| L, l | 受控链路集合及其元素 | — | `s_cbapLinks`(rdma-hw.cc) |
| F, i | 活动流集合及其元素 | — | `s_cbapFlows` / `CbapSbaController::m_flows` |
| P_i | 流 i 的固定路径(链路序列) | — | `FlowState::path`(cbap-sba.cc) |
| C_l | 链路 l 线速(wire) | bit/s | `runtime.config.capacityBps` |
| q_l(t) | 链路 l 瓶颈出口队列 | Byte | `link.latest.queueBytes` |
| r_i(t) | 流 i 的许可发送速率(wire) | bit/s | `qp->m_rate` |
| r_i* | 流 i 的迁移目标速率 | bit/s | `qp->cbap.migrationTargetBps` |
| A_l(t) | 链路 l 的许可到达率合计 | bit/s | 账本合计(见 §3) |
| H_eff | 实测执行时域(瓶颈可见 p99) | s | `CBAP_QC_H_GUARD_US`;v2 实测 118/15/12 µs |
| τ | 最早未生效降速命令的剩余期限 | s | rdma-hw.cc:891–897 |
| M_safe | 打包化安全余量 | Byte | `CBAP_QC_SAFETY_MARGIN_BYTES`=fanin×1000 |
| Q_abs | 队列硬上界 | Byte | 由 `CBAP_QC_APP_HARD_DELAY_US`×C/8 导出 |
| Q_low/Q_high/Q_red | 控制分区边界 | Byte | Q_low=0.5·Q_abs;Q_red=Q_abs−M_safe;Q_high=Q_red−BMAX·C·H_eff/8 |
| Q_target | 预测提升的队列目标 | Byte | `CBAP_QB2_QTARGET_RATIO`×Q_abs(v2: 8 µs×C/8) |
| BMAX | 预测提升相对上限 | 无量纲 | `CBAP_QB2_BMAX_RATIO`=0.02 |
| ρ_init | 旧侧初始让出比例 | 无量纲 | `CBAP_INITIAL_RELEASE_RATIO`=0.90 |
| α_k | 第 k 个控制周期的迁移收缩系数 | 无量纲 | rdma-hw.cc:3440–3448 |
| u_k | 路径队列压力 | 无量纲 | rdma-hw.cc:3419–3432 |
| T_ctrl | 控制周期 | s | `CBAP_CONTROL_EPOCH_US`=5 µs |
| T_lease | 启动无反馈兜底期限 | s | `sbaLeaseNs` 默认 1 ms(rdma-hw.h:357) |

单位约定:速率一律为 wire 域 bit/s(载荷速率 = wire×952/1000,
v2 包几何:载荷 952 B + 头部 48 B = wire 1000 B,
`CbapLinkBytesPerPacket`,rdma-hw.cc:359–374);队列一律为 Byte,
速率积分转字节须除以 8。

## 2 逐链路流体队列模型

固定路由下,链路 l 的许可到达率为

  A_l(t) = Σ_{i: l∈P_i} r_i(t)                    (bit/s)

队列演化(单位 Byte,分段常值输入下逐段线性):

  dq_l/dt = (A_l(t) − C_l)/8,          q_l(t) > 0
  dq_l/dt = max(A_l(t) − C_l, 0)/8,    q_l(t) = 0

该模型的离散对应即控制器的预测方程(§3),预测按控制周期
T_ctrl=5 µs 刷新,周期内输入视为常值。

## 3 双阶段盲窗预测(QueueControllerEpoch,rdma-hw.cc:679 起)

控制器对每条受控链路维护逐 QP 账本(oldWireBps / commandedWireBps /
predictedArrivalWireBps),并构造两条到达包络
(rdma-hw.cc:857–887):

- **安全包络** A_safe:未到生效期限的**降速**命令不予采信,取
  max(old, cmd);**升速**命令立即计入(保守方向);其余取
  predictedArrival。
- **期限后包络** A_ddl:降速命令按命令值计入,其余同上。

取 τ = min(最早降速生效期限 − now, H_eff)(若无待生效降速则
τ = H_eff,rdma-hw.cc:891–897),两阶段预测
(rdma-hw.cc:896–916):

  q1 = q0 + (A_safe − C_l)·τ/8
  q2 = q1 + (A_ddl − C_l)·(H_eff − τ)/8
  q_stop = max(q0, q1, q2)          (前缀最大,恒有 q_stop ≥ q0)
  q_safe = q_stop + M_safe

注意:q1、q2 允许为负(流体下溢),但 q_stop 因包含 q0 而非负;
实现记录前缀最大位置(qcPrefixMaxIndex)并对 q_stop < q0 计数为
不变量违例(构造上不可能)。

**分区与 RED 滞回**(rdma-hw.cc:918–939):进入 RED 当且仅当
q_safe ≥ Q_abs 或 q0 ≥ Q_abs 或 PFC 危险;退出 RED 要求
q_stop ≤ Q_high 且 q0 ≤ Q_high 且无待生效升速。RED 区强制
boost=0、按 drainMax 排空(rdma-hw.cc:942–956)。

**预测余量(提升)上界**(rdma-hw.cc:1023–1083)。其真实语义为:
在 GREEN 区,于基准聚合预算之上追加的**许可 wire 速率增量** B_l
(它不是总准入速率,也不是对单流的配额;实现中 desired =
R_budget − C_l,聚合预算围绕 C_l 表达且刻意不钳位于 C_l):

  B_l = min{ BMAX·C_l,  max(0, (Q_target − q_stop))·8/H_eff }
  否决:room_red = (Q_red − q_stop)·8/H_eff;
        room_red ≤ 0 ⇒ B_l = 0;B_l > room_red ⇒ B_l = room_red

即论文可写为
  B_l ≤ max{0, min[ BMAX·C_l, 8(Q_target−q_stop)/H_eff,
                    8(Q_red−q_stop)/H_eff ]}
与源码逐项一致。B_l 附带**余量租约**:有效提升在
now + H_eff 内未刷新即作废(qb2LeaseExpireNs,
rdma-hw.cc:846–848、1044–1049)。HOLD 区提升按每周期 ×0.99 缓释,
DRAIN 区提升为 0 并按压力比例温和排空(≤ min(2·BMAX·C_l,
drainMax),rdma-hw.cc:1065–1080)。

## 4 批次准入预算(AdmitBatch,cbap-sba.cc:183–388)

设链路 l 的可用容量为 C_avail,l(v2 中 `SBA_WIRE_DOMAIN_PLANNING=1`,
遥测有效容量换算回 wire 域,rdma-hw.cc:2918–2936),旧侧观测占用为
R_old,l(生命周期护栏:FINISHED/ADMISSION_HOLD/COLLECTING 不入册,
cbap-sba.cc:196–213)。核心模式初始预算
(cbap-sba.cc:283–303):

  released_l = ⌊ρ_init · R_old,l⌋
  B_init,l  = min( C_avail,l,  (C_avail,l − R_old,l) + released_l )

即"未占余量 H_l = C_avail,l − R_old,l 加上旧侧让出的 ρ_init 份额,
且永不超过链路可用容量"。注意 H_l 为**容量余量**(bit/s),与预测
时域 H_eff(时间)无关,论文中不得混写。守恒检验
(cbap-sba.cc:331–386):除逐链路 CheckConservation 外,核心模式
校验计划态占用界

  Σ_i grants_i + (1−ρ_init)·R_old,l ≤ max(C_avail,l, R_old,l) + |F_new|

(右端第一项为占用界 occupancyBound,+|F_new| 容忍逐流向下取整;
违反即抛出异常终止,属 fail-fast 而非静默钳位。)

## 5 迁移公式(EvaluateCbapSbaMigration,rdma-hw.cc:3419–3471)

路径队列压力(逐链路带内归一,带界来自链路配置
ecnThresholdBytes 的预算分数,默认 0.5/1.0,rdma-hw.h:358;
v2 链路文件取值 400 000 B,对应带 [200 kB, 400 kB]):

  u_k = max_{l∈P_i} clip( (q_l − 0.5·q_l^ecn)/(1.0·q_l^ecn − 0.5·q_l^ecn), 0, 1 )

收缩系数(rdma-hw.cc:3440–3448;默认 0.30/0.30/0.35,
rdma-hw.h:369–370):

  α_k = 0.30·[1 + 0.35·(1 − 2u_k)] ∈ [0.195, 0.405]   (r* ≥ r,升速)
  α_k = 0.30                                            (r* < r,降速)

更新与钳位(rdma-hw.cc:3452–3471):

  r_i[k+1] = clip( r_i[k] + α_k·(r_i*[k] − r_i[k]),
                   区间 [min(r_i[k], r_i*), max(r_i[k], r_i*)] )
  r_i[k+1] ← clip(r_i[k+1], minRate, maxRate_i)

实现保证 next 落在 current 与 target 之间(双向区间钳位),再受
minRate(=0.01·C)与 QP 协议上限约束;不存在越过 target 的路径。
方向仅由 sign(r*−r) 决定,与新旧批次角色无关(源码注释明确)。
迁移目标在活动集变化或期限(migrationMaxRtt=5 个 RTT 窗口,
rdma-hw.h:370)到达时重算。

## 6 性质 1(准入容量可行性)

**命题**:固定路由、预算在单次求解期间冻结时,ProgressiveFill
(cbap-sba.cc:87–166)的输出满足:对每条链路 l,
Σ_{i: l∈P_i} grants_i ≤ B_l(交给求解器的预算 newBatchResidual),
且 grants_i ≤ maxRate_i。

**证明概要**:速率向量自零起,每轮迭代所有活跃流增加同一增量
step = min( min_l remaining_l/count_l, min_i (maxRate_i − r_i) )
(cbap-sba.cc:104–135)。按定义 step ≤ remaining_l/count_l 对每条
链路成立,故本轮增加后 used_l ≤ B_l 仍成立;链路饱和
(linkStep ≤ step + 0.5,0.5 为 long double 容差)即冻结所有过路
流,其速率此后不变;流达自身上限亦冻结。迭代至多 |F|+1 轮
(每轮至少冻结一流,否则 break),终态各链路占用不超预算。最后
逐流下取整只会进一步减小占用(cbap-sba.cc:158–164)。核心模式
另有第 4 节的计划态占用界的运行时断言兜底。∎

成立条件:预算冻结、路径固定、单线程原子准入(实现即如此);
不涉及执行期的 DCQCN 扰动(由第 5 节迁移与第 3 节控制器处理)。

## 7 性质 2(冻结预算下的 max-min 公平)

**命题**:在单次 ProgressiveFill 求解内,输出分配对约束
{Σ_{i:l∈P_i} r_i ≤ B_l, 0 ≤ r_i ≤ maxRate_i} 是 max-min 公平的。

**证明概要**:等增量水填充的标准论证。设输出为 r,若存在可行 r'
使某流 j 的 r'_j > r_j,考察 j 被冻结的原因:(i) 若因自身上限,
则 r'_j 不可行;(ii) 若因瓶颈链路 l 饱和,则 l 上
Σ r = B_l,且 l 上所有仍活跃至该轮的流速率相同并 ≤ r_j(等增量
性),故提高 r'_j 必使 l 上某流 m(r_m ≤ r_j)减小,即任何提高
j 的可行方案都以牺牲不高于 j 的流为代价——这正是 max-min 公平的
定义。∎

**范围限定**:该性质仅对"一次准入求解 / 一个冻结控制周期"成立;
动态闭环(迁移、DCQCN 接管、批次到达/完成)不在此命题范围内,
论文不得外推为"系统始终全局 max-min 公平"。

## 8 性质 3(单盲窗队列安全,条件性上界)

**命题**:设 t0 为某控制周期起点,若在 [t0, t0+H_eff] 内
(A1)实际许可到达率不超过第 3 节包络:在 [t0, t0+τ] 内
A_l(t) ≤ A_safe,在 [t0+τ, t0+H_eff] 内 A_l(t) ≤ A_ddl;
(A2)链路满负荷服务速率为 C_l(工作保持);
(A3)离散打包化误差不超过 M_safe(v2 取每流一个 wire 包:
fanin×1000 B);
则对任意 t∈[t0, t0+H_eff]:

  q_l(t) ≤ q_stop + M_safe = q_safe。

若该周期决策满足 q_safe ≤ Q_red(GREEN 提升被第 3 节否决项强制
满足;Q_red = Q_abs − M_safe),则 q_l(t) ≤ Q_red < Q_abs。

**证明概要**:分段线性流体轨迹在 [t0, t0+τ] 与 [t0+τ, t0+H_eff]
两段各为常斜率,其最大值只能出现在段端点,即 {q0, q1, q2} 之一,
故 sup q ≤ q_stop;叠加打包化误差上界 M_safe 得 q_safe。∎

**边界说明**:这是**单个 H_eff 窗口内、包络假设成立时的条件性
上界**,不是全局稳定性或一切速率下的 PFC-free 结论。v2 实验中
该界在 200/400 G 全部成立(qdelay ≤ 43 µs ≪ D_abs);10 G 存在
5 个准入瞬态越界单元(超出 ≤ 一个盲窗 C·H_eff/8,
matrix_report_v2.md §3),原因是 (A1) 中的包络在准入瞬态跨越了
可行域(H_eff=118 µs 相对 D_abs=826 µs 不再可忽略),论文必须
如实呈现。

## 9 引理(固定目标下迁移的几何收敛)

**命题**:固定 r*,忽略 minRate/maxRate 钳位时,误差
e[k] = r* − r[k] 满足 e[k+1] = (1−α_k)·e[k];
由 α_k∈[0.195, 0.405]⊂(0,1),更新映射为收缩映射,
|e[k]| ≤ 0.805^k·|e[0]|,即**目标跟踪的几何收敛**。

**证明**:代入更新式即得;区间钳位保证迭代点单调趋向 r*,
不振荡、不越界。∎

**边界**:若 r* < minRate,序列停在 minRate(不动点偏移);目标
每次重算后重新起算;本引理不构成闭环全局稳定性结论。实测
f=0.405(u=0)与 CBAP_MIG 日志一致。

## 10 算法伪代码

### 算法 1:CBAP-SBA 批次准入与公平分配

```
输入: 批次 B 的流集合 F_new(含路径 P_i、上限 maxRate_i),时刻 ready
输出: 逐流许可速率 grants
 1  在 ready 时刻聚合批次;release ← ready + T_plan (=5 µs)
                                  // planningDelayNs, rdma-hw.h:339
 2  C_avail ← GetCbapSbaAvailableCapacity()   // wire 域, rdma-hw.cc:2918
 3  对每条链路: 统计旧侧占用 R_old,l(排除 FINISHED/HOLD/COLLECTING)
                                  // AdmitBatch, cbap-sba.cc:196–213
 4  B_init,l ← min(C_avail,l, (C_avail,l−R_old,l) + ⌊ρ_init·R_old,l⌋)
                                  // 核心初始释放, cbap-sba.cc:283–303
 5  grants ← ProgressiveFill(F_new, B_init)   // 水填充, cbap-sba.cc:87
 6  校验逐链路守恒与计划态占用界; 违例则异常终止
                                  // cbap-sba.cc:331–386
 7  for i ∈ F_new:
 8      if grants_i = 0: 状态 ← ADMISSION_HOLD   // cbap-sba.cc:317–321
 9      else: 状态 ← STARTUP_SENDING; r_i ← grants_i
10  为存量流重算迁移目标(旧侧收缩、新侧上爬)
                                  // RecomputeCbapSbaMigrationTargets
11  release 时刻: 逐流施加首包相位偏置 off_i = rank_i·T_pkt/n
    (T_pkt = 8·wire_pkt/r_i, 仅平移 m_nextAvail, 不改变速率与字节)
                                  // phase spread, rdma-hw.cc:7668–7703
12  启动兜底: sbaLeaseExpiry_i ← release + T_lease (=1 ms)
                                  // rdma-hw.cc:3041–3042
```

### 算法 2:队列安全预测租约、反馈迁移与预算回收

```
每个控制周期 T_ctrl = 5 µs(每条受控链路):
 1  采样 q0 与逐 QP 账本; 构造 A_safe / A_ddl 包络
                                  // rdma-hw.cc:857–887
 2  τ ← min(最早降速期限−now, H_eff)
 3  q1, q2, q_stop ← 两阶段预测; q_safe ← q_stop + M_safe
                                  // rdma-hw.cc:896–916
 4  分区: RED 进入/退出按滞回; RED ⇒ boost←0, 全额排空, 返回
                                  // rdma-hw.cc:918–956
 5  GREEN: B ← min(BMAX·C, max(0,(Q_target−q_stop))·8/H_eff)
        再按 room_red=(Q_red−q_stop)·8/H_eff 否决/钳位
        余量租约: now+H_eff 未刷新即作废
                                  // rdma-hw.cc:1023–1064
    HOLD: 提升 ×0.99 缓释;  DRAIN: 提升 0, 按压力温和排空
                                  // rdma-hw.cc:1065–1080
 6  迁移: 对每条迁移中的流
        u ← 路径队列压力; α ← 0.30·[1+0.35(1−2u)] 或 0.30
        r ← clip(r + α(r*−r), [r,r*]区间, minRate, maxRate)
                                  // rdma-hw.cc:3419–3471
 7  事件驱动的预算回收与重准入:
        流完成 ⇒ FINISHED, 记 flow_completed_capacity_release,
        重算目标并 ReadmitHeld(HOLD 流水填充再准入)
                                  // cbap-sba.cc:457–470, 389–433;
                                  // 触发环 rdma-hw.cc:3078–3100
 8  反馈交接: 首个可操作反馈(CNP)到达 ⇒
        STARTUP_SENDING→DCQCN_OWNED, 以当前 applied 速率交接
                                  // OnActionableFeedback,
                                  // cbap-sba.cc:435–456; 调用点 4501
 9  启动兜底: now ≥ sbaLeaseExpiry 且仍无反馈 ⇒ 强制交接
                                  // EvaluateCbapSbaLease,
                                  // rdma-hw.cc:3124–3147
```

**命名规约(重要)**:第 5 步的"**预测余量租约**"(时长 H_eff,
限制提升的持续性)与第 9 步的"**启动无反馈兜底**"(固定
T_lease=1 ms,保证控制权最终移交)是两个不同机制,论文中分别
称"余量租约"与"启动兜底",不得同称 lease。

## 11 复杂度

设 |F| 为批次流数,|L| 为受控链路数,p̄ 为平均路径长度。

- **ProgressiveFill**:至多 |F|+1 轮;每轮对每条链路扫描全部流并
  作路径成员判定(std::find,O(p̄)),故每轮 O(|L|·|F|·p̄),
  最坏 **O(|F|²·|L|·p̄) 时间、O(|F|+|L|) 空间**。原稿的
  O(|F||L|) 遗漏了多轮迭代与路径扫描。常见情形:冻结层级数
  k ≪ |F|(v2 单瓶颈同构批次 k=1,即一轮完成),实际近似
  O(|F|·|L|·p̄)。v2 规模(|F|≤65, |L|=1, p̄=1)下为微秒级。
- **控制周期**:账本扫描与包络构造 O(|F|);迁移一步 O(|F|·p̄);
  每周期合计 O(|F|·p̄),周期 5 µs。
- **事件路径**:反馈交接、完成释放均 O(1) 次状态转移 +
  一次 ReadmitHeld(最坏又是一次水填充,同上界)。

## 12 理论适用边界(论文必须保留)

1. 全部性质均为**局部/条件性**结论:固定路由、冻结预算、单盲窗
   包络假设;不宣称一般拓扑全局稳定、全局最优或一切速率下
   PFC-free。
2. 10 G 下 H_eff(118 µs)与 D_abs 同量级,准入瞬态可越 Q_abs
   至多约一个盲窗(实验 5 例,均已如实报告);200/400 G 下
   盲窗缩小两个数量级,越界为零。
3. T_lease=1 ms 为**未标定的保守占位值**(源码注释原文:
   "UNCALIBRATED backstop … must be recalibrated",
   rdma-hw.cc:3126–3131);200G-S2 有 42/65 条流、400G-S2 有 9/65
   条流按该兜底交接(实测),应作为实现边界说明,不得作为主结论。
4. ADMISSION_HOLD 与重准入在 v2 正式矩阵 23 个 CBAP 单元中
   0 次触发(容量始终为正),属"实现具备、数据未覆盖"的机制;
   phase spread 已启用但无独立消融,同理只能列为实现机制。
5. 小消息(msg < BDP)场景 CBAP 完成时间不占优;TIMELY/DCTCP
   在部分 400 G 场景以约 450 µs 队列与千余次 PFC 换取 1–2.5% 的
   更短完成时间——诚实边界,不得删减。
