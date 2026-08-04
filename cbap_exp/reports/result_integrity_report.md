# CBAP-v0 result integrity report

- Expected formal runs: 147
- Valid formal runs: 147
- Invalid/missing formal runs: 0
- Capacity violations: 0
- Credit violations: 0
- Statistical unit: scenario + subcase + algorithm + seed.
- Three seeds are summarized by mean, median and range; no packet-level pseudo-replication or p-values are used.
- Seed-1 bounded packet/control traces: 49/49.
- Full-CBAP rate-transition/freshness audit errors: 0.

Input hashes, exit status, completion flags, CC_MODE, NaN/Inf and truncation are checked for every run. Detailed failures are in `processed/invalid_runs.csv`. Aggregate admission capacity is replayed offline per batch/link.

The seed-1 packet evidence contains real controlled-link DATA dequeue events and merged control events. Host TX_SCHEDULE/TX_SEND timestamps were not retained, so the exact sender packet-gap inequality remains NOT_MEASURED rather than being inferred from switch departures.
