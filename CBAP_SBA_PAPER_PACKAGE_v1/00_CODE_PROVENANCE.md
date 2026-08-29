# Code provenance

HEAD: 0c090e46cf41ff0e3d691dec45c4f5d0507d29b3

Recent commits:
```
0c090e4 README: CBAP-SBA overview, results, reproduction, provenance; upstream HPCC attribution kept
8c958b8 Experiment results: 30-cell matrix, parameter frontier, sensitivity annex
d51077a Tooling and provenance: generators, runners, extractors, patches, run logs
dbee109 CBAP-SBA controller: predictive leased headroom (D4v2), correctness fixes, unified timing
a745d58 AUDIT-ONLY CHECKPOINT: dynamic-PFC and 4-stage actuation audit
95160dc EXPERIMENTAL, NOT VALID: queueing-delay credit and its failed acceptance
```

| artefact | sha256 |
|---|---|
| binary third | 5b5920f859fa86a269b5de4d9a7479226e27b03ecfc63c8356b100edb116c7e1 |
| libns3 point-to-point | ABSENT |
| rdma-hw.cc | 5230e9132851aec2943c9963396211d5ff5a4a15744bd59f76bb2677f3584021 |
| rdma-hw.h | 87d052b7e65dff473025b5eec1ccf6a6bee06bf53fc5cf3cf5682af10b1d4dbe |
| cbap-sba.cc | 9a035ad7c1bdf404d8e6dfd00c3c58a6e3d2569f781fc499fd9a960e7b376f1e |
| third.cc | d866cf86cd6df6b239cb83c2403f95f06cad5857502eec64b495789da94bae58 |

Analysis/tooling scripts: tools/ in the repo (committed d51077a); per-file SHAs in SHA256SUMS of this package.

Source patches applied this campaign: tools/patches/fixAD..fixAK (each atomic, anchored, with byte-regression evidence in the round reports).
