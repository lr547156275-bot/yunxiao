# BOP-QB multi-link static capability audit

## Unique verdict

`SINGLE_BOTTLENECK_HARDCODED`

The frozen implementation does not implement the requested multi-link
objective

`max_l 8 * (q_l + sum_{f uses l} B_f) / (rho*C_l-background_l)`.

It implements one scalar `linkTime`, based on one configured bottleneck
capacity, one queue sample, and the sum of all bytes in the round group.
BOP-QB similarly derives one queue target and one group credit from one ECN
threshold and one queue observation.

## Findings

1. **All controlled links on a flow path:** not enumerated. Fixed ECMP paths
   exist for packet forwarding, but the planner receives no flow-to-link
   membership.
2. **Per-link work:** absent. `totalBytes` is global to the group.
3. **Different link capacities:** absent. A single
   `m_bopBottleneckBps` is shared by all members; one telemetry sample may
   overwrite that scalar.
4. **A flow crossing multiple candidate bottlenecks:** not represented.
5. **Constraining-link output:** absent because there is no link-indexed
   maximum.
6. **Hardcoded bottleneck:** present through `BOP_BOTTLENECK_BPS` and the
   single-capacity threshold lookup.
7. **QB credit port scope:** the queue target/room/credit calculation protects
   one abstract bottleneck queue, not every output port on every fixed path.
8. **Different shared links:** no independent capacity constraint exists.
   Charging all group bytes to one configured link can be over-conservative
   when flows use disjoint links, while using the wrong capacity/queue can be
   unsafe for a slower or more congested link.

The detailed code references are in `multilink_source_map.csv`; every scalar
bottleneck dependency is listed in `hardcoded_bottlenecks.csv`.

## Scope consequence

Existing BOP-QB results remain evidence only for the explicitly configured
single shared bottleneck topology. The implementation cannot support a paper
claim of native multi-link `T_star`, serial overlapping bottlenecks, or
per-link QB credit safety. No algorithm code was changed by this audit.
