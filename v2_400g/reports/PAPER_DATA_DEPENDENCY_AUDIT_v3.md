# 论文数据关系与口径审计(v3)

依据:`v2_400g/reports/final_results_v2.csv`(HEAD f0557692)、
`matrix_report_v2.md`、正式矩阵原始输出(fm*)与源码。
审计脚本:`paper_audit_v3.py`(只读)。

## 1 主矩阵完整性

- 主论文口径(排除 DCQCN-LowQ):CBAP-SBA / HPCC / DCQCN-SN /
  DCTCP-SN / TIMELY,3 速率 × 6 场景 × 5 算法 = **90 行,逐行核验
  存在且 n_complete==fanin,无缺失**。
- 场景定义与 CSV 一致:S0 64×256 KiB、S1 64×1 MiB、S2 64×4 MiB、
  S3 64×16 MiB(bg 0.8C);S4 64×4 MiB(bg 0.95C);S5 32×8 MiB
  (bg 0.8C)。缓冲默认 64 MB。
- DCQCN-LowQ(dcql)与 dcqs/cbap0/缓冲扫描为附录数据,不入主表。

## 2 指标定义(与提取脚本逐字一致)

- FCT_i = last_ack_i − first_data_tx_i(逐流);
  平均 FCT = incast 流算术平均;P99 FCT = nearest-rank
  (下标 round((n−1)·0.99))。
- BCT = max_i(last_ack_i) − network_release;
  CCT = max_i(last_ack_i) − application_ready。
- 基线的 application_ready 字段为 0(未产生该事件),提取脚本
  回退到 network_release —— 实测 fm400g_s2_dcqn 中
  release−ready=20 ms 即 ready 未置位的偏移,证实回退逻辑生效。
- 吞吐 = fanin × message_size × 8 / CCT,为 payload goodput。

## 3 指标间依赖(不得重复计数的证据)

1. **CCT−BCT 恒为 5 µs(CBAP),基线为 0**。实测
   fm400g_s2_cbap 全部 64 流 release−ready = 5000 ns 整
   (planningDelayNs 默认,rdma-hw.h:339)。这是**定义差异**
   (CBAP 把规划时延计入 CCT),CCT 与 BCT 不是两组独立证据;
   论文选其一为主指标,另一个只作口径说明。
2. **吞吐 = g(CCT) 的确定函数**(§2 公式),吞吐排序与 CCT 排序
   必然互逆,二者只能算一项优势。建议主图吞吐面板替换为
   **背景流保全率**(bg_tail_gbps / (0.8C×952/1000)),后者是独立
   证据(数据源见 §5)。
3. **qdelay_us = qpeak_mb×2^20×8/C**,二者同一队列证据的两种
   单位,胜场统计只计一次。
4. **ideal time = fanin×size×8×(1000/952)/C**(payload→wire 精确
   封装修正;包几何:载荷 952 B+头 48 B,
   `CbapLinkBytesPerPacket` rdma-hw.cc:359–374,配置
   `PACKET_PAYLOAD_SIZE 952`)。适用范围:批次线速排空下界,
   不含 RTT/启动项;仅用于 p99/ideal 归一,不作为可达值宣称。

## 4 PFC 主张的精确分母

- 120 单元中 **CBAP 配置单元为 23 个**(cbap 18 + cbap0 3 +
  缓冲扫描 cbap 2),**23/23 全部 PFC=0**;确定性孪生另计。
- 基线单元 97 个,其中 **42 个 PFC>0**(最大 3694 次,
  fm400g_s3_timely)。论文表述应为"CBAP 覆盖的 23 个配置全部
  零 PFC",不得写"120 个单元均为零 PFC"。

## 5 背景流保全:独立证据与制表来源

- 列:`bg_tail_gbps`(尾窗速率,payload)与 `bg_total_gb`;
  原始:各单元 `selected_flow_timeseries.csv` flow_id=0 的
  snd_una 时间序列(可画恢复曲线)。
- 推荐图形:各速率 S2/S3 的 bg 速率-时间曲线(批次前/中/后),
  或按算法的保全率柱状图。关键数据点:CBAP 各场景=满上限
  (304.6 G @0.8×400G;362.7 G @0.95×400G);dcqs 400G-S3 崩至
  12 G;dcqn 仅回 ~186 G。
- 该证据与 CCT/队列无函数依赖,可独立计一项结论。

## 6 v1 / v2 边界(不得混写)

- v1(10 G,冻结):Q_abs=838.86 µs(1 MiB,消息绑定参数化)、
  缓冲 8 MB、包 1048 B、H_GUARD=175 µs 假设值;其 30 单元矩阵、
  前沿扫描、敏感性附录为 10 G 结论的证据基础。
- v2 主矩阵:延迟参数化(规则 A)、缓冲 64 MB、包 1000 B、
  H_GUARD 实测;10 G 行仅服务速率尺度曲线,且存在 5 个准入瞬态
  越界单元(≤ 一个盲窗),必须如实标注。
- 400 G 缓冲敏感性(8/32/64 MB)为 v2 附录,单独成图,不与主
  矩阵混排。

## 7 机制启用状态(参数表必须收录)

| 机制 | v2 状态 | 证据 |
|---|---|---|
| phase spread | **启用**(CBAP_PHASE_SPREAD_ENABLE 1) | fm*_cbap 配置;无独立消融 ⇒ 只能列为实现机制 |
| wire-domain planning | 启用(SBA_WIRE_DOMAIN_PLANNING 1) | 配置 + rdma-hw.cc:2918–2936 |
| M_safe | 64×1000 B | CBAP_QC_SAFETY_MARGIN_BYTES 64000 |
| 1 ms 启动兜底 | 启用(默认 1 ms,未标定占位值) | rdma-hw.h:357;源码注释;§8 实测 |
| ADMISSION_HOLD/重准入 | 实现具备,v2 正式 23 单元 0 次触发 | sba_events 审计 |
| 余量租约(H_eff) | 启用 | rdma-hw.cc:846–849, 1044–1049 |

## 8 1 ms 兜底的实测边界(可写,限定为实现边界)

sba_events 审计(STARTUP_SENDING→DCQCN_OWNED 的
first_feedback−release):

- fm200g_s2_cbap:65 次交接,min 775.7 µs,**42/65 恰在 1000.0 µs
  兜底触发**(CBAP 将队列压至 ECN 阈下,首批包常不产生 CNP);
- fm400g_s2_cbap:min 418.6 µs,p50 549.7 µs,**9/65 在 1 ms 兜底**。

结论表述模板:"在 200G-S2 中 65 条流有 42 条经 1 ms 启动兜底而非
反馈交接完成控制权移交"——作为实现边界与参数敏感点说明,
不作为性能主张;并注明该常量为未标定保守占位值(源码注释)。

## 9 参数—公式—图表—结论四级映射

| 参数(值) | 进入公式 | 支撑图表/CSV | 支撑结论 |
|---|---|---|---|
| H_eff 118/15/12 µs(实测) | q1/q2、B_l、租约 | 02_heff_measurement.csv | 盲窗随速率缩小两个数量级 ⇒ 高速端优势 |
| D_abs=max(80µs,7H_eff) | Q_abs、性质3 | 07_formal_matrix_design.md、gates 列 | 队列有界主张(200/400G 成立;10G 5 例瞬态) |
| BMAX=0.02、Q_target=8µs | B_l 上界 | 04_screening_results.csv(内点最优) | 参数选择有完整曲线支撑 |
| ρ_init=0.90 | B_init | sba_events(grant) | 工作保持初始释放 |
| α=0.30/0.30/0.35 | 迁移引理 | CBAP_MIG 日志(f=0.405) | 目标跟踪几何收敛 |
| M_safe=64 kB | q_safe、Q_red | 配置+gates | 打包化误差覆盖 |
| T_lease=1 ms | 算法2 第9步 | §8 实测分布 | 控制权必然移交(实现边界) |
| MIN_RATE=0.01C | 迁移钳位下限 | 配置 | 地板可行性(10G 包络) |
| bg=0.8C/0.95C | 场景定义 | final_results_v2.csv bg 列 | 背景保全独立证据 |

## 10 问题分级

**必须修改(论文侧)**
1. 式(3) 的 k1|e|+k2e² 与实现不符,按第 5 节迁移公式替换;
   摘要/正文/结论中"非线性迁移"改为"压力自适应几何收敛
   (区间钳位)"。
2. "120 单元零 PFC"的分母表述 → "CBAP 覆盖的 23 个配置
   23/23 零 PFC;基线 97 个中 42 个非零"。
3. CCT 与 BCT、CCT 与吞吐、qpeak 与 qdelay 不得作为独立优势
   重复计数(§3)。
4. lease 一词拆分为"余量租约(H_eff)"与"启动兜底(1 ms)"。
5. v1/v2 结果不得混排;10 G 的 5 个瞬态越界单元必须保留。

**建议修改**
6. 主图吞吐面板替换为背景流保全率(§5);吞吐移至表格。
7. S0(msg<BDP)的 1–3% 劣势写入正文边界小节,不藏附录。
8. 1 ms 兜底的实测占比(§8)作为实现边界小节;标注未标定占位。
9. phase spread 仅列实现机制,声明无独立消融。

**无需修改**
10. 90 行主矩阵完整性、指标提取链路、ideal 公式、确定性单种子
    论证(孪生逐字节一致)均经核验,无矛盾。

## 11 自检结论

公式—代码—参数—数据四者交叉核验未发现矛盾:预测公式与
rdma-hw.cc:896–916 逐项一致;迁移系数与 rdma-hw.h:369–370 及
CBAP_MIG 日志 f=0.405 一致;5 µs 规划延迟与 flow_timing 实测
release−ready=5000 ns 一致;1 ms 兜底与 sba_events 实测 1000.0 µs
截顶一致;90 行主矩阵与 CSV 逐行一致。
