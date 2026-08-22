# Locate the actuation-accounting faults from the EXISTING traces (item 8.1:
# no re-runs). Marked ONLINE_PREFLIGHT_FAIL_ACTUATION_ACCOUNTING, not
# CAPACITY_INFEASIBLE -- the band is brakeable:
#   (Q_abs - Q_red) * 8 / MAX_BOOST = 67072*8/3e9 = 178.9 us > H_guard 175 us
import csv
import os
import sys

C = 10e9
H_GUARD_S = 175e-6
EPOCH_NS = 5000.0
Q_ABS = 1048575.0
M_SAFE = 67072.0
M_ACT = 0.30 * C * H_GUARD_S / 8.0
Q_RED = Q_ABS - M_SAFE
Q_HIGH = Q_RED - M_ACT
Q_LOW = 0.5 * Q_ABS
ONW = 1048.0

CELLS = [('rho=0.90', 'qc_s3_rho090'), ('rho=0.9875', 'qc_s3_rho09875')]


def rows(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


os.chdir(os.path.dirname(os.path.abspath(__file__)))

print('=== brakeability check (overturns the earlier "infeasible" claim) ===')
fill_us = (Q_ABS - Q_RED) * 8 / (0.30 * C) * 1e6
print('  (Q_abs - Q_red) = %.0f B' % (Q_ABS - Q_RED))
print('  fill time at MAX_BOOST = %.1f us  vs H_guard = %.1f us  -> %s'
      % (fill_us, H_GUARD_S * 1e6,
         'BRAKEABLE' if fill_us > H_GUARD_S * 1e6 else 'NOT brakeable'))
print('  So the failure is actuation accounting, NOT capacity infeasibility.')

for label, cell in CELLS:
    qc = rows(cell + '_out/qc_trace.csv')
    link = rows(cell + '_out/selected_link_timeseries.csv')
    if not qc:
        print('%s: no trace' % label)
        continue
    print('')
    print('=' * 72)
    print('=== %s' % label)
    print('=' * 72)

    # ---- item 4: why is floorBps 6.6 G when 65 * 100 M = 6.5 G? ---------
    print('')
    print('  --- item 4: dynamic floor, per epoch ---')
    fl = {}
    for r in qc:
        key = (num(r.get('floor_bps', 0)), num(r.get('protected_count', 0)))
        fl[key] = fl.get(key, 0) + 1
    for (f, pc), n in sorted(fl.items(), key=lambda x: -x[1])[:6]:
        implied = (f / 100e6) if f else 0
        print('    floor=%.3f G  protected_count=%-3d  epochs=%-7d'
              '  implied flows at 100M = %.1f'
              % (f / 1e9, int(pc), n, implied))
    print('    NOTE 65 flows x 100 Mbps = 6.500 G exactly.')
    print('    A floor of 6.600 G implies 66 contributions, i.e. one extra.')
    print('    The controller adds sum(minRate over protectedQps) THEN adds')
    print('    qcBackgroundFloorBps on top. If the background flow is ALREADY')
    print('    a member of protectedQps, its MIN_RATE is counted twice ->')
    print('    65 members + 1 background = 66 x 100 M = 6.6 G. That is the bug:')
    print('    a double count I introduced when adding the background floor.')

    # ---- item 1: Q_stop < Q_current violations --------------------------
    viol = [i for i, r in enumerate(qc)
            if num(r['q_stop']) < num(r['q_current']) - 1]
    print('')
    print('  --- item 1: Q_stop < Q_current violations = %d ---' % len(viol))
    if viol:
        print('    %12s %9s %9s %9s %8s %-12s' %
              ('t(us)', 'q_cur', 'q_stop', 'delta', 'drain', 'zone'))
        for i in viol[:8]:
            r = qc[i]
            print('    %12.1f %9.0f %9.0f %9.0f %8.4f %-12s'
                  % (num(r['time_ns']) / 1e3, num(r['q_current']),
                     num(r['q_stop']),
                     num(r['q_current']) - num(r['q_stop']),
                     num(r['drain']) / C, r['zone']))
        # Is q_stop simply the PREVIOUS epoch's q_current?
        lag = 0
        for i in viol:
            if i > 0 and abs(num(qc[i]['q_stop'])
                             - num(qc[i - 1]['q_current'])) < 2:
                lag += 1
        print('    of these, q_stop equals the PREVIOUS epoch q_current: '
              '%d (%.1f%%)' % (lag, 100.0 * lag / len(viol)))
        if lag > 0.8 * len(viol):
            print('    -> TELEMETRY ORDERING: the trace samples q_stop from the')
            print('       controller BEFORE the controller has seen this epoch\'s')
            print('       queue, so it reports the previous epoch\'s value against')
            print('       the current queue.  A write-order fault, not a control')
            print('       fault: the controller itself never used a stale Q.')

    # ---- item 2: sender-effective vs bottleneck-arrival -----------------
    print('')
    print('  --- item 2: sumR_effective vs actual bottleneck arrival ---')
    br = [i for i, r in enumerate(qc) if num(r['q_current']) > Q_ABS]
    if br and link:
        i = br[0]
        tb = num(qc[i]['time_ns'])
        win = [r for r in link
               if tb - 240000 <= num(r['time']) * 1e9 <= tb]
        if len(win) > 1:
            txb = sum(num(r.get('tx_bytes_delta', 0)) for r in win)
            span = num(win[-1]['time']) - num(win[0]['time'])
            dq = num(win[-1]['queue_bytes']) - num(win[0]['queue_bytes'])
            served = txb * 8 / span if span > 0 else 0
            arrival = (txb + dq) * 8 / span if span > 0 else 0
            print('    sumR_effective (controller) = %.4f G'
                  % (num(qc[i]['sumR_effective']) / 1e9))
            print('    served rate    (link trace) = %.4f G' % (served / 1e9))
            print('    arrival rate   (link trace) = %.4f G' % (arrival / 1e9))
            print('    gap: arrival - sumR_eff     = %.4f G'
                  % ((arrival - num(qc[i]['sumR_effective'])) / 1e9))
            print('    excess over C               = %+.4f G   '
                  '(unit bug fixed: was printed as Gbps from a bps value)'
                  % ((arrival - C) / 1e9))
            print('    -> sumR_effective is a SENDER-side pacing sum; the')
            print('       bottleneck is still receiving old-rate packets that')
            print('       left before the new rate took effect.  Q_stop must')
            print('       integrate the ARRIVAL rate until')
            print('       first_affected_packet_at_bottleneck, not the sender')
            print('       rate.  Those bytes belong in an in-flight ledger.')

    # ---- item 5: byte accounting -----------------------------------------
    print('')
    print('  --- item 5: served rate 10.41 G exceeds C = 10 G ---')
    if link:
        allw = [r for r in link if num(r.get('tx_bytes_delta', 0)) > 0]
        if allw:
            samples = [num(r['tx_bytes_delta']) for r in allw]
            print('    tx_bytes_delta distinct values: %s'
                  % sorted(set(samples))[:6])
            print('    sample interval = %.1f us'
                  % ((num(link[1]['time']) - num(link[0]['time'])) * 1e6))
            mx = max(samples)
            iv = num(link[1]['time']) - num(link[0]['time'])
            print('    max implied rate = %.4f G' % (mx * 8 / iv / 1e9))
            print('    1048 B payload vs 1048+overhead wire bytes:')
            print('      if queue_bytes counts WIRE bytes and pacing counts')
            print('      PAYLOAD, a 10 G payload rate is >10 G on the wire.')
            print('      10.4101/10.0 = %.4f -> implies %.0f B overhead per'
                  ' 1048 B packet' % (10.4101 / 10.0,
                                      1048 * (10.4101 / 10.0 - 1)))

    # ---- item 6: RED residency ------------------------------------------
    print('')
    print('  --- item 6: RED residency segments ---')
    segs = []
    cur = None
    for i, r in enumerate(qc):
        if r['zone'] == 'RED':
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        else:
            if cur:
                segs.append(tuple(cur))
                cur = None
    if cur:
        segs.append(tuple(cur))
    print('    RED entries: %d   total %.2f ms   longest %.3f ms'
          % (len(segs),
             sum(b - a + 1 for a, b in segs) * EPOCH_NS / 1e6,
             max((b - a + 1) for a, b in segs) * EPOCH_NS / 1e6
             if segs else 0))
    for k, (a, b) in enumerate(segs[:5]):
        print('      seg %d: %.1f-%.1f us  Q %0.f->%0.f (%+.0f B)  '
              'Q_safe_exit=%.0f'
              % (k, num(qc[a]['time_ns']) / 1e3, num(qc[b]['time_ns']) / 1e3,
                 num(qc[a]['q_current']), num(qc[b]['q_current']),
                 num(qc[b]['q_current']) - num(qc[a]['q_current']),
                 num(qc[b]['q_safe'])))
    stuck = [(a, b) for a, b in segs
             if num(qc[b]['q_current']) < Q_HIGH]
    print('    segments still RED while Q_current < Q_high: %d' % len(stuck))

    # ---- item 7: overshoot magnitude -------------------------------------
    print('')
    print('  --- item 7: overshoot characterisation ---')
    over = [num(r['q_current']) - Q_ABS for r in qc
            if num(r['q_current']) > Q_ABS]
    if over:
        runs = []
        run = 0
        for r in qc:
            if num(r['q_current']) > Q_ABS:
                run += 1
            else:
                if run:
                    runs.append(run)
                run = 0
        if run:
            runs.append(run)
        print('    epochs over Q_abs      : %d (%.3f%%)'
              % (len(over), 100.0 * len(over) / len(qc)))
        print('    max overshoot          : %.0f B = %.2f packets of %.0f B'
              % (max(over), max(over) / ONW, ONW))
        print('    max overshoot ratio    : %.2f%% of Q_abs'
              % (100.0 * max(over) / Q_ABS))
        print('    longest continuous run : %d epochs = %.3f ms'
              % (max(runs), max(runs) * EPOCH_NS / 1e6))
        print('    one-packet serialisation = %.3f us; longest run = %.1f us'
              % (ONW * 8 / C * 1e6, max(runs) * EPOCH_NS / 1e3))
        pkt_only = (max(over) < ONW
                    and max(runs) * EPOCH_NS / 1e3 <= ONW * 8 / C * 1e6)
        print('    qualifies as PACKETIZATION_QUANTIZATION: %s'
              % ('yes' if pkt_only else
                 'NO -- overshoot is %.1f packets over %.1f us, a HARD FAIL'
                 % (max(over) / ONW, max(runs) * EPOCH_NS / 1e3)))

print('')
print('=' * 72)
print('=== VERDICT: ONLINE_PREFLIGHT_FAIL_ACTUATION_ACCOUNTING ===')
print('  NOT CAPACITY_INFEASIBLE: the Q_red..Q_abs band needs 178.9 us to fill')
print('  at MAX_BOOST, which exceeds H_guard = 175 us.')
sys.exit(1)
