# CBAP-v0 implementation report

CBAP was added selectively on top of the pre-existing dirty round/BOP
worktree. The exact pre-CBAP status and patch are retained under
`cbap_exp/preflight/`; no reset, clean, or old-result deletion was used.

- `rdma-queue-pair.h/.cc` owns the sender-QP phase, grants, live rate,
  base-eligibility/credit meter, feedback freshness, and audit counters.
- `rdma-hw.h/.cc` owns modes 20--23 and the logical coordinator: explicit
  flow/link maps, batch admission, equal-weight progressive filling, delayed
  summaries, tracking, and rate decisions.
- `switch-node.h/.cc` and `switch-mmu.h/.cc` expose read-only completed-epoch
  byte, queue, ECN, and pause observations. Existing forwarding, ECN, PFC,
  ACK, and baseline control actions remain in their prior branches.
- `scratch/third.cc` parses CBAP-only configuration, binds snapshots, writes
  bounded CSVs, and traces controlled-link DATA dequeue events for seed 1.
- `cbap_exp/scripts/` generates the fixed cases, validates resumable runs,
  materializes the required summaries, augments bounded traces, recomputes
  audits/statistics, and creates dependency-free PNG/PDF/CSV figures.

Modes are: 20 Independent-Min-Grant diagnostic, 21 Init-Only, 22 Rate-Only,
and 23 Full. Preferred mode 16 was unavailable; frozen BOP-QB remains mode 15.
The control inputs are release-known batch membership/fixed paths or summaries
that have already completed and arrived after the modeled delay. Future queue,
future traffic, and ground-truth root labels are never controller inputs.

The coordinator is a simulation control-plane abstraction, not a claim of a
deployed protocol. Summary/grant counts and estimated bytes are explicit.
CBAP adds no DATA header. `code_changes.patch` is the current tracked diff of
the shared source files; because those files were dirty before this task, it
may contain pre-existing hunks. `preflight/preexisting_changes.patch` provides
the boundary needed to distinguish them.

All three Python static tests, script compilation/syntax checks, and the final
`python2 ./waf build` passed. Formal output validation passed 147/147 and the
separate legacy-mode smoke set passed 4/4.
