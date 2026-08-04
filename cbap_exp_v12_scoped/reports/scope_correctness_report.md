# Scope correctness report

Scope status: **PASS**.

| Scenario | Expected | Actual | Pass |
|---|---:|---:|---:|
| single_pending | BYPASS | BYPASS | True |
| batch_incast | ENABLE | ENABLE | True |
| two_pending_overload | ENABLE | ENABLE | True |
| two_pending_low_demand | BYPASS | BYPASS | True |
| no_shared_link | BYPASS | BYPASS | True |
| synchronous_parking_lot | ENABLE | ENABLE | True |

## single_pending overhead decomposition

- DCQCN raw RCT: 351.849000000 us
- Scoped raw RCT: 356.849000000 us
- Scope decision delay: 5.000000000 us
- Raw overhead: 5.000000000 us
- Network-only RCT: 351.849000000 us
- Unexplained overhead: 0.000000000 us

Formal performance uses raw RCT including the 5 us scope delay. Network-only RCT is used only to verify that BYPASS adds no network behavior. The fixed control cost is neither removed nor hidden.
