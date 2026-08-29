set -u
cd /work
CK=/work/matrix_logs/audit_checkpoint
mkdir -p $CK
# Snapshot the exact audit-only sources, so the controller diff is isolable.
for f in scratch/third.cc src/point-to-point/model/rdma-hw.cc \
         src/point-to-point/model/rdma-hw.h \
         src/point-to-point/model/cbap-sba.cc src/point-to-point/model/cbap-sba.h; do
  cp "simulation/$f" "$CK/$(echo $f | tr '/' '_')"
done
cp /work/simulation/build/scratch/third $CK/third.bin 2>/dev/null || true
cd $CK
sha256sum *_third.cc *rdma-hw.cc *rdma-hw.h *cbap-sba.cc *cbap-sba.h 2>/dev/null | sed 's/^/  /'
echo "  binary: $(sha256sum third.bin 2>/dev/null | cut -c1-16)"
echo
echo "=== git checkpoint commit (LOCAL ONLY, no push) ==="
cd /work
git add -A simulation/ 2>/dev/null
git -c user.name=audit -c user.email=audit@local commit -q -m "AUDIT-ONLY CHECKPOINT: dynamic-PFC and 4-stage actuation audit

Read-only instrumentation and audit deliverables. NO controller.

Adds, all trace/hook only:
  - SampleCbapPfcAudit + CBAP_PFC_AUDIT_FILE       (dynamic PFC predicate inputs)
  - per-ingress-port detail + CBAP_PFC_PORTS_FILE  (contributors by measured rx)
  - 4-stage actuation trace + CBAP_ACTUATION_FILE  (generation + QP key + seq)
  - RdmaHw::s_cbapActuationHook (NULL by default), GetCbapQpForAudit (read-only)

Verified scope: 332 added / 0 removed lines vs pre-audit snapshot; zero added or
removed writes to m_rate / ChangeRate / m_nextAvail / mlx.m_targetRate /
hp.m_curRate; switch-mmu.{cc,h} and switch-node.cc untouched, so ShouldSendCN(),
ECN marking and the dynamic PFC threshold are unmodified.

Key measured results:
  - PFC counter (ingress_bytes) and CBAP queue_bytes (egress BEgressQueue) are
    NOT the same quantity; mean ratio 0.2823. Two independent guards required;
    the 400 KB ECN proxy is rejected.
  - H_eff(arrival) global max 170.328 us over 443 samples -> H_guard = 175 us.
  - Earlier ~20 us H_eff estimate WITHDRAWN (was two separately-measured legs).
  - pending excess peaks at 1765 B = 1.41 us, ~30x smaller than my earlier
    43.4 us projection, which is WITHDRAWN; commands here are mostly decreases.
  - Q(t) is NOT stale (5.0 us delivery lag); the issue is pending actions.

NOT pushed. Controller is deliberately absent so it can be diffed separately." 2>&1 | tail -2
echo "  HEAD now: $(git rev-parse --short HEAD)"
echo "  branch  : $(git rev-parse --abbrev-ref HEAD)"
echo "  pushed? : $(git log --oneline origin/master..HEAD 2>/dev/null | wc -l) unpushed commits (expected: not pushed)"
echo "AUDIT_CHECKPOINT=$(git rev-parse HEAD)" | tee /work/matrix_logs/audit_checkpoint.ref
