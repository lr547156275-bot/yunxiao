import io

# Extend the audit snapshot with the fields the trace now reports, and fix the
# protected-set count: the floor came out 6.3 G (63 flows) instead of 6.5 G
# (64 incast + 1 background), so two flows were being excluded.
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()

old = ('\tstruct CbapQcSnapshot {\n'
       '\t\tuint64_t boostEffectiveBps, boostCommandedBps, pendingGeneration;\n'
       '\t\tuint64_t drainTargetBps, guardExceeded, queueBytes;\n'
       '\t\tuint32_t zone;\n'
       '\t\tuint32_t activeSenders;   // census the controller used this epoch\n'
       '\t};')
assert h.count(old) == 1, ('snapshot', h.count(old))
h = h.replace(old,
              '\tstruct CbapQcSnapshot {\n'
              '\t\tuint64_t boostEffectiveBps, boostCommandedBps, pendingGeneration;\n'
              '\t\tuint64_t drainTargetBps, guardExceeded, queueBytes;\n'
              '\t\tuint32_t zone;\n'
              '\t\tuint32_t activeSenders;   // census the controller used\n'
              '\t\t// Reported so the trace never recomputes what the controller\n'
              '\t\t// already decided -- an earlier trace recomputed q_stop with\n'
              '\t\t// the old endpoint formula and reported phantom violations.\n'
              '\t\tuint64_t qStopBytes, qSafeBytes;\n'
              '\t\tuint64_t floorBps, drainMaxBps;\n'
              '\t\tuint64_t pendingExcessBytes;\n'
              '\t\tuint64_t invariantViolations;\n'
              '\t\tuint32_t protectedCount;\n'
              '\t};')
io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

pc = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
c = io.open(pc, encoding='utf-8', errors='surrogateescape').read()
old2 = ('\tout->zone = it->second.qcZone;\n'
        '\tout->activeSenders = it->second.qcActiveSenders;\n'
        '\treturn true;')
assert c.count(old2) == 1, ('accessor', c.count(old2))
c = c.replace(old2,
              '\tout->zone = it->second.qcZone;\n'
              '\tout->activeSenders = it->second.qcActiveSenders;\n'
              '\tout->qStopBytes = it->second.qcQStopBytes;\n'
              '\tout->qSafeBytes = it->second.qcQSafeBytes;\n'
              '\tout->floorBps = it->second.qcFloorBps;\n'
              '\tout->drainMaxBps = it->second.qcDrainMaxBps;\n'
              '\tout->pendingExcessBytes = it->second.qcPendingExcessBytes;\n'
              '\tout->invariantViolations = it->second.qcInvariantViolations;\n'
              '\tout->protectedCount =\n'
              '\t\t(uint32_t)it->second.qcProtectedQps.size();\n'
              '\treturn true;')
io.open(pc, 'w', encoding='utf-8', errors='surrogateescape').write(c)
print("snapshot extended: qStopBytes/floorBps/protectedCount exposed")
