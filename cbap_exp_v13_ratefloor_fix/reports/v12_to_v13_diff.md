# v1.2 to v1.3 semantic difference

| Item | v1.2 | v1.3 |
|---|---|---|
| Identity | `cbap_full_v12_scoped` | `cbap_full_v13_ratefloor_fix` |
| CC_MODE | 24 | 25 |
| Rate-floor policy | `ONE_PACKET_PER_EPOCH_LEGACY` | `EXACT_GRANT_PACING` |
| Positive applied rate | legacy `max(target, 1.7024 Gb/s)` path | exact positive target after existing caps |
| Zero target | legacy floor behavior | explicit paused QP |
| Packet interval | existing DataRate pacing | nanosecond ceiling of wire bits/rate |
| Control epoch | 5 us | unchanged 5 us |
| Scope/admission/credit | frozen | identical |

The semantic floor was split in `RdmaHw::SetCbapRate`; the legacy branch is
retained verbatim. Exact packet timing is handled by `CbapPacketGapNs`,
`UpdateNextAvail`, and `ChangeRate`. Egress pause enforcement is in
`RdmaEgressQueue`/`QbbNetDevice` selection.
