# B080 root cause — LEDGER_GHOST_ARRIVAL (classification B/C)

NOT "EXPECTED_NONMONOTONIC_SATURATION".  The low duty is a
correctness defect in per-QP command bookkeeping, established
read-only from scr7_b080_out/controller_v2_trace.csv + qc_trace.csv
(b080_audit.py passes 1+2), then anchored in code.

## Q1 first occurrences (b080)
- boost_requested>0: t=2.000010000 s (law asks 1.198G, clamp 0.8G)
- boost_commanded>0: t=2.000010000 s
- boost_effective>0: t=2.000190000 s (command->effective 180 us = H_eff+1 epoch, correct)
- pending_excess>0:  t=2.000255000 s

## Q2 duty attribution (11,723 batch epochs)
- LAW_ZERO (Q_pred >= Q_target): 11,615 = 99.08%
- WAITING pending ETA: 71 = 0.61%; ON: 35 = 0.30%; vetoes: ~0
- zones: GREEN throughout; RED/DRAIN never entered
- lease violations 0; SAME-generation stuck pending 0 (an earlier
  ">2*H_eff" count of 96 was a detector artifact on legal
  replacement chains and is retracted)

## Q3 trajectory
Single 175 us lease at 0.8G (2.000190-2.000360), queue 9,432 ->
28,296 B (deposit matches 0.8G*188us/8).  From 2.000255 the trace
shows pending_excess LOCKED at 26,528-26,534 B (p50 == p99) for
the remaining 58 ms; that constant alone exceeds Q_target=26,214,
so the GREEN law headroom is permanently zero and boost never
re-arms.  Full table: b080_audit2.py output.

## Mechanism (code-anchored)
1. Propagation (DeliverCbapPortSummary): per-QP share =
   (boostCmd - drainCmd)/genSize is an ABSOLUTE aggregate applied
   on top of senderEffective (which already contains the boost).
   A down-to-zero command computes share = 0: NO pending flag, and
   commandedWireBps frozen at the boosted senderEffective.
2. Confirmation (QueueControllerEpoch): commandedWireBps is never
   cleared after the deadline, so the confirmation branch
   re-asserts predictedArrival = (stale boosted) commandedWireBps
   EVERY epoch, overwriting the per-epoch refresh from the actual
   rate.  Self-sustaining: inflated Q_pred -> law 0 -> delta <
   deadband -> no new command -> stale value never rewritten.

## Q4 verdict: B/C
- B: arrival-envelope accounting carries a ghost (ledger claims
  ~11.2G while dispatched targets sum ~9.7G and physical queue
  stays ~2-3KB)
- C: state-machine ordering lets a CLOSED command keep rewriting
  predictedArrival
- affects b005-b040 as well: same constant ghost (b040: 15,901 B
  < Q_target, so it still re-armed at 55.6%% in-batch duty), i.e.
  all scr7 v2 numbers are biased and scr8 rerun supersedes them.
- open secondary observation (re-audit after fix): b080 mean
  applied sum 9.72G vs cap 10G across all batch thirds.

## Fix
fixAH_ledger.py, two edits in rdma-hw.cc only: share computed as
delta (commandedNet - effectiveNet)/genSize; commandedWireBps
cleared on confirmation.  No threshold, zone, law, checker, or
frozen parameter touched.  Unit test qb2_ledger_unittest.py
(python mirror, 7 checks) reproduces the ghost under the old
semantics and proves the bounded-lifetime property under the fix.
