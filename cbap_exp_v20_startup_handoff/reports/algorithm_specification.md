# CBAP-SAH / CBAP-v2.0 specification

## Identity and state

The two implementations are `cbap_v20_startup_handoff_dcqcn` (mode 28) and `cbap_v20_startup_handoff_hpcc` (mode 29). The state path is:

`PREPARE -> CLASSIFY -> BYPASS -> BASE_CC_ONLY`, or

`PREPARE -> CLASSIFY -> STARTUP_ADMISSION -> SMOOTH_HANDOFF -> BASE_CC_ONLY`.

`BASE_CC_ONLY` is terminal with respect to CBAP rate control.

## Causal classification

For each used fixed-path link, the planner uses only the latest telemetry delivered no later than `application_ready`. The blind window is the maximum of the participating QPs' base RTT and the observed feedback-pipeline delay. It computes:

- `W_f,l = min(remaining_bytes_f, r_ind_f,l * blind_window_l / 8)`;
- `W_l = sum_f W_f,l`;
- `S_l = C_effective_l * blind_window_l / 8 + max(Q_target_l - Q0_l - packet_margin_l, 0)`;
- `E_l = max(W_l - S_l, 0)`.

No shared pending link or no excess beyond the packet margin yields C0. One risky shared link yields C1. Multiple risky links, or missing/stale telemetry on a shared path, yields C2. No scenario name, workload name, message-size threshold, or fixed fan-in threshold is consulted.

## Queue target and startup budget

`Q_target_l = queue_target_fraction * ECN_threshold_l`, where the accepted values are exactly `0`, `0.125`, `0.25`, `0.5`, and `0.75`.

For controlled links:

`R_startup_l = max(0, C_effective_l + 8e9 * (Q_target_l - Q0_l - packet_margin_l) / blind_window_ns)`.

The signed queue term permits controlled queue construction below the target and forces drain below effective capacity when the starting queue exceeds the target. A whole-batch progressive-fill projection computes per-flow grants; each applied rate is the minimum grant over its fixed path and NIC maximum.

## Lease and handoff

The startup lease expires on the earliest of fresh-feedback completion, two RTTs, PFC, `Q_high`, or stale path state. C1 waits for complete post-release fresh feedback for active newcomers. C2 permits handoff after any valid post-release link feedback.

Handoff inherits the current CBAP-applied rate into the base controller, preserves the existing next-send time, disables exact CBAP pacing/credit, and transfers permanent ownership to DCQCN or HPCC-INT. It performs no line-rate reset, extra increase, or catch-up send.
