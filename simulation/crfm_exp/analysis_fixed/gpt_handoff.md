# 给 GPT 的 fixed screening 摘要

唯一正式判定：**INCONCLUSIVE**（只有 seed=1，不能写稳定结论）。

数据有效性：32/32 运行通过；exit=0；所有流/轮次完成；无 NaN、死锁或
截断；四模式均有 INT；RA 多轮 carry>0；所有下一轮 release 均晚于上一轮
ACK completion；gap plan 最大误差 0 ns。

问题证据：HPCC gap20/50 的 late ratio=0.590/0.757，后续 start rate
显著下降；但 later-round mean RCT penalty 只有 gap20 为正（+57.5%），
gap50/100/500 为负。gap50 actionable-byte=0.080 满足阈值，但
gap20=0.169 不满足。long-burst actionable ratio=0.998，single-round
四算法完全相同。Reset 将 gap20/50/100/500 的 mean RCT 分别降低
25.58%/20.55%/18.29%/12.16%，但它仅是诊断 oracle。

算法证据：

- RA vs HPCC P95：gap20 -63.70%，gap50 -2.69%，gap100 -0.64%；
- gap20 queue max +36.02%；
- size256 P95 +51.62%、goodput -13.71%；
- long-burst P95 +9.64%、goodput -5.03%；
- RA 与 Gate 在四个 gap 场景 P95 基本相同。

筛选解释：跨轮低速率状态得到支持，但 CRFM 性能代价没有在 gap 扫描中
一致出现，只得到未完全满足严格标准的单 seed 证据；
RA-HPCC 没有通过 GO 条件，且没有证明优于 Gate。若坚持统计确认，只能
冻结参数补 seed2/3；不要基于本结果调参或宣称稳定失败。

完整数字见 `crfm_ra_hpcc_report.md`、`per_seed_metrics.csv` 和
`comparison.csv`。
