# Pre-release residual-work audit

## 唯一类型：`POST_RELEASE_RESIDUAL_WORK`

四次 seed=1 诊断均通过完整性、事件队列守恒、ECN owner 守恒和
32 MiB 文件上限检查。该结论不是 `PURE_RESIDUAL_QUEUE`：两个场景在
collective 最早 release 时都仍有大量 primer 工作尚未到达瓶颈。

| scenario | algorithm | actual q0 B | primer in-flight B | release后primer到达 B | queue peak B | primer ECN | collective ECN |
|---|---:|---:|---:|---:|---:|---:|---:|
| residual_64k | bop_qb | 71,940 | 142,024 | 142,024 | 331,360 | 0 | 0 |
| residual_64k | oracle_q0 | 71,940 | 142,024 | 142,024 | 243,394 | 0 | 0 |
| residual_160k | bop_qb | 179,850 | 209,280 | 354,700 | 633,740 | 9 | 16 |
| residual_160k | oracle_q0 | 179,850 | 209,280 | 354,700 | 433,180 | 1 | 0 |

`residual_64k` 中 primer 在 release 后仍有 132 个包、142,024 B 到达；
`residual_160k` 中仍有 326 个包、354,700 B 到达，其中 134 个包、
145,420 B 甚至是在 release 后才由 primer sender 发出。两场景的
in-flight 和 post-release arrival 均非零，数量与 release 后 queue
增长处于同一量级，足以否定“q0 是纯静态残余队列”的假设。

Oracle 后 `residual_160k` 剩余的 1 个 ECN 确实属于 primer，collective
ECN 为 0；这是 post-release primer work 的后果。它不作为独立的
`PRIMER_ECN_ACCOUNTING` 唯一类型，因为跨两个场景的主要可操作原因是
release 后仍持续到达的 residual work，而不仅是 ECN 统计归属。

数据口径：

- queued：release 时驻留在选定瓶颈队列中的 primer 线上字节；
- in-flight：发送端已经发出、但尚未进入选定瓶颈队列的 primer
  线上字节，包括上游排队和链路传输；
- post-release arrival：release 时刻及之后进入选定瓶颈队列的
  primer 线上字节；
- ECN：选定瓶颈输出端口真实 ECN counter 增量，按触发该次增量的
  packet owner 分类。

因此可以继续实现双 probe、非负 queue 趋势外推的 BOP-QB-PRT。
