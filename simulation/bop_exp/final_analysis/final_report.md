# BOP-QB final validation report

## 唯一判定：`ADD_PRERELEASE_TELEMETRY`

60/60 次运行全部有效。42 B 线上字节归一化后，BOP-QB 在三个 16-sender 场景的 group RCT 仅慢 0.47%–0.80%，在 n32_64k 则快 29.81%；四场景队列峰值下降 70.60%–85.21%。但是两个 residual 场景中正式 BOP-QB 都把非零 q0 估计为 0；Oracle-q0 在 RCT 不变的情况下将队列峰值降低 28.39% 和 32.73%，并将 residual_160k 的三 seed ECN 总数从 85 降至 4。因此不能直接 FINALIZE，下一步应仅增加 pre-release telemetry。

## 数据完整性

- 运行矩阵：60/60；无缺失、重复或额外运行。
- 所有 exit status=0，全部流和 round 完成，无 NaN/Inf、死锁、日志截断或 barrier 跨轮重叠。
- 同 scenario+seed 跨算法的 topology/flow/fixed-path/round 哈希一致；三个 seed 的 round 哈希互不相同。
- 所有 residual release q0 均处于声明范围；primer 不计入 collective RCT。
- Equalized DCQCN 与 BOP-QB 的每个 flow-round 包数、payload、最小/平均/最大 DATA 线上大小完全一致。

## 等线上字节结果

RCT 单位为 µs；queue 是三 seed 的每次运行峰值均值；goodput 是 collective payload / group active RCT。

| 场景 | 算法 | mean RCT | P95 | max | queue B | goodput Gb/s | mean wire B | ECN | PFC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gap_20us | dcqcn | 90.733 | 91.006 | 91.095 | 508571 | 92.454 | 1040.970 | 28 | 0 |
| gap_20us | dcqcn_wire_equalized | 95.054 | 95.570 | 95.863 | 559987 | 88.251 | 1082.970 | 39 | 0 |
| gap_20us | bop_qb | 95.502 | 95.951 | 95.991 | 153690 | 87.837 | 1082.970 | 0 | 0 |
| gap_50us | dcqcn | 91.160 | 92.498 | 93.438 | 516525 | 92.022 | 1040.970 | 36 | 0 |
| gap_50us | dcqcn_wire_equalized | 95.354 | 96.742 | 97.674 | 555937 | 87.974 | 1082.970 | 49 | 0 |
| gap_50us | bop_qb | 95.856 | 97.320 | 97.720 | 160230 | 87.514 | 1082.970 | 0 | 0 |
| single_round | dcqcn | 90.713 | 90.987 | 91.028 | 504453 | 92.474 | 1040.970 | 9 | 0 |
| single_round | dcqcn_wire_equalized | 94.949 | 95.223 | 95.264 | 503045 | 88.349 | 1082.970 | 13 | 0 |
| single_round | bop_qb | 95.710 | 95.913 | 95.930 | 147877 | 87.646 | 1082.970 | 0 | 0 |
| n32_64k | dcqcn | 213.184 | 282.519 | 308.129 | 1041136 | 78.764 | 1040.970 | 616 | 0 |
| n32_64k | dcqcn_wire_equalized | 266.715 | 416.489 | 418.559 | 1139494 | 63.714 | 1082.970 | 619 | 0 |
| n32_64k | bop_qb | 187.210 | 187.649 | 187.834 | 168587 | 89.617 | 1082.970 | 0 | 0 |

### 42 B 解释量与队列下降

| 场景 | BOP vs Equalized RCT | 原BOP-DC gap µs | 42B解释比例 | BOP vs Equalized queue下降 |
|---|---:|---:|---:|---:|
| gap_20us | 0.471% | 4.769 | 90.607% | 72.555% |
| gap_50us | 0.526% | 4.696 | 89.313% | 71.178% |
| single_round | 0.801% | 4.997 | 84.777% | 70.604% |
| n32_64k | -29.809% | -25.973 | N/A（BOP原本已更快） | 85.205% |

### 三 seed 配对 RCT 差值

差值定义为 BOP-QB − Equalized DCQCN；负值才表示 BOP-QB 更快。

| 场景 | mean diff µs | 95% CI µs | 三seed方向 |
|---|---:|---:|---:|
| gap_20us | 0.448 | [-0.287, 1.183] | 0负/0零/3正 |
| gap_50us | 0.502 | [0.076, 0.927] | 0负/0零/3正 |
| single_round | 0.761 | [0.170, 1.351] | 0负/0零/3正 |
| n32_64k | -79.505 | [-170.020, 11.010] | 3负/0零/0正 |

在 gap20、gap50、single 三个原始 DCQCN 更快的场景中，其 RCT 优势有 84.78%–90.61% 可由少 42 B/DATA 解释；等字节后 BOP-QB 仅慢 0.47%–0.80%。n32 不适合计算该解释比例，因为 BOP-QB 原本就比 DCQCN 快 12.18%，等字节后优势扩大到 29.81%。三 seed 很少，CI 应作为不确定性而非稳定性证明。

## 非零残余队列

| 场景 | 算法 | actual q0 B | estimated q0 B | abs error B | credit B | queue max B | RCT µs | ECN | PFC | actual安全 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| residual_64k | bop_qb | 71940 | 0 | 71940 | 183616 | 323003 | 109.500 | 0 | 0 | FAIL |
| residual_64k | bop_qb_oracle_q0 | 71940 | 71940 | 0 | 111676 | 231296 | 109.500 | 0 | 0 | PASS |
| residual_160k | bop_qb | 179850 | 0 | 179850 | 183616 | 640130 | 134.562 | 85 | 0 | FAIL |
| residual_160k | bop_qb_oracle_q0 | 179850 | 179850 | 0 | 3766 | 430637 | 134.562 | 4 | 0 | PASS |

- residual_64k：Oracle credit 减少 71,940 B，queue max 下降 28.39%，RCT 变化 0%，两者均无 ECN/PFC。
- residual_160k：Oracle credit 减少 179,850 B，queue max 下降 32.73%，RCT 变化 0%，ECN 从 85 降至 4，PFC 均为 0。
- 原 BOP-QB 的 estimate-based safety 标志通过，但用 actual q0 回放均失败；Oracle 的 actual safety 均通过。

## 判定依据

- 等字节 RCT 的“不比基线慢超过3%”门槛通过：三个 16-sender 场景慢不到1%，n32 则快 29.81%。
- 队列门槛通过：BOP-QB 相对 Equalized DCQCN 均下降 ≥50%。
- `FINALIZE_BOP_QB` 未通过：residual_160k 出现 85 个 ECN，且 两个 residual 场景的 actual safety 均失败。
- `ADD_PRERELEASE_TELEMETRY` 通过：q0 严重低估；Oracle queue 下降超过20%，改善 ECN，RCT 无退化。

## 能与不能得出的结论

可以得出：短消息中原 DCQCN 的大部分 RCT 优势来自 42 B 线上字节差；BOP-QB 在等字节条件下保留显著队列优势；准确的 pre-release q0 对非零残余队列安全有实质价值。

不能得出：Oracle 可以部署、pre-release telemetry 的具体实现方式已经确定、4 个残余 ECN 必然可消除，或三 seed 已足以证明更广泛工作负载上的统计稳定性。

## 下一步最小工作

只实现 release 前可获得的 q0 telemetry，并保持 BOP-QB 的 0.5×ECN、基础配速、credit、phase、ACK 和 barrier 不变；随后复用当前 residual 场景验证其与 Oracle 的差距。
