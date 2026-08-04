# BOP-QB wire-overhead audit

## 结论

短消息诊断中 BOP-QB 的每个正向 DATA 包比 DCQCN 固定多 42 B。
准确来源是 `IntHeader::NORMAL`：

```
5 hops * sizeof(IntHop=8 B) + nhop(2 B) = 42 B
```

`scratch/third.cc` 对 DCQCN（CC_MODE=1）选择
`IntHeader::NONE`，对 BOP-QB（CC_MODE=15）选择
`IntHeader::NORMAL`。诊断原始事件也逐包验证了固定差值：

- 普通包：DCQCN 1048 B，BOP-QB 1090 B；
- 尾包：DCQCN 584 B，BOP-QB 626 B；
- 两类包均固定相差 42 B。

因此满足“所有 DATA 包固定相差 42 B”的前置条件，可以实现等线上字节
DCQCN 诊断基线。

## 发送端逐层封装

`RdmaHw::GetNxtPacket` 的真实顺序如下。

| 层 | 类型 | DCQCN | BOP-QB | 代码来源 |
|---|---|---:|---:|---|
| 应用 | RDMA DATA payload | 最多 1000 B | 最多 1000 B | `Create<Packet>(payload_size)` |
| RDMA/序列 | `SeqTsHeader` 的 seq + PG | 6 B | 6 B | `SeqTsHeader::GetHeaderSize` |
| 遥测 | `IntHeader` | 0 B | 42 B | `IntHeader::GetStaticSize` |
| 传输 | UDP | 8 B | 8 B | `UdpHeader` |
| 网络 | IPv4 | 20 B | 20 B | 无 options 的 `Ipv4Header` |
| 链路 | 仓库的 `PppHeader` | 14 B | 14 B | `PppHeader::GetStaticSize` |
| 其他自定义头 | 无 | 0 B | 0 B | DATA 发送路径没有其他 AddHeader |

这里名为 `PppHeader` 的仓库实现实际序列化 14 B：2 B protocol 加
12 B 占位，用作类 Ethernet 链路头。没有额外独立的 RDMA BTH；
本仓库的 RDMA 序列语义由 6 B `SeqTsHeader` 承载。

所以满 payload DATA 包为：

```
DCQCN: 1000 + 6 + 8 + 20 + 14 = 1048 B
BOP-QB: 1000 + 6 + 42 + 8 + 20 + 14 = 1090 B
```

交换机不重新封装 DATA。它只在 ECN 时暂时移除并重新添加 14 B
`PppHeader` 和 20 B IPv4 头以设置 ECN bits，并就地写入已有的
42 B INT 区域。瓶颈 `PhyTxBegin` 直接读取 `Packet::GetSize()`，
因此上述大小就是参与序列化、排队、ECN 和 PFC 记账的大小。

## 接收端处理

`QbbNetDevice::Receive` 使用 `CustomHeader::PeekHeader` 解析而不改变
Packet。`RdmaHw::ReceiveUdp` 同样不逐个调用 `RemoveHeader`；它通过
`packet_size - CustomHeader::GetSerializedSize()` 逻辑移除
14 B 链路头、20 B IPv4、8 B UDP、6 B seq/PG 和当前 INT 大小，
得到 RDMA payload，随后交给 `ReceiverCheckSeq`。

诊断模式 `dcqcn_wire_equalized` 在 DATA payload 尾部、添加
Seq/UDP/IP/链路头之前追加一个 42 B `WirePaddingHeader`。接收端在
上述 payload 记账之前执行 `RemoveAtEnd(42)`。因此：

- padding 处于 IPv4 DATA 包内并参与所有链路序列化和队列记账；
- 应用 payload、包数、seq、ACK milestone 和 QP 完成字节不变；
- ACK、NACK、CNP 和 PFC 的构造路径没有 padding；
- DCQCN alpha、CNP、timer、恢复和 pacing 仍调用 CC_MODE=1 的同一套
  Mellanox/DCQCN函数。

`wire_size_summary.csv` 在共享瓶颈的真实 `PhyTxBegin` 聚合
`Packet::GetSize()`，并分别记录应用 payload、协议 overhead 和
diagnostic padding，以便运行后再次逐 flow-round 验证。
