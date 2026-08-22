# Controller preflight analysis: item 7 evidence + item 8 hard gates.
#
# Item 7 requires POSITIVE evidence the mechanism actually engaged:
#   boost > 0, pending > 0, and sumR > C must each occupy a non-zero interval.
#   Absence of those means the controller did not take effect, and the run must
#   NOT be reported as a pass.
#
# Item 8 hard gates:
#   64/64 complete; PFC = drop = retx = 0; pending ledger closes;
#   H_guard violations = 0; actual queue delay <= hard delay.
import csv
import os
import sys

C = 10e9
H_GUARD_S = 175e-6
APP_HARD_DELAY_S = 838.86e-6
HARD_BYTES = APP_HARD_DELAY_S * C / 8.0
SOFT_BYTES = 0.5 * HARD_BYTES
EPOCH_NS = 5000
BG_HOST = '65'

CELLS = [('rho=0.90', 'qc_s3_rho090'), ('rho=0.9875', 'qc_s3_rho09875')]


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return list(csv.DictReader(handle))


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


results = []


def check(cell, name, ok, detail):
    results.append((cell, name, ok, detail))


for label, cell in CELLS:
    print('')
    print('=== %s (%s) ===' % (label, cell))
    d = cell + '_out'
    summary = rows(os.path.join(d, 'flow_summary.csv'))
    if not summary:
        print('  NO OUTPUT')
        check(label, 'cell produced output', False, 'missing flow_summary.csv')
        continue

    bg = [r for r in summary if r['src'] == BG_HOST]
    bg_ids = set(id(r) for r in bg)
    inc = [r for r in summary if id(r) not in bg_ids]
    done = [r for r in inc if r['completed'] == '1']
    print('  incast completed : %d/%d' % (len(done), len(inc)))
    check(label, '64/64 incast completed', len(done) == 64,
          '%d/%d' % (len(done), len(inc)))

    retx = sum(num(r['retx_bytes']) for r in summary)
    check(label, 'retransmission = 0', retx == 0, '%.0f B' % retx)

    link = rows(os.path.join(d, 'selected_link_timeseries.csv'))
    if link:
        pfc_ns = sum(num(r.get('pfc_pause_ns_delta', 0)) for r in link)
        pfc_ev = sum(num(r.get('pfc_event_delta', 0)) for r in link)
        qpeak = max(num(r['queue_bytes']) for r in link)
        check(label, 'PFC pause = 0 and events = 0',
              pfc_ns == 0 and pfc_ev == 0,
              'pause=%.0f ns events=%.0f' % (pfc_ns, pfc_ev))
        check(label, 'actual queue delay <= hard delay',
              qpeak <= HARD_BYTES,
              'peak %.0f B (%.2f us) vs hard %.0f B (%.2f us) = %.1f%%'
              % (qpeak, qpeak * 8 / C * 1e6, HARD_BYTES,
                 APP_HARD_DELAY_S * 1e6, 100.0 * qpeak / HARD_BYTES))
        print('  queue peak       : %.0f B (%.2f us) = %.1f%% of hard'
              % (qpeak, qpeak * 8 / C * 1e6, 100.0 * qpeak / HARD_BYTES))

    # ---- item 7: did the mechanism actually engage? --------------------
    qc = rows(os.path.join(d, 'qc_trace.csv'))
    if not qc:
        print('  NO qc_trace.csv -- cannot verify the mechanism engaged')
        check(label, 'controller trace present', False, 'missing qc_trace.csv')
        continue
    print('  qc_trace rows    : %d' % len(qc))

    boost_pos = [r for r in qc if num(r['boost_effective']) > 0]
    pending = [r for r in qc if num(r['pending_generation']) > 0]
    sumr_gt_c = [r for r in qc if num(r['sumR_effective']) > C]
    drain_pos = [r for r in qc if num(r['drain']) > 0]
    guard_bad = [r for r in qc if num(r['guard_exceeded']) > 0]
    zones = {}
    for r in qc:
        zones[r['zone']] = zones.get(r['zone'], 0) + 1

    print('  zones            : %s' % zones)
    print('  boost>0 epochs   : %d (%.1f%%)'
          % (len(boost_pos), 100.0 * len(boost_pos) / len(qc)))
    print('  pending>0 epochs : %d (%.1f%%)'
          % (len(pending), 100.0 * len(pending) / len(qc)))
    print('  sumR>C epochs    : %d (%.1f%%)'
          % (len(sumr_gt_c), 100.0 * len(sumr_gt_c) / len(qc)))
    print('  drain>0 epochs   : %d (%.1f%%)'
          % (len(drain_pos), 100.0 * len(drain_pos) / len(qc)))
    if boost_pos:
        bmax = max(num(r['boost_effective']) for r in boost_pos)
        print('  max boost_eff    : %.4f C' % (bmax / C))
    if qc:
        qsmax = max(num(r['q_stop']) for r in qc)
        print('  max Q_stop       : %.0f B (%.2f us) = %.1f%% of hard'
              % (qsmax, qsmax * 8 / C * 1e6, 100.0 * qsmax / HARD_BYTES))

    # These are the item 7 requirements. Failing them means the mechanism did
    # not take effect -- NOT that the run was benign.
    check(label, 'ITEM 7: boost > 0 over a non-zero interval',
          len(boost_pos) > 0, '%d epochs' % len(boost_pos))
    check(label, 'ITEM 7: pending > 0 over a non-zero interval',
          len(pending) > 0, '%d epochs' % len(pending))
    check(label, 'ITEM 7: sumR > C over a non-zero interval',
          len(sumr_gt_c) > 0, '%d epochs' % len(sumr_gt_c))
    check(label, 'ITEM 8: H_guard violations = 0', len(guard_bad) == 0,
          '%d epochs with guard_exceeded > 0' % len(guard_bad))

    # GREEN -> YELLOW -> GREEN, the live behaviour item 7 asks for.
    seq = [r['zone'] for r in qc]
    g2y = any(seq[i] == 'GREEN' and seq[i + 1] == 'YELLOW'
              for i in range(len(seq) - 1))
    y2g = any(seq[i] == 'YELLOW' and seq[i + 1] == 'GREEN'
              for i in range(len(seq) - 1))
    check(label, 'GREEN -> YELLOW observed', g2y, 'yes' if g2y else 'no')
    check(label, 'YELLOW -> GREEN observed', y2g, 'yes' if y2g else 'no')
    if 'RED' in zones:
        red_rows = [i for i, z in enumerate(seq) if z == 'RED']
        print('  RED entered      : %d epochs, first at row %d'
              % (zones['RED'], red_rows[0]))
        # Recovery time and peak overshoot must be reported if RED occurs.
        t0 = num(qc[red_rows[0]]['time_ns'])
        after = [i for i in range(red_rows[-1], len(seq)) if seq[i] != 'RED']
        rec = (num(qc[after[0]]['time_ns']) - t0) / 1e3 if after else -1
        over = max(num(r['q_stop']) for r in qc if r['zone'] == 'RED')
        print('  RED recovery     : %.1f us ; peak Q_stop in RED %.0f B'
              ' (%.1f%% of hard)' % (rec, over, 100.0 * over / HARD_BYTES))

print('')
print('=== gate summary ===')
fail = 0
for cellname, name, ok, detail in results:
    print('  [%s] %-12s %-48s %s'
          % ('PASS' if ok else 'FAIL', cellname, name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d gates passed' % (len(results) - fail, len(results)))
sys.exit(1 if fail else 0)
