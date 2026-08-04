# BOP-QB final validation implementation

最终算法保持为 `bop_qb`、CC_MODE=15、queue target=`0.5*ECN`。
CC_MODE=17 和 18 均标记为 diagnostic-only：

- 17 `dcqcn_wire_equalized`：复用 DCQCN 控制路径，仅给正向 DATA
  增加 42 B 可移除 padding；
- 18 `bop_qb_oracle_q0`：复用 BOP-QB 规划、信用、phase 和发送路径，
  只把规划时 q0 替换为 release 前瞬间读取的共享瓶颈真实队列。

残余队列场景包含 16 个 collective sender 和 4 个 primer sender。
Primer 使用独立 group 1000 和固定路径，以每 NIC 100 Gbit/s 真实
DATA 构造队列；它不进入 collective group、RCT、wire summary 或
release queue summary。两条 100 Gbit/s spine 输出汇入一条
100 Gbit/s 瓶颈，每条 spine 承载两个同步 primer。以第一批 DATA
到达为起点，经过一条 sender stream 的序列化时间后，两份 stream
已到达而一份 stream 已排出，残余量等于一份 stream 的线上字节。
因此每个 primer 的 payload 等于目标 q0，启动提前量使用真实分包数
及 BOP-QB 每包 90 B 头部计算。该解析公式一次性生成，未做参数搜索。
每个 residual 场景只有一个 collective round，运行有效性由真实
release queue 范围决定。

`PlanRoundGroup` 通过只读 callback 在最早实际 group release 时读取
目标 `QbbNetDevice` 的 `GetQueue()->GetNBytesTotal()`。CC_MODE=15
仍然使用原有 pre-release INT estimate；CC_MODE=18 才使用真实值。
两者都记录 estimate、actual、误差、sample age/origin、credit 及两种
safety replay。

最终输出新增：

- `wire_size_summary.csv`：每个 collective flow-round 的线上 DATA
  大小聚合；
- `release_queue_summary.csv`：每个 collective group-round 的真实和
  估计 q0、信用、安全、queue max、ECN、PFC。

运行脚本继承 `JOBS=1`、5 GiB 磁盘保护、断点续跑和已有输出限额。
