# CBAP-v1 final analysis

## Decision

**CONTINUE_WITH_MAJOR_REVISION**

Implementation validity and research value are separated below. No old CBAP-v0 STOP decision is reused.

## Integrity

- Formal runs: 84/84 valid; 0 invalid; 0 missing.
- Semantic repair: SEMANTIC_PASS.
- DETERMINISTIC_REPETITION for 24/28 scenario-algorithm groups; only 4/28 vary across seeds (all varying groups are E2). Input schedules are identical across seeds; the seed affects only stochastic simulation behavior where present.

## RQ1 — actual independent versus batch admission

E2 actual aggregate admission is 383.962 Gbit/s for Independent, 172.782 for Rate-Only, and 153.585 for Full. Independent exceeds the reconstructed admission budget by 203.803 Gbit/s. The fixed implementation therefore produces a real sender-side distinction, not merely different plan fields.

## RQ2 — Full credit lifetime

All semantic credit gates exit with admission and all pacing counters are zero. In staggered E4, F0 tracking actual/current/base rates are 44.232/46.272/12.920 Gbit/s (actual/current ratio 0.956). Actual tracking is therefore no longer permanently clamped to the initial base rate.

## RQ3 — batch-admission value in E2

Rate-Only versus Independent changes peak queue by -56.32%, queue AUC by +17.91%, and new-batch CCT by -1.57%. Joint admission removes the reconstructed actual oversubscription while retaining similar old-flow aggregate goodput.

## RQ4 — continuous tracking

In E2, Rate-Only versus Init-Only changes new-batch CCT by -50.85% and peak queue by -25.20%. Tracking is valuable in this incast, but E1 Rate-Only is +12.27% slower in new-flow CCT than Init-Only, so the benefit is workload-dependent.

## RQ5 — credit ablation

Full versus Rate-Only changes E2 peak queue by -8.42%, queue AUC by -36.24%, and CCT by +0.47%. In E1 and both static E4 cases the two outputs are identical. Credit therefore has a modest E2 queue benefit here, but no independent gain in the accurate static cases; prediction-error/background-burst validation remains necessary.

## RQ6 — parking-lot fairness

Synchronous Full goodputs are 45.446/45.474/45.474 Gbit/s. Staggered later F0 is 44.307 Gbit/s versus 71.214/71.227 for incumbents, so F0/min(F1,F2)=0.622. It is not the old ~25 Gbit/s result, but staggered fairness is still incomplete. F0 current rate is 30.429 Gbit/s at 4 estimated RTT and 38.429 Gbit/s at 6 RTT. Multi-decrease flow/epoch violations across CBAP runs: 0. Retained outputs do not expose the internal protection-floor value, so its decay is explicitly NOT_MEASURED.

## Interpretation

- Code semantics tested by the 20-run gate are correct.
- The batch-admission hypothesis is supported in E2.
- Tracking helps E2 but is not uniformly beneficial.
- Credit is not generally necessary in these static accurate-prediction cases.
- Victim isolation remains unvalidated because E3 was intentionally not rerun.
- The remaining E1 cost and staggered parking-lot imbalance require major revision before a broad claim.
