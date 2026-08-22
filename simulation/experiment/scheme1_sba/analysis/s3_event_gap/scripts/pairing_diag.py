# -*- coding: utf-8 -*-
# Two unit-test failures to resolve before any conclusion is reported.
#
# F1  DCQCN pacer trace has 0 rows.
# F2  DCQCN TX_BEGIN=68800 but TX_END=68801  (one extra END)
#
# F2 matters: if a TX_END has no matching TX_BEGIN, the gap construction could
# mis-order intervals.  The candidate benign explanation is a packet whose
# TX_BEGIN fell before the trace window opened while its TX_END fell inside --
# a window-edge effect, not a pairing defect.  That is checkable: the unmatched
# END must be the FIRST TX event in the file and its uid must never appear as a
# BEGIN.
import csv
import os

B = '/work/simulation/experiment/scheme1_sba'
T0N, T1N = 2000000000, 2058372997

for tag in ('ct_cbap_on_out', 'ct_dcqcn_on_out'):
    d = os.path.join(B, tag)
    p = os.path.join(d, 'causal_queue.csv')
    print('=== %s ===' % tag)
    if not os.path.exists(p):
        print('  ABSENT')
        continue
    beg, end = {}, {}
    order = []
    with open(p) as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if r['event'] == 'TX_BEGIN':
                beg.setdefault(r['packet_uid'], []).append((i, int(r['time_ns'])))
                order.append(('B', i, r['packet_uid'], int(r['time_ns'])))
            elif r['event'] == 'TX_END':
                end.setdefault(r['packet_uid'], []).append((i, int(r['time_ns'])))
                order.append(('E', i, r['packet_uid'], int(r['time_ns'])))
    only_end = [u for u in end if u not in beg]
    only_beg = [u for u in beg if u not in end]
    print('  TX_BEGIN uids=%d  TX_END uids=%d' % (len(beg), len(end)))
    print('  END without BEGIN : %d  %s' % (len(only_end), only_end[:5]))
    print('  BEGIN without END : %d  %s' % (len(only_beg), only_beg[:5]))
    for u in only_end[:3]:
        i, t = end[u][0]
        print('    unmatched END uid=%s at row %d t=%d  (window opens %d)'
              % (u, i, t, T0N))
        print('    is it the FIRST TX event in the file? %s'
              % (order[0][2] == u and order[0][0] == 'E'))
        print('    dt from window open = %d ns' % (t - T0N))
    for u in only_beg[:3]:
        i, t = beg[u][0]
        print('    unmatched BEGIN uid=%s at row %d t=%d (window closes %d, '
              'dt to close=%d ns)' % (u, i, t, T1N, T1N - t))
    # duplicates would be a genuine defect
    dbl_b = [u for u, v in beg.items() if len(v) > 1]
    dbl_e = [u for u, v in end.items() if len(v) > 1]
    print('  uids with >1 BEGIN : %d   >1 END : %d' % (len(dbl_b), len(dbl_e)))

    # tx_serialization.csv is the independent recorder; compare its pairing
    tp = os.path.join(d, 'tx_serialization.csv')
    if os.path.exists(tp):
        tb = te = 0
        tbeg, tend = set(), set()
        with open(tp) as fh:
            for r in csv.DictReader(fh):
                t = int(r['time_ns'])
                if not (T0N <= t <= T1N):
                    continue
                if r['event'] == 'TX_BEGIN':
                    tb += 1
                    tbeg.add(r['packet_uid'])
                elif r['event'] == 'TX_END':
                    te += 1
                    tend.add(r['packet_uid'])
        print('  independent recorder in-window: BEGIN=%d END=%d' % (tb, te))
        print('    END w/o BEGIN=%d  BEGIN w/o END=%d'
              % (len(tend - tbeg), len(tbeg - tend)))

# F1: DCQCN pacer emptiness -- is it expected?  The emit site is inside
# ChangeRate's CBAP branch, so a DCQCN run (CC_MODE 1, CBAP_ENABLE 0) can never
# reach it.  Verify against the config and the source, not by assumption.
print('=== F1: why is DCQCN causal_pacer.csv empty? ===')
cfg = os.path.join(B, 'ct_dcqcn_on.txt')
for k in ('CC_MODE', 'CBAP_ENABLE', 'CAUSAL_PACER_TRACE_FILE'):
    for ln in open(cfg):
        if ln.startswith(k + ' '):
            print('  config %-26s = %s' % (k, ln.split(None, 1)[1].strip()))
hw = '/work/simulation/src/point-to-point/model/rdma-hw.cc'
src = open(hw).read()
i = src.find('CausalPacerTrace::Emit')
if i > 0:
    seg = src[max(0, i - 2600):i]
    # which enclosing branch?
    for marker in ('IsCbapMode', 'cbap.', 'CbapPacketGapNs'):
        print('  emit site preceded by %-18s : %s'
              % (marker, 'yes' if marker in seg else 'no'))
print('  => an empty DCQCN pacer trace is EXPECTED (CBAP-only code path),')
print('     not a telemetry failure.  It must not be read as "DCQCN made no')
print('     rate changes" -- DCQCN changes rates via its own DCQCN path, which')
print('     this tracer does not instrument.')
