# 第5章 实验评估（main-v2 修正版）

## 当前判定

**DCQCN_REVIEW_REQUIRED**。273 个正式运行均通过复用审计，但 n32 DCQCN 跨版本漂移尚未解释。本章数字可作为审计中的仿真结果，不能作为已经最终冻结的论文结论。

## 实验口径

结果来自 ns-3 固定 ECMP、100 Gbit/s 单共享瓶颈仿真。正式基线仅为 DCTCP、DCQCN、TIMELY 和 HPCC-INT。BOP-QB 分别与四者比较；best formal CC baseline 只从四者按 mean group RCT 选择。

历史 `pfc_only` 统一改称 `open_loop_no_endhost_cc`，仅作为 uncontrolled injection reference。PFC configured but runtime pause behavior not verified。它不参与主胜负统计。

## 修正后的主结果

相对 best formal CC baseline，BOP-QB 在 1/15 场景同时改善 RCT 和峰值队列；在 4/15 场景以不超过 3% RCT 代价换取至少 50% 峰值队列下降。完整逐场景数字见 `bop_exp/main_v2/analysis/best_cc_baseline_comparison.csv`。

消息大小、参与者、compute gap 和异构性扫描均保留所有场景。Gate→BOP→BOP-QB 消融与 Wire-Equalized 诊断复用既有数据；Wire-Equalized 不替代标准 DCQCN。

## PFC 与重现性限制

main-v2 的九次事件级 PFC 审计尚未执行，因此 PFC 指标标记 NA，不声明 BOP-QB 改善 PFC。n32 DCQCN 当前均值 262.024 us，旧报告 213.184 us；旧原始输入缺失，结论为 DCQCN_DRIFT_UNRESOLVED。

## 适用边界

三 seed 只反映当前有限输入；结果不代表真实 GPU/NCCL、生产部署、动态路由、多瓶颈或强背景流。
