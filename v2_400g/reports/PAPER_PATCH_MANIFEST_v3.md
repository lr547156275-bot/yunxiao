# PAPER_PATCH_MANIFEST_v3

生成时间:2026-08-26。分支 `cbap-queue-delay-credit`,
HEAD `f0557692e7121ffeaecb675f51999b92f26d5446`。未提交任何 commit,
未修改源码与实验结果。

## 1 实际读取的文件与范围

| 文件 | 读取范围(行) | 用途 |
|---|---|---|
| simulation/src/point-to-point/model/rdma-hw.cc | 359–374, 679, 840–1090, 2256, 2420–2440, 2700–2745, 2800–2960, 3041–3160, 3419–3471, 4494–4512, 6630–6636, 7668–7703 | 预测/分区/提升/迁移/兜底/交接/相位分散/包几何 |
| simulation/src/point-to-point/model/rdma-hw.h | 194, 228, 251, 271–274, 339, 356–375 | 全部默认参数 |
| simulation/src/point-to-point/model/cbap-sba.cc | 30, 87–166, 168–175, 183–388, 389–433, 435–470, 483–499 | 水填充/准入/重准入/交接/完成释放 |
| simulation/scratch/third.cc | 733, 3646, 3754 | 配置键映射 |
| v2_400g/configs/fm400g_s2_cbap.txt | 全文关键键 | v2 实际启用标志 |
| v2_400g/reports/final_results_v2.csv | 全表 | 90 行主矩阵/PFC 分母 |
| v2_400g/reports/matrix_report_v2.md | 全文 | 结论边界 |
| v2_400g/reports/02_heff_measurement.csv、04_screening_results.csv、07_formal_matrix_design.md | 引用 | 参数冻结链 |
| v2_400g/results/fm{200,400}g_s2_cbap/{flow_timing,sba_events}.csv、fm400g_s2_dcqn/flow_timing.csv | 审计脚本 | 5 µs 间隔/1 ms 兜底/HOLD 计数 |

## 2 生成的文件

1. v2_400g/reports/PAPER_THEORY_PATCH_v3.md
2. v2_400g/reports/PAPER_CODE_EQUATION_MAP_v3.csv
3. v2_400g/reports/PAPER_DATA_DEPENDENCY_AUDIT_v3.md
4. v2_400g/reports/PAPER_PATCH_MANIFEST_v3.md(本文件)
(辅助:仓库根 paper_audit_v3.py,只读审计脚本)

## 3 待替换论文表述:旧问题 → 正确表达

| 旧表述 | 问题 | 正确表达(源码依据) |
|---|---|---|
| 式(3) k1\|e\|+k2e² 非线性迁移 | 与实现不符 | u_k 路径压力 + α_k=0.30[1+0.35(1−2u_k)](升)/0.30(降),区间钳位;rdma-hw.cc:3419–3471 |
| "非线性迁移控制" | 误导 | "压力自适应几何收敛(带区间钳位与速率地板)" |
| 单一 "lease" | 两机制混称 | 余量租约(H_eff,rdma-hw.cc:846/1044)与启动兜底(1 ms,rdma-hw.cc:3124–3147)分列 |
| B_l 为"准入总速率" | 语义错误 | GREEN 区基准聚合预算之上的附加许可 wire 速率增量(desired=R_budget−C) |
| H 与 H_eff 混写 | 量纲混淆 | B_init 中 H_l=C_avail−R_old 为容量余量(bit/s);H_eff 为时间(s) |
| 复杂度 O(\|F\|\|L\|) | 漏多轮扫描 | 最坏 O(\|F\|²·\|L\|·p̄),常见一轮 O(\|F\|·\|L\|·p̄);空间 O(\|F\|+\|L\|) |
| "120 单元零 PFC" | 分母含基线 | CBAP 23/23 零 PFC;基线 97 中 42 个非零 |
| 双阶段预测按论文猜测式 | 需与码一致 | q1/q2/前缀最大/τ=min(最早降速期限,H_eff);rdma-hw.cc:891–916 |

## 4 可以写的结论

- 性质 1/2/3 与迁移引理(按补丁第 6–9 节的条件与范围);
- 200/400G:队列 20–50 倍分离、CBAP 23 配置零 PFC、缓冲不变性、
  msg≥BDP 时批完成 p99 最优或并列且随速率扩大、背景流满保全;
- 参数选择链(screening 内点最优 + H_eff 实测)可复现;
- 单种子正当性(确定性孪生逐字节一致)。

## 5 必须降级或附条件的结论

- 队列有界:条件性单盲窗上界;10 G 有 5 例瞬态越界(≤1 盲窗),
  必须保留并解释;
- max-min 公平:仅单次求解/冻结预算内;
- 迁移收敛:固定目标的几何收敛,非闭环全局稳定;
- 1 ms 兜底:实现边界(未标定占位值,源码注释原文引用),
  200G-S2 42/65、400G-S2 9/65 的实测占比只作边界说明;
- phase spread、ADMISSION_HOLD/重准入:实现具备,无独立消融/
  数据未覆盖,不得写为"实验验证"。
- 小消息(S0)劣势 1–3%、TIMELY/DCTCP 以高队列+PFC 换部分场景
  更短完成时间:诚实边界,保留。

## 6 仍需人工确认

1. 迁移**目标重算**的旧侧收缩比例(源码注释提及
   "R_old* = (1−eta)·R_old",rdma-hw.cc:3155 附近):η 的取值与
   配置键未在本轮核读范围内逐行确认,论文如引用需先核
   RecomputeCbapSbaMigrationTargets 全文。
2. 迁移压力带挂在链路文件 ecnThresholdBytes=400 000 B(三速率同
   值,非随速率缩放)——是设计意图还是 v1 遗留,需作者确认并在
   参数表如实标注。
3. 《计算机工程》格式的公式编号、图表号与参考文献占位
   "[待映射:主题]" 由论文整合环节处理。
4. 主图吞吐面板 → 背景流保全率的替换(审计建议 6)需作者确认
   图幅取舍。
