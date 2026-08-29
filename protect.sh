set -u
cd /workspaces/yunxiao
BEFORE=$(git rev-parse HEAD)
echo "  commit BEFORE any change: $BEFORE"
git add -u simulation/experiment/scheme1_sba/metrics.py \
           simulation/experiment/scheme1_sba/s1_flow.txt \
           simulation/experiment/scheme1_sba/s2_flow.txt \
           simulation/experiment/scheme1_sba/s3_flow.txt \
           simulation/experiment/scheme1_sba/s4_flow.txt \
           simulation/experiment/scheme1_sba/s5_flow.txt \
           simulation/experiment/scheme1_sba/s6_flow.txt
git -c user.name="bshu02" -c user.email="bshu02@ubiq2.com" commit -q -F - <<'MSG'
Fix background flows to pg=3 and add fixed-window background statistics

Configuration correctness fix, no algorithm change.

The background data flow was on priority group 0. switch-node.cc:181 maps
udp.pg directly to the egress queue index, and switch-mmu.cc:106 returns false
unconditionally from ShouldSendCN() when qIndex == 0. The background flow was
therefore exempt from ECN marking by construction, and -- because pg also
selects which queue a packet waits in -- it was also isolated from the incast
queue, so its RTT stayed low. Both effects let it hold capacity indefinitely.

Consequence: DCQCN and DCTCP never received congestion signals for it, and
TIMELY measured an RTT distorted by the queue separation (a 1.27 MB queue is
1021 us of delay against a 15.2 us base RTT). HPCC and CBAP-SBA were unaffected,
since neither depends on ECN and HPCC reads port-level INT state.

All 7 background data flows across the six scenarios move from pg=0 to pg=3.
ShouldSendCN() is NOT modified -- queue 0 is plausibly reserved for control
traffic -- and ACK/CNP handling is untouched. Verified: no incast flow ever used
pg=0, and only the pg field changed in each flow file.

metrics.py additionally gains fixed-window background statistics
(bg_fw_* on FIXED_WINDOW_S = 150 ms) because the existing bg_during_gbps and
bg_retention_pct are scoped to each run's own CCT, which is not comparable
across algorithms once collective durations differ by 5x. Also propagates
bg_recovery*_never_dipped for multi-background-flow scenarios (S6), where it
was previously blank.

Measured effect on the 30-cell matrix (algorithm and binaries unchanged,
third 0156d0ba / p2p lib 0bacef18): the three ECN/RTT baselines improve 3.4x to
19.7x, while HPCC and CBAP-SBA are unchanged to within 1%. Prior results are
preserved under pg0_invalid/ and must not be used for paper conclusions.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
AFTER=$(git rev-parse HEAD)
echo "  commit AFTER pg fix        : $AFTER"
git log --oneline -1
echo
echo "=== create the working branch ==="
git checkout -b cbap-queue-delay-credit 2>&1 | tail -1
echo "  branch: $(git rev-parse --abbrev-ref HEAD)  base: $(git rev-parse --short HEAD)"
