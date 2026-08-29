import io

# --- header: protected QP set + the new ledger fields ----------------------
ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()

if h.count('qcProtectedQps') == 0:
    a = ('\t\tuint32_t qcPeakActiveSenders;   '
         '// high-water mark for the drain floor')
    assert h.count(a) == 1, ('anchor a', h.count(a))
    h = h.replace(a,
                  '\t\t// Protected QP set for this controller generation: every QP\n'
                  '\t\t// still present in the rate target/effective vector, i.e. one\n'
                  '\t\t// that would actually receive this command.  Membership is NOT\n'
                  '\t\t// "did it happen to send this epoch" -- a paced flow between\n'
                  '\t\t// packets is still protected.  Removed only on completion,\n'
                  '\t\t// reclaim or handoff; cleared when the generation ends.\n'
                  '\t\tstd::set<uint32_t> qcProtectedQps;\n'
                  '\t\tuint64_t qcFloorBps;            '
                  '// sum of protected minimum rates\n'
                  '\t\tuint64_t qcDrainMaxBps;         // C - floorBps\n'
                  '\t\t// Actuation ledger, per item 4.\n'
                  '\t\tuint64_t qcExpectedEffectTimeNs;\n'
                  '\t\tuint64_t qcActualEffectTimeNs;\n'
                  '\t\tuint64_t qcRBeforeCommandBps;\n'
                  '\t\tuint64_t qcRCommandedBps;\n'
                  '\t\tuint64_t qcREffectiveBps;\n'
                  '\t\tuint64_t qcRPendingBps;\n'
                  '\t\tuint64_t qcPendingExcessBytes;\n'
                  '\t\tuint64_t qcInFlightArrivalBytes;\n'
                  '\t\tuint64_t qcInvariantViolations;\n'
                  + a + '   // DIAGNOSTIC ONLY, not the floor')

    b = '\t\t\t  qcPeakActiveSenders(0), qcQStopBytes(0),'
    assert h.count(b) == 1, ('anchor b', h.count(b))
    h = h.replace(b,
                  '\t\t\t  qcFloorBps(0), qcDrainMaxBps(0),\n'
                  '\t\t\t  qcExpectedEffectTimeNs(0), qcActualEffectTimeNs(0),\n'
                  '\t\t\t  qcRBeforeCommandBps(0), qcRCommandedBps(0),\n'
                  '\t\t\t  qcREffectiveBps(0), qcRPendingBps(0),\n'
                  '\t\t\t  qcPendingExcessBytes(0), qcInFlightArrivalBytes(0),\n'
                  '\t\t\t  qcInvariantViolations(0),\n'
                  + b)
    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

print("header: qcProtectedQps=%d ledger fields=%d"
      % (h.count('qcProtectedQps'), h.count('qcPendingExcessBytes')))
