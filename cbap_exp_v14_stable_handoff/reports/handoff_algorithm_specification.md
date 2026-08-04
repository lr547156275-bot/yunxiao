# CBAP-v1.4 stable-handoff specification

Algorithm identity: `cbap_full_v14_stable_handoff`, CC_MODE 26. The frozen
v1.3 identity remains `cbap_full_v13_ratefloor_fix`, CC_MODE 25.

The v1.4 batch follows PREPARE → ADMISSION_HOLD → TRACKING, with the unchanged
v1.3 RECOVERY branch. A batch may enter the atomic HANDOFF_PENDING event only
after every active newcomer is in TRACKING, complete post-release feedback is
fresh, startup credit and zero-grant pause are inactive, every controlled link
is CLEAR/STABLE and below the existing Q_low/gradient/arrival bounds, no recent
CNP/PFC/emergency or applied-capacity violation remains, two consecutive stable
epochs have elapsed, and tracking has lasted at least
`max(2*path_RTT, 2*CONTROL_EPOCH)`. The batch must still have acknowledged-byte
remaining work.

Handoff is batch-level, one-way, and executed once. Current CBAP applied rates
are frozen. The existing Mellanox/DCQCN `mlx` current and target rates are both
initialized to that rate; alpha is initialized to the no-congestion value
because eligibility excludes fresh CNP evidence. Original DCQCN CNP, alpha,
decrease, AI/HAI, and recovery timer functions are reused. No DCQCN timer is
fired by the handoff event itself. The next transmission time is the maximum of
the already scheduled time, the handoff time, and the last actual DATA send plus
the packet gap at the handoff rate. This prevents line-rate restart and catch-up
bursts.

After BASE_CC, CBAP credit, rate updates, and grants are permanently disabled for
those flows. Switch monitoring may continue and is accounted separately from
active control summaries. Later congestion is handled only by original DCQCN.

CC_MODE 25 runs the same eligibility predicate as a read-only shadow. It records
the first candidate but never changes phase, pacing, credit, or rate.
