cd /work
echo "############ scope check: third.cc ############"
git diff 3050a84 -- simulation/scratch/third.cc | grep -E "^[-+]" | grep -vE "^[-+]{3}" > /tmp/t.diff
echo "  changed lines: $(wc -l < /tmp/t.diff)"
echo
echo "--- does the diff ADD/REMOVE any rate, pacing, or CC assignment? ---"
grep -E "^[-+]" /tmp/t.diff | grep -E "m_rate|m_nextAvail|ChangeRate|m_bps *=|MIN_RATE|min_rate|RATE_AI|rate_ai|targetRate *=" || echo "  (none)"
echo
echo "--- does it touch flow/topology/seed/routing config? ---"
grep -E "^[-+]" /tmp/t.diff | grep -E "FLOW_FILE|TOPOLOGY|SIM_SEED|CBAP_PATH_FILE|KMIN|KMAX|PMAX|BUFFER_SIZE|PAUSE_TIME|pfc_a_shift|ConfigEcn|ConfigHdrm" || echo "  (none)"
echo
echo "--- new config keys added (should be exactly the 3 trace keys) ---"
grep -E "^\+" /tmp/t.diff | grep -oE 'key.compare\("[A-Z_]+"\)' | sort -u
echo
echo "############ scope check: rdma-hw.h ############"
git diff 3050a84 -- simulation/src/point-to-point/model/rdma-hw.h | grep -E "^[-+]" | grep -vE "^[-+]{3}" | grep -iE "actuation|ForAudit" || echo "  (no audit lines)"
echo
echo "############ ShouldSendCN / switch ECN / PFC threshold: untouched? ############"
git diff --stat 3050a84 -- simulation/src/point-to-point/model/switch-mmu.cc simulation/src/point-to-point/model/switch-mmu.h simulation/src/point-to-point/model/switch-node.cc
echo "  (empty above = switch MMU / node not modified at all)"
