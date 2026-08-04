# CBAP-v1.2 scoped specification

`cbap_full_v11_unscoped` remains CC_MODE 23 with `CBAP_SCOPE_POLICY=ALWAYS`.
`cbap_full_v12_scoped` is CC_MODE 24 with
`CBAP_SCOPE_POLICY=SHARED_BATCH_OVERSUBSCRIPTION` and base CC DCQCN.

At `application_ready`, the scoped dispatcher reads only port summaries whose
sample and delivery times are no later than `application_ready`. For every
candidate link it replays Full-v1.1 effective capacity, incumbent floor,
queue-room, feedback-horizon, and admission-capacity calculations. Each
pending flow is then considered alone against the unchanged incumbents. Its
independent path grant is the minimum link grant on its fixed path.

For link `l`, `D_l` is the sum of these independent grants. The link triggers
exactly when it has at least two pending flows and
`D_l > A_admit_l + max(1 bps, 1e-9 C_l)`. There is no workload-name, message
size, percentage, or learned threshold in this predicate.

An enabled decision dispatches to the existing `PlanCbapBatch` implementation.
The Full-v1.1 rate changes, decrease states, freshness, queue credit, pacing,
progressive filling, and floor decay remain their existing implementations.
A bypass decision registers no CBAP QP state, grant, credit, or tracking. Its
QP was initialized as ordinary Mellanox/DCQCN, and CNPs take the exact DCQCN
handler. Read-only base-flow references let a later enabled batch account for
currently active bypassed incumbents without converting those incumbents into
CBAP-controlled QPs.

Both outcomes use a fixed 5,000 ns planning interval. `application_ready` is
recorded before the interval and network release after it, so bypass does not
receive a zero-cost advantage.

Scope telemetry is distinguished from CBAP grant/tracking traffic. A bypass
has zero grant messages and zero rate/credit records; release-before port
summaries remain available because they are required to make the scope
decision.
