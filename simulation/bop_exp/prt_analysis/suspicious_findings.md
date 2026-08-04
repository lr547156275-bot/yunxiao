# Suspicious findings

1. 原 BOP-QB 和 Oracle 的 `prt_runs` 只记录瓶颈总 ECN，没有
   primer/collective owner 字段。两个 group 的 `group_ecn_marks` 在时间重叠时会
   同时累计同一个端口事件，不能相减恢复 owner。因此不能把原版总 ECN 冒充
   collective ECN。PRT 自身的 owner 计数完整。

2. 两个 residual 场景每个 seed 都发送 2 个 probe，但只有第一个在 release
   前返回，返回率恒为 50%。要求用于 `POST_RELEASE_RESIDUAL_WORK` 的双样本
   slope 分支从未执行。

3. `residual_64k` 的单 probe 保守 margin 将 `q_hat` 提高到约 162.17 KB，
   而实际 q0 为 71.94 KB。绝对误差约 90.23 KB，比原 BOP-QB 的 71.94 KB
   误差高 25.43%。

4. `residual_160k` 的 `q_hat` 三个 seed 都被截到 200 KB target，启动信用
   因而为 0。`safety_bound_valid=0` 表示保守估计加 packet margin 已超过
   target；运行只因信用为零而保持“未增加额外 burst work”。实际 q0 加
   packet margin 仍低于 target。

5. `gap_50us` seed 1 的首轮 probe 产生 88,875 B 的保守 `q_hat`，尽管
   release 时实际 q0 为 0；该 seed 的平均 RCT 增加 0.153 us。另两个 seed
   首轮 probe 未及时返回，结果与原 BOP-QB 相同。

6. PRT 在 `residual_64k` 的 queue 比 Oracle 还低 30.52%，但这是信用从
   Oracle 的 111,676 B 进一步压到约 21,445 B 的结果，不代表 q0 估计比
   Oracle 更准确。
