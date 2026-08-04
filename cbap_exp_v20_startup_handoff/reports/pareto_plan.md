# Queue-target Pareto diagnostic plan

The manifest contains exactly 30 seed-1 v2.0/DCQCN runs: six scenarios crossed with five fixed queue-target fractions (`0`, `0.125`, `0.25`, `0.5`, `0.75`). No automatic selection or search is performed.

Scenarios:

1. `fan16_msg256k_load80`
2. `fan64_msg256k_load80`
3. `fan64_msg1m_load80`
4. `fan64_msg4m_load80`
5. `fan64_msg1m_load95`
6. `parking_lot_synchronous`

Existing DCQCN, HPCC-INT, CBAP-init-only, and frozen v1.3 results are reused only when all topology, flow, round, path, controlled-link, and group-schedule hashes match. A missing hash match is reported rather than silently substituted or rerun.

The analyzer emits all-work metrics and four SVG/PDF plots: FCT versus peak queue, FCT versus Queue AUC, throughput versus peak queue, and utilization versus peak queue. It does not choose a winning fraction.
