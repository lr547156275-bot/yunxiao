set -u
cd /work/simulation/experiment/scheme1_sba
# Step 1: preserve the old results, mark them pg0_invalid. Nothing is deleted.
mkdir -p pg0_invalid
for d in final_report analysis_s1 analysis_s2 analysis_s3 analysis_s4 analysis_s5 analysis_s6 paper_data; do
  [ -d "$d" ] && [ ! -d "pg0_invalid/$d" ] && cp -r "$d" pg0_invalid/ && echo "  copied $d -> pg0_invalid/"
done
cat > pg0_invalid/INVALID_pg0_DO_NOT_USE.md <<'EOF'
# INVALID: pg0 background-flow configuration — DO NOT USE FOR PAPER CONCLUSIONS

These results were produced with the background data flow on priority group 0.
`SwitchMmu::ShouldSendCN()` (switch-mmu.cc:106) returns false unconditionally
when `qIndex == 0`, and `switch-node.cc:181` maps `udp.pg` directly to `qIndex`.
The background flow was therefore **exempt from ECN marking by construction** and
could never be signalled to reduce its rate.

Evidence (S3-shaped run, background pg=0 vs pg=3, nothing else changed):

| metric | background pg=0 | background pg=3 |
|---|---|---|
| background cnp_count | 0 | 114 |
| background minimum_rate | 10 000 000 000 | 100 000 000 |
| incast mean FCT | 281.564 ms | 54.278 ms |
| background goodput | 7.641 Gbps | 7.420 Gbps |

Consequences for anything computed from these directories:

* The "100 % background retention" of DCQCN / DCTCP / TIMELY is an artifact: their
  background flow could not be marked, so it never reduced its rate.
* Every background-protection comparison (retention, minimum throughput,
  slowdown, recovery) is affected.
* Incast FCT for all algorithms is inflated, because the background flow held
  capacity it should have yielded.
* The capacity-feasibility and eta-sweep conclusions were measured under this
  configuration and must be re-derived.

The algorithm code is unchanged and remains frozen. Only the experiment
configuration was wrong. `ShouldSendCN()` was NOT modified — queue 0 is
plausibly reserved for control traffic, so the fix is to move background DATA
flows to pg=3, leaving ACK/CNP handling untouched.

Retained for the old-vs-new difference table only.
EOF
echo "=== pg0_invalid/ contents ==="
ls pg0_invalid/ | sed 's/^/  /'
du -sh pg0_invalid 2>/dev/null | sed 's/^/  size: /'
