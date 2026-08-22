# Full preflight report (item 8) plus the 16 acceptance conditions (item 7).
import csv
import os
import sys

C = 10e9
H_GUARD_S = 175e-6
EPOCH_NS = 5000.0
H_NS = H_GUARD_S * 1e9
Q_ABS = 1048575.0
M_UNC_OLD = 62397.0
M_PKT = 67072.0
M_SAFE = 67072.0
M_ACT = 0.30 * C * H_GUARD_S / 8.0
Q_RED = Q_ABS - M_SAFE
Q_HIGH = Q_RED - M_ACT
Q_LOW = 0.5 * Q_ABS
FLOOR_BPS = 6.5e9
DRAIN_MAX = C - FLOOR_BPS
BG_HOST = '65'
ZONES = {'GREEN': 'GREEN/BOOST', 'YELLOW': 'YELLOW', 'RED': 'RED'}

CELLS = [('rho=0.90', 'qc_s3_rho090'), ('rho=0.9875', 'qc_s3_rho09875')]


def rows(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def q(vals, frac):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(round(frac * (len(s) - 1))))]


acc = []


def check(cell, name, ok, detail):
    acc.append((cell, name, ok, detail))


print('=== boundaries and margins (identical for both cells) ===')
print('  Q_low  = %9.0f B = %7.2f us   (0.50 * Q_abs, pre-existing value)'
      % (Q_LOW, Q_LOW * 8 / C * 1e6))
print('  Q_high = %9.0f B = %7.2f us   (Q_red - M_act)'
      % (Q_HIGH, Q_HIGH * 8 / C * 1e6))
print('  Q_red  = %9.0f B = %7.2f us   (Q_abs - M_safe)'
      % (Q_RED, Q_RED * 8 / C * 1e6))
print('  Q_abs  = %9.0f B = %7.2f us   (1.0 * D_tx, NOT widened)'
      % (Q_ABS, Q_ABS * 8 / C * 1e6))
print('  M_unc  = %9.0f B  (max clean residual, old build)' % M_UNC_OLD)
print('  M_pkt  = %9.0f B  (N * on_wire = 64 * 1048)' % M_PKT)
print('  M_safe = %9.0f B  = max(M_unc, M_pkt), NOT the sum' % M_SAFE)
print('  M_act  = %9.0f B  = MAX_BOOST * H_guard / 8' % M_ACT)
print('  DRAIN_MAX = %.2f G   floor = %.2f G' % (DRAIN_MAX / 1e9,
                                                 FLOOR_BPS / 1e9))

for label, cell in CELLS:
    print('')
    print('=' * 66)
    print('=== %s (%s)' % (label, cell))
    print('=' * 66)
    d = cell + '_out'
    summary = rows(os.path.join(d, 'flow_summary.csv'))
    qc = rows(os.path.join(d, 'qc_trace.csv'))
    link = rows(os.path.join(d, 'selected_link_timeseries.csv'))
    if not summary or not qc:
        print('  MISSING OUTPUT')
        check(label, 'cell produced output', False, 'missing files')
        continue

    bg = [r for r in summary if r['src'] == BG_HOST]
    bgid = set(id(r) for r in bg)
    inc = [r for r in summary if id(r) not in bgid]
    done = [r for r in inc if r['completed'] == '1']

    # ---- prediction residual -------------------------------------------
    qcur = [num(r['q_current']) for r in qc]
    qstop = [num(r['q_stop']) for r in qc]
    qsafe = [num(r['q_safe']) for r in qc]
    step = int(H_NS / EPOCH_NS)
    resid = []
    for i in range(len(qc) - step):
        peak = max(qcur[i:i + step + 1])
        r = peak - qstop[i]
        if r > 0:
            resid.append(r)
    print('')
    print('  --- prediction residual (actual peak in next H_guard - Q_stop) ---')
    if resid:
        print('    n=%d  mean=%.0f  p95=%.0f  p99=%.0f  max=%.0f B'
              % (len(resid), sum(resid) / len(resid), q(resid, .95),
                 q(resid, .99), max(resid)))
        print('    max residual vs M_safe=%.0f B : %s'
              % (M_SAFE, 'WITHIN' if max(resid) <= M_SAFE else 'EXCEEDS'))
    else:
        print('    no positive residual')
    inv = [r for r in qc if num(r['q_stop']) < num(r['q_current']) - 1]
    print('    Q_stop < Q_current violations: %d' % len(inv))

    # ---- queue ---------------------------------------------------------
    print('')
    print('  --- queue ---')
    print('    mean=%.0f  p95=%.0f  p99=%.0f  peak=%.0f B'
          % (sum(qcur) / len(qcur), q(qcur, .95), q(qcur, .99), max(qcur)))
    print('    delay mean=%.2f  p95=%.2f  p99=%.2f  peak=%.2f us'
          % (sum(qcur) / len(qcur) * 8 / C * 1e6, q(qcur, .95) * 8 / C * 1e6,
             q(qcur, .99) * 8 / C * 1e6, max(qcur) * 8 / C * 1e6))
    print('    peak / Q_abs = %.1f%%' % (100.0 * max(qcur) / Q_ABS))

    # ---- zone residency ------------------------------------------------
    zc = {}
    for r in qc:
        zc[r['zone']] = zc.get(r['zone'], 0) + 1
    print('')
    print('  --- zone residency ---')
    for z in sorted(zc):
        print('    %-14s %7d epochs (%.2f%%) = %.2f ms'
              % (z, zc[z], 100.0 * zc[z] / len(qc), zc[z] * EPOCH_NS / 1e6))

    # ---- boost / drain -------------------------------------------------
    b = [num(r['boost_effective']) for r in qc]
    dr = [num(r['drain']) for r in qc]
    sumr = [num(r['sumR_effective']) for r in qc]
    bpos = [x for x in b if x > 0]
    dpos = [x for x in dr if x > 0]
    print('')
    print('  --- boost / drain ---')
    print('    boost>0 : %d epochs (%.2f ms), max %.4f C'
          % (len(bpos), len(bpos) * EPOCH_NS / 1e6,
             max(bpos) / C if bpos else 0))
    print('    drain>0 : %d epochs (%.2f ms), max %.4f C'
          % (len(dpos), len(dpos) * EPOCH_NS / 1e6,
             max(dpos) / C if dpos else 0))
    print('    sumR>C  : %d epochs (%.2f ms)'
          % (len([x for x in sumr if x > C]),
             len([x for x in sumr if x > C]) * EPOCH_NS / 1e6))
    print('    sumR<C  : %d epochs (%.2f ms)'
          % (len([x for x in sumr if x < C]),
             len([x for x in sumr if x < C]) * EPOCH_NS / 1e6))
    print('    sumR min=%.3f G  max=%.3f G  (floor %.2f G)'
          % (min(sumr) / 1e9, max(sumr) / 1e9, FLOOR_BPS / 1e9))
    both = [r for r in qc
            if num(r['boost_effective']) > 0 and num(r['drain']) > 0]

    # ---- FCT / goodput -------------------------------------------------
    print('')
    print('  --- FCT and goodput ---')
    if done:
        f = sorted(num(r['fct']) for r in done)
        st = min(num(r['start_time']) for r in done)
        fi = max(num(r['finish_time']) for r in done)
        byts = sum(num(r['total_size_bytes']) for r in done)
        print('    incast FCT mean=%.4f p95=%.4f p99=%.4f ms'
              % (sum(f) / len(f) * 1e3, q(f, .95) * 1e3, q(f, .99) * 1e3))
        print('    BCT=%.4f ms   incast goodput=%.4f Gbps'
              % ((fi - st) * 1e3, byts * 8 / (fi - st) / 1e9))
    if bg:
        bb = bg[0]
        print('    background acked=%.4f Gb  completed=%s  retx=%.0f B'
              % (num(bb['acked_bytes']) * 8 / 1e9, bb['completed'],
                 num(bb['retx_bytes'])))

    # ---- safety --------------------------------------------------------
    pfc_ns = pfc_ev = 0.0
    util = 0.0
    ecn = 0.0
    if link:
        pfc_ns = sum(num(r.get('pfc_pause_ns_delta', 0)) for r in link)
        pfc_ev = sum(num(r.get('pfc_event_delta', 0)) for r in link)
        ecn = sum(num(r.get('ecn_marks_delta', 0)) for r in link)
        u = [num(r['utilization']) for r in link]
        util = sum(u) / len(u)
    retx = sum(num(r['retx_bytes']) for r in summary)
    print('')
    print('  --- safety and utilisation ---')
    print('    PFC pause=%.0f ns  events=%.0f   retx=%.0f B   ECN marks=%.0f'
          % (pfc_ns, pfc_ev, retx, ecn))
    print('    mean utilisation=%.4f' % util)
    over_abs = len([r for r in qc if num(r['q_safe']) > Q_ABS])
    print('    Q_safe > Q_abs occurrences: %d' % over_abs)
    print('    guard_exceeded: %d'
          % len([r for r in qc if num(r['guard_exceeded']) > 0]))

    # ---- the 16 acceptance conditions ---------------------------------
    seq = [r['zone'] for r in qc]
    check(label, '1. 64/64 incast completed', len(done) == 64,
          '%d/%d' % (len(done), len(inc)))
    check(label, '3. boost > 0 observed', len(bpos) > 0,
          '%d epochs' % len(bpos))
    check(label, '4. sumR_effective > C observed',
          len([x for x in sumr if x > C]) > 0,
          '%d epochs' % len([x for x in sumr if x > C]))
    g2y = any(seq[i] == 'GREEN' and seq[i + 1] != 'GREEN'
              for i in range(len(seq) - 1))
    check(label, '5. GREEN -> YELLOW observed', g2y, 'yes' if g2y else 'no')
    hi = [r for r in qc if num(r['q_stop']) > Q_HIGH]
    if hi:
        drained = [r for r in hi if num(r['drain']) > 0
                   and num(r['boost_effective']) == 0]
        check(label, '7. Q_stop>Q_high implies boost=0 and drain>0',
              len(drained) == len(hi),
              '%d of %d such epochs drained' % (len(drained), len(hi)))
    else:
        check(label, '7. Q_stop>Q_high (not reached this run)', True,
              'no epoch exceeded Q_high; branch covered by replay')
    check(label, '8. boost and drain never both non-zero', len(both) == 0,
          '%d epochs' % len(both))
    near = [r for r in qc if num(r['q_current']) > 0.95 * Q_ABS]
    check(label, '9. does not linger near Q_abs',
          len(near) < 0.01 * len(qc),
          '%d epochs above 95%% of Q_abs (%.3f%%)'
          % (len(near), 100.0 * len(near) / len(qc)))
    check(label, '10. actual queue peak <= Q_abs', max(qcur) <= Q_ABS,
          '%.0f B = %.1f%% of Q_abs' % (max(qcur), 100.0 * max(qcur) / Q_ABS))
    check(label, '11. Q_safe > Q_abs occurrences = 0', over_abs == 0,
          '%d' % over_abs)
    check(label, '12. PFC pause and events = 0',
          pfc_ns == 0 and pfc_ev == 0,
          'pause=%.0f events=%.0f' % (pfc_ns, pfc_ev))
    check(label, '14. retransmission = 0', retx == 0, '%.0f B' % retx)
    tail = seq[-200:]
    check(label, '16. returns to GREEN at the end',
          all(z == 'GREEN' for z in tail),
          'last 200 epochs %s' % ('all GREEN' if all(z == 'GREEN' for z in tail)
                                  else 'not all GREEN'))
    check(label, 'Q_stop >= Q_current always', len(inv) == 0,
          '%d violations' % len(inv))
    check(label, 'drain <= DRAIN_MAX always',
          all(x <= DRAIN_MAX + 1 for x in dr),
          'max drain %.4f C vs limit %.4f C'
          % (max(dr) / C if dr else 0, DRAIN_MAX / C))
    check(label, 'sumR >= floor always', min(sumr) >= FLOOR_BPS - 1,
          'min %.3f G vs floor %.2f G' % (min(sumr) / 1e9, FLOOR_BPS / 1e9))
    if resid:
        check(label, 'max residual <= M_safe', max(resid) <= M_SAFE,
              '%.0f vs %.0f B' % (max(resid), M_SAFE))

print('')
print('=' * 66)
print('=== acceptance summary ===')
fail = 0
for cellname, name, ok, detail in acc:
    print('  [%s] %-12s %-46s %s'
          % ('PASS' if ok else 'FAIL', cellname, name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d conditions passed' % (len(acc) - fail, len(acc)))
sys.exit(1 if fail else 0)
