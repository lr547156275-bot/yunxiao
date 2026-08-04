# RS-HPCC implementation

## Source changes

- `rdma-queue-pair.h/.cc` extends each round with group/participant input,
  DCQCN snapshots, and one RS decision record. Per-QP RS estimator and
  aggregate counters are persistent across rounds.
- `rdma-hw.h/.cc` renames mode 13 to `CC_MODE_RS_HPCC`, removes the empirical
  carry/recovery state, selects a same-hop INT bottleneck snapshot, maintains
  the estimator, predicts queue, performs bounded bisection, and applies one
  start-rate update in `ReleaseRound`.
- `scratch/third.cc` parses the eight-field round plan and RS configuration,
  admits original DCQCN mode 1 with persistent rounds, validates group
  membership and thresholds, installs attributes, and writes the new output.
- The switch INT path remains one shared `PushHop` path for modes 3, 11, 12,
  and 13. ECN, PFC, ACK, and pacing code is unchanged.

## Baseline isolation

Original mode 3 still invokes the existing `HandleAckHp` for its feedback.
Mode 1 still invokes `cnp_received_mlx` and leaves alpha/decrease/recovery
timers running through OFF intervals. RS calls `HandleAckHp` only for
actionable current-round feedback. Gate and RS both count and gate late/stale
updates; Reset retains its diagnostic per-release HPCC reset.

No queue is modified by RS, no route changes, and no future feedback is read.
The only RS rate action is `SelectRsRoundStartRate` followed by
`SetRoundStartRate` during release.

## Input and threshold validation

`prepare_rs_run.py` deterministically generates:

```text
flow_id round_id round_group_id participant_count round_bytes
compute_gap_ns jitter_ns jitter_group
```

Each group has all 16 planned senders and identical `participant_count=16`.
Seed jitter changes the plan hash; a scenario/seed plan is byte-identical
across algorithms.

The 100-Gbit/s cases use `KMIN_MAP=400`, so the actual deterministic ECN
threshold is 400,000 bytes. For switch 18, the topology provides three
100-Gbit/s, 1-us ports and two active spine ingress ports. With 32 MiB,
4-KiB per-port reserve, three-BDP per-port headroom, and dynamic-PFC shift 3,
the audited conservative per-ingress boundary is:

```text
usable = 32*2^20 - 3*(37500 + 4096) = 33,429,644 bytes
Qpfc   = floor(usable / (2^3 + 2))  = 3,342,964 bytes
```

The generator recomputes this from topology/config/fixed paths and fails if
the checked-in metadata or config disagrees.

## Safeguards

Rates are finite positive integers bounded by `[0.05*rmax,rmax]`. The model
validates participant count, same-hop INT capacity/queue/time, timestamp age,
threshold ordering, feedback delay, monotonicity, and final prediction.
Failures use a visible conservative minimum-rate fallback; they never silently
reuse the removed carry logic.

Existing trace limits remain 64 MiB per detailed file, 128 MiB total,
10 MiB for `run.log`, and a 5-GiB free-space preflight. Successful detailed
CSV files are removed only by successful `gzip`; summaries remain raw.
