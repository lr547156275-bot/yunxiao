set -u
cd /workspaces/yunxiao
BEFORE=$(git rev-parse HEAD)
git add -u simulation/scratch/third.cc \
           simulation/src/point-to-point/model/rdma-hw.cc \
           simulation/src/point-to-point/model/rdma-hw.h
git add -f simulation/experiment/scheme1_sba/queue_credit_unit_check.py \
           simulation/experiment/scheme1_sba/queue_credit_acceptance.py 2>/dev/null || true
git -c user.name="bshu02" -c user.email="bshu02@ubiq2.com" commit -q -F - <<'MSG'
EXPERIMENTAL, NOT VALID: queueing-delay credit and its failed acceptance

Preserved on this experimental branch so the investigation is not lost. The
mechanism is DISABLED by default (CBAP_DELAY_CREDIT_ENABLE=0) and in that state
reproduces the strict-conservation planner bit-for-bit -- verified on S3, nine
metrics identical to 9 decimal places.

None of the credit results may be used for paper conclusions. Marked invalid in
two stages, for two different reasons:

  INVALID_QUEUE_CREDIT_WIRING_BUG -- first attempt. Three wiring defects: the
  phase latch fired at the first replan while the queue was still 0, so the
  SYNC_BURST allowance was never used; credit/drain were computed inside the
  handover branch of ReplanCbapSbaMigrationTargets, which only runs during a
  migration, so drain never took effect; and the queue therefore ran to 136 240 B
  (7.17 RTT) against a 1 RTT bound.

  PERSISTENT_RATE_CREDIT_WITHOUT_LEASE_EXPIRY -- second attempt, after the wiring
  was fixed. Per-state behaviour became correct (credit only below target, drain
  only above, 0 violations each), but the granted boost had no expiry: it altered
  the admitted per-flow rate itself rather than adding a temporary increment over
  a base rate, so it persisted 2.6 ms instead of one 15 us horizon. Queue peaked
  at 118 424 B (6.23 RTT).

Two audit findings worth keeping, both of which corrected earlier claims of mine:

  * The "97.6% of epochs oversubscribed / 2.93 s" figure was a statistics-scope
    error. The credit path runs every epoch for the whole 3 s run, including when
    no batch exists. Within the batch lifetime only 4 epochs (20 us) granted
    credit. Idle-epoch bookkeeping must be suppressed.

  * AdmitBatch computes (C - old_reservation) * 0.5, in that order: one old-flow
    subtraction at cbap-sba.cc:185, one 0.5 batch weight at :228. With C=10 G and
    an 8 G background reservation this yields 1.0 G for 64 flows = 15.625 Mbps,
    matching the measured admit_rate exactly. An earlier report of mine said
    "-4.0 G then x0.5" and mislabelled the order; both were wrong.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
echo "  before: $BEFORE"
echo "  after : $(git rev-parse HEAD)"
git log --oneline -1
echo "=== worktree clean? ==="
git status --porcelain | wc -l | sed 's/^/  uncommitted: /'
