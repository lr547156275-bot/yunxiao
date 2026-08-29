import io

ph = '/work/simulation/src/point-to-point/model/rdma-hw.h'
h = io.open(ph, encoding='utf-8', errors='surrogateescape').read()

if h.count("qcSafetyMarginBytes") == 0:
    a = '\t\tuint64_t qcOnWirePacketBytes; // for the packetization margin'
    assert h.count(a) == 1, ('anchor a', h.count(a))
    h = h.replace(a, a + '\n'
                  '\t\tuint64_t qcSafetyMarginBytes; '
                  '// M_safe, from the measured residual')

    b = '\t\tuint32_t qcActiveSenders;       // census used for the margin'
    assert h.count(b) == 1, ('anchor b', h.count(b))
    h = h.replace(b, b + '\n'
                  '\t\tuint32_t qcPeakActiveSenders;   '
                  '// high-water mark for the drain floor\n'
                  '\t\tuint64_t qcQStopBytes;          // last Q_stop\n'
                  '\t\tuint64_t qcQSafeBytes;          // last Q_safe\n'
                  '\t\tuint64_t qcQSafeOverAbs;        '
                  '// times Q_safe exceeded Q_abs\n'
                  '\t\tuint32_t qcBandInvalid;         '
                  '// boundary ordering check failed\n'
                  '\t\tbool qcInRed;                   '
                  '// RED latch, exits below Q_high')

    c = '\t\t\t  qcPendingEtaNs(0), qcDrainCommandedBps(0),'
    assert h.count(c) == 1, ('anchor c', h.count(c))
    h = h.replace(c,
                  '\t\t\t  qcPeakActiveSenders(0), qcQStopBytes(0),\n'
                  '\t\t\t  qcQSafeBytes(0), qcQSafeOverAbs(0),\n'
                  '\t\t\t  qcBandInvalid(0), qcInRed(false),\n'
                  + c)

    d = '\t\t\t  qcOnWirePacketBytes(0),'
    assert h.count(d) == 1, ('anchor d', h.count(d))
    h = h.replace(d, '\t\t\t  qcOnWirePacketBytes(0), qcSafetyMarginBytes(0),')

    io.open(ph, 'w', encoding='utf-8', errors='surrogateescape').write(h)

print("header fields: qcSafetyMarginBytes=%d qcPeakActiveSenders=%d qcInRed=%d"
      % (h.count("qcSafetyMarginBytes"), h.count("qcPeakActiveSenders"),
         h.count("qcInRed")))
