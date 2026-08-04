# Main-v1 algorithm audit

This audit records source mappings; it does not claim experimental results.
The frozen hashes are in `config/frozen_source_hashes.sha256`.

| Name | CC_MODE | Sender action | Feedback | DATA header |
|---|---:|---|---|---:|
| PFC-only | 0 | QP maximum-rate pacing; no ACK-side CC branch | ignored by sender | 48 B |
| DCTCP | 8 | `HandleAckDctcp` | ECN echoed in ACK | 48 B |
| DCQCN | 1 | Mellanox/DCQCN CNP path | ECN/CNP | 48 B |
| TIMELY | 7 | `HandleAckTimely` | RTT timestamp | 56 B |
| HPCC-INT | 3 | `HandleAckHp` | per-hop INT | 90 B |
| CRFM-Gate | 12 | `HandleAckCrfm`; only actionable feedback updates rate | round-mapped INT | 90 B |
| BOP | 13 | one `PlanRoundGroup` plan per group-round | INT retained for later observations | 90 B |
| BOP-QB | 15 | shared BOP plan plus bounded group startup credit | pre-release INT observation | 90 B |
| Wire-equalized DCQCN | 17 | exact DCQCN sender-control path | ECN/CNP | 90 B |

The mapping comes from the enum and dispatch branches in `rdma-hw.h/.cc`.
Mode 0 has no ACK-side ECN/RTT/INT rate handler; switch ECN and PFC remain
enabled by the common scenario config. Mode 17 is diagnostic-only: it adds a
42-byte removable DATA padding header but reuses the mode-1 DCQCN control path.
ACK, CNP and PFC construction do not add padding.

## Frozen BOP-QB boundary

The main framework does not modify the following files:

- `rdma-hw.cc/.h`
- `rdma-queue-pair.cc/.h`

The frozen implementation retains `CC_MODE_BOP_QB=15`,
`BOP_QB_QUEUE_FRACTION=0.50`, shared `T_star`, byte-proportional base rates,
group credit, byte-proportional credit allocation, phase stagger, same-QP
rounds, cumulative sequence space, ACK completion, and global barrier.

QC, QB-Max, PRT, Oracle-q0 and BOP-WC are absent from `run_manifest.csv`.
Their legacy symbols may remain in the historical source tree, but no main-v1
script can select them because algorithm names and CC modes come exclusively
from the audited registry.
