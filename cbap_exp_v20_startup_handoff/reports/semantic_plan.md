# Semantic validation plan

The manifest contains exactly eight seed-1 runs:

| ID | Purpose | Expected |
|---|---|---|
| S1 | no shared bottleneck | C0 bypass |
| S2 | one pending flow | C0 bypass |
| S3 | shared link without blind-window excess | C0 bypass |
| S4 | one risky hotspot | C1 and batch admission |
| S5 | multiple risky links | C2 and path-min admission |
| S6 | `Q0 < Qtarget` | controlled queue construction allowed |
| S7 | `Q0 > Qtarget` | startup aggregate below effective capacity |
| S8 | fresh feedback | one-shot smooth handoff and zero later CBAP writes |

The validator also requires completed flows, valid numeric fields, no predicted startup capacity violation, no pacing violation, no catch-up burst, and zero post-handoff CBAP write count.

These are correctness tests, not performance evidence. They must pass before the Pareto diagnostic is interpreted.
