# Preregistered validation

The semantic matrix has exactly 8 deterministic seed-1 runs. The reduced performance matrix has exactly 7 scenarios × 6 algorithms = 42 runs. Thresholds and the permitted final decision vocabulary are those in the task specification. No parameter search or outcome-dependent mutation is implemented. If correctness or principal performance gates fail, the prescribed fallback is CBAP-v1.3, not another mechanism version.

## S3 fixture correction

The original `incumbent_completion` fixture used an 8 MiB incumbent with a
32 × 1 MiB newcomer batch. Its incumbent completed before newcomer release,
and the newcomer batch completed after only one stable epoch, so it could not
exercise the preregistered post-delegation reserve-release semantics. That run
is retained as an invalid-fixture diagnostic.

The corrected `incumbent_completion_post_handoff` fixture reuses the validated
`fan64_msg4m_load80` topology and schedule, changes only the synthetic
incumbent work from 512 MiB to 256 MiB, and retains the fixed 80 Gbit/s offered
load. The size is chosen from the event-order bounds: the incumbent cannot
finish before the guarded-handoff window at that source rate, while 64 × 4 MiB
of newcomer work provides a post-handoff observation interval. This correction
does not change CC_MODE 27, any controller parameter, the two-stable-epoch
requirement, or any validation scenario.
