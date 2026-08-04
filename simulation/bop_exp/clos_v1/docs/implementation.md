# Multi-link implementation

## Isolation and compatibility

`BOP_MULTILINK_ENABLE` defaults to false. The original single-bottleneck
BOP-QB planning block and original global-round scheduling remain the exact
path for all existing configurations. Multi-link inputs, telemetry, group
dependencies, and planning are entered only when the flag is true.

The runtime regression gate compares the current executable against the
existing main-v1 seed-1 results for `msg_64k_n16_g50`,
`msg_256k_n16_g50`, and `n32_64k_g50`. It enforces the requested 1 ns/1 B
tolerances and exact ECN, credit, base-rate, and completion-order equality.

## Planning

Each flow has an explicit fixed list of controlled egress-link IDs. For every
active group, the implementation computes per-link workload, prior legal queue
observation, available capacity, and `T_link`; `T_star` is the maximum of all
link and flow line-rate bounds. The base rate is the frozen
`min(Rmax, 8B/T_star)` expression.

The multi-link QB credit uses one rational `alpha` across all paths. Per-flow
floors use integer arithmetic. Remaining bytes are considered in deterministic
sender-rank/flow-ID order, and every one-byte increment is checked against
every link on that flow's path. Runtime assertions replay capacity, formula,
and credit constraints.

INT samples become eligible only if their ACK arrived before the group release.
There is no direct Queue-object read and no future telemetry. A missing prior
sample means `q_l=0` and is marked as fallback.

Host NIC outputs participate in workload/capacity/credit constraints but are
not mapped to switch INT hops. Because every successor release follows full
ACK completion of its predecessor, their release-time residual queue prior is
legally zero. Switch-output links retain explicit ordered INT mapping.

## Collective schedule

`group_schedule.txt` is an explicit single global-barrier chain. A successor is
planned only after every QP in its predecessor has ACK-completed. QPs are
created once per `(src,dst)` pair; later steps and iterations append releases
to the same QP and continuous sequence space.

- All-to-all deterministically splits each rank's total bytes among `N-1`
  destinations.
- The ring uses `N-1` reduce-scatter and `N-1` all-gather step barriers.
- The hierarchical collective uses seven local reduce-scatter steps, an
  inter-leaf ring all-reduce on each local-rank shard, and seven local
  all-gather steps.

The second formal collective iteration starts 50 us after the first
iteration's final global barrier.
