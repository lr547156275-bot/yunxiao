cd /work
echo "=== build status ==="
grep -hE "BUILD_EXIT|error:" /work/matrix_logs/build_gen.log | head -8
echo
echo "############ SCOPED DIFF: rdma-hw.cc vs the pg=3 frozen baseline ############"
echo "(baseline = commit 3050a84, the pg=3 correction)"
git diff 3050a84 -- simulation/src/point-to-point/model/rdma-hw.cc | grep -E "^[-+]" | grep -vE "^[-+]{3}" > /tmp/rh.diff
echo "  total changed lines: $(wc -l < /tmp/rh.diff)"
echo
echo "--- lines that ADD a write to a rate / pacing / target field (must be none new) ---"
grep -nE "^\+" /tmp/rh.diff | grep -E "m_rate *=|ChangeRate\(|m_nextAvail *=|mlx\.m_targetRate *=|hp\.m_curRate *=|appliedRateBps *=|migrationTargetBps *=" || echo "  (none)"
echo
echo "--- lines that REMOVE such a write (must be none) ---"
grep -nE "^-" /tmp/rh.diff | grep -E "m_rate *=|ChangeRate\(|m_nextAvail *=|mlx\.m_targetRate *=|hp\.m_curRate *=" || echo "  (none)"
echo
echo "--- the audit-only additions in rdma-hw.cc ---"
grep -nE "^\+" /tmp/rh.diff | grep -iE "actuationhook|GetCbapQpForAudit" || echo "  (none)"
