# CBAP-v1.4 implementation report

## Source audit

The original DCQCN state is the `RdmaQueuePair::mlx` structure: `m_targetRate`,
`m_alpha`, the alpha/decrease CNP flags, `m_first_cnp`, recovery stage, and the
alpha/decrease/rate-increase events. `RdmaHw::cnp_received_mlx`,
`UpdateAlphaMlx`, `CheckRateDecreaseMlx`, and `RateIncEventTimerMlx` remain the
only DCQCN controller. CC_MODE 26 is included in `IsDcqcnMode` so normal QP
initialization and completion cancellation use those original fields and events.

Before handoff, ACK CNPs are observed for eligibility but are blocked from
calling `cnp_received_mlx`, exactly isolating the CBAP controller. After atomic
handoff the block is removed and ACK CNPs take the original DCQCN path.

## Implementation

- CC_MODE 26 adds stable batch handoff without modifying the CC_MODE 25 rate,
  credit, scope, admission, feedback, or exact-pacing branches.
- Existing phase numeric values 0–5 are unchanged. HANDOFF_PENDING and BASE_CC
  are appended as 6 and 7.
- The candidate predicate uses explicit flow paths and the existing controlled
  port summaries. K is fixed at two; the minimum tracking time is structural.
- The handoff event sets DCQCN current/target equal to the current CBAP applied
  rate, initializes the unmaintained congestion state without an immediate AI,
  preserves the next-packet pacing deadline, then transfers ownership.
- Applied-rate accounting excludes handed-off flows from CBAP constraints.
  Monitoring-only summaries remain separate from active control summaries.
- New batch/flow, controller-ownership, and control-message outputs support the
  offline hard-condition audit.
- CC_MODE 25 gets only a shadow candidate record; no v1.3 control action changes.

## Inputs and matrix

Case files are copied from validated v1.3/v1.2 inputs. The fan64/load95 case is
derived from the validated fan64/load80 case using the exact existing load-scan
transformation: only incumbent link `0 66` changes from 80 to 95 Gb/s. Flow,
round, path, PFC/ECN, and collective inputs remain unchanged, and hashes are
recorded.

The semantic manifest contains exactly seven runs. The deterministic validation
manifest contains six scenarios × five algorithms = 30 runs. The validation
script refuses to start until the semantic report begins with
`HANDOFF_SEMANTIC_PASS`.

## Data protection

Scripts default to one job, disable NS_LOG and core dumps, reject starts below
5 GiB free, cap retained `run.log` at 10 MiB, retain diagnostics on failure, and
support valid-run resume. Detailed selected traces are compressed only after a
successful, parseable run.

After the first manual semantic attempt, two pre-experiment defects were
corrected without changing the v1.4 controller: the `ROUND_MODE` configuration
registry now includes CC_MODE 26, and the redundant legacy all-DATA packet
trace is directed to `/dev/null`. The bounded sender trace and all handoff,
ownership, applied-rate, and control-message audits remain enabled. This avoids
the deterministic 96 MiB trace truncation seen in the 4 MiB v1.3 shadow run.
Static tests now cover both conditions.

The output contract distinguishes the preregistered pending collective from
the incumbent workload. Every pending flow and pending round must be present
and ACK-complete. Incumbent flow IDs must be present in the round schedule but
are allowed to remain active at the collective-oriented stop time. The v1.4
metric collector uses the same pending-only scope for collective FCT, group
RCT, payload goodput, and completion. This keeps completion validation and
formal metrics consistent while retaining incumbent packets, queues, ECN, PFC,
and link utilization as real network effects.

Pacing violations are scoped to CBAP exact-grant ownership. DCQCN-owned packets
after handoff are audited by the separate first-packet/catch-up and ownership
records; a later DCQCN rate decrease is not retrospectively labeled a CBAP
pacing violation. The forced-recovery semantic case verifies that handoff never
occurs inside its configured recovery guard. A post-guard handoff still requires
the unchanged real eligibility predicate; completion without becoming eligible
is recorded as `completed_before_handoff`, not fabricated into a handoff.

The applied-capacity invariant is enforced for RATE_ONLY and FULL CBAP modes.
`CBAP_INIT_ONLY` intentionally stops CBAP rate enforcement after admission and
returns to its DCQCN path, so later applied-rate excess is retained as an
ablation metric rather than misclassified as an invalid run.

## Scope

No ns-3 experiment was executed in this implementation phase. Therefore this
report makes no claim about handoff occurrence, performance, or research value.
