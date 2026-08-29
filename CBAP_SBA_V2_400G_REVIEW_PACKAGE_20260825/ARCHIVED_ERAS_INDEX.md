# ARCHIVED_ERAS_INDEX — superseded rounds (NOT in this package; do not cite)

Archive tar: `v2_archived_eras.tar.gz` in release `evidence-v2-2026-08`
sha256 `84abf90329016006ddf25383c0d73927609dcc4053d69dde720aa05ff4d30c55`
(11,179,810 bytes). Each era was moved (never deleted) with a pre-move
`MANIFEST_pre_move.txt`; originals remain in the release asset.

| era directory | rounds contained | why superseded |
|---|---|---|
| `results_r1_pkt1048/` | preflight round 1 (pf_single/pf_burst/heff ×3 rates) | 1048B wire packets: ns-integer truncation skewed per-packet tx time (+4.8% at 400G); goodput criterion mixed the trailing ACK RTT into the rate; burst theory used a single-link model on a multi-tier fabric. Replaced by the 1000B-wire geometry and corrected criteria (preflight round 2/3). |
| `results_r2_floor1ns/` | preflight round 2 (same cells, 1000B packets) | remaining −1ns double-floor in tx-time computation (gap 799/39/19ns instead of 800/40/20) → +0.125%/+2.6%/+5.3% rate skew. Replaced after `TX_TIME_ROUND_NS` (round 3: exact integer gaps, PASS). |
| `results_bgfreeze_era/` | screening round 1 (9-cell grid), heff_400g round 3, pf_burst_400g round 3 | u32 truncation in `GetNxtPacket` froze any flow whose remaining bytes hit an exact multiple of 2^32 — every 400G background flow (>4.29GB) froze mid-run, so those cells measured incast without live background competition. Replaced after the payload64 fix by the 8-cell screening cross and heff/burst reruns (all with live-background gates). |

Every superseding fix was proven inert on v1 semantics by a twin
byte-regression (`regv3`, `regv4` markers in `raw/v2_configs_logs.tar.gz`
logs). If an audit of the formal evidence surfaces a contradiction, the
archive tar can be submitted separately; its contents must not be used
for any performance claim.
