# n32 DCQCN cross-version configuration audit

The archived final-validation report records a three-seed mean group RCT of
213.184 us. Current main-v1 records approximately 262.024 us, a difference of
48.840 us (22.91% relative to the archived value).

| Field | Current main-v1 | Archived final validation |
|---|---|---|
| scenario | `n32_64k_g50` | reported as `n32_64k` |
| senders | 32 | 32 (report only) |
| message bytes | 65,536 | 65,536 (report only) |
| rounds | 4 | not recoverable from retained inputs |
| compute gap | 50 us | not recoverable from retained inputs |
| jitter/seed | deterministic seed 1/2/3 inputs retained | raw inputs absent |
| fixed paths | SHA-256 retained in each current run | raw file absent |
| link rate | 100 Gbit/s | report says 100 Gbit/s |
| propagation delay | current topology retained | raw topology absent |
| payload/MTU | payload 1000 B; current config retained | raw config absent |
| ECN/PFC thresholds | current config retained | raw config absent |
| ACK/CNP/DCQCN parameters | current config retained | raw config absent |
| simulation duration | 0.05 s | raw config absent |
| source hash | current run metadata retained | source patch only |
| CC_MODE | 1 | reported DCQCN; raw config absent |

The archive contains the report, comparison CSV, source patch, and Git status,
but no complete legacy `run_meta.json`, `config.txt`, `topology.txt`,
`flow.txt`, `rounds.txt`, or fixed-path file. Consequently
`legacy_config_unavailable=true`. Reconstructing missing fields would be
guessing, so the legacy replay is not schedulable. A deterministic replay of
the complete current seed-1 input is provided separately.

Static status: `DCQCN_DRIFT_UNRESOLVED`. This is not evidence of a DCQCN
control change; it means the retained evidence is insufficient to attribute
the cross-version difference.
