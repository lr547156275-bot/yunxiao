# Fixed screening suspicious findings

1. 只有 seed=1；任何稳定性、标准差和置信区间结论都不可用。
2. 只有 `gap_20us` 的 later-round mean RCT penalty 为正（+57.5%）；
   gap50/100/500 分别为 -25.3%/-51.3%/-59.9%，跨轮低起始速率没有
   转化为一致的后续 RCT 代价。
3. `gap_20us` HPCC actionable-byte ratio 为 0.169，未满足问题确认的
   `<=0.10` 严格阈值。
4. RA 相对 Gate 在 gap_20/50/100/500 的 P95 改善均为 0 或近似 0，
   完整 carry 没有显示增量价值。
5. `size_256k` 中 RA 相对 HPCC：P95 RCT +51.62%、goodput -13.71%。
6. long-burst control 中 RA 相对 HPCC：P95 RCT +9.64%、goodput -5.03%。
7. `gap_20us` 中 RA queue max 相对 HPCC +36.02%，超过 GO 的 10% 限制。
8. 32 次运行均无 PFC 事件，因此只能确认“不恶化为正事件”，不能比较
   已发生 PFC 时的暂停行为。
9. `hpcc_round_reset` 只能诊断跨轮状态，不能作为部署算法。
10. 修复后的输入、INT、release、QP 和序列检查均通过，没有无效运行被
   以 0 补入统计。
