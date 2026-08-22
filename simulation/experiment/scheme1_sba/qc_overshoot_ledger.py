# If the actual queue still exceeds Q_abs, item 8 requires the FIRST breaching
# epoch's complete prediction ledger and arrival ledger. Producing it is the
# required action -- widening Q_abs, lowering MAX_BOOST or changing rho is not.
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

CELLS = [('rho=0.90', 'qc_s3_rho090'), ('rho=0.9875', 'qc_s3_rho09875')]


def rows(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


os.chdir(os.path.dirname(os.path.abspath(__file__)))
any_breach = False

for label, cell in CELLS:
    qc = rows(cell + '_out/qc_trace.csv')
    link = rows(cell + '_out/selected_link_timeseries.csv')
    if not qc:
        print('%s: no trace' % label)
        continue
    print('')
    print('=' * 70)
    print('=== %s' % label)
    print('=' * 70)

    peak_q = max(num(r['q_current']) for r in qc)
    print('  actual queue peak (controller view) = %.0f B = %.1f%% of Q_abs'
          % (peak_q, 100.0 * peak_q / Q_ABS))
    if link:
        peak_l = max(num(r['queue_bytes']) for r in link)
        print('  actual queue peak (link trace)      = %.0f B = %.1f%% of Q_abs'
              % (peak_l, 100.0 * peak_l / Q_ABS))

    breach = [i for i, r in enumerate(qc) if num(r['q_current']) > Q_ABS]
    if not breach:
        print('  NO EPOCH EXCEEDED Q_abs')
        continue
    any_breach = True
    i = breach[0]
    print('')
    print('  FIRST BREACHING EPOCH: index %d, t = %.3f us'
          % (i, num(qc[i]['time_ns']) / 1e3))
    print('  total breaching epochs: %d (%.3f%% of %d)'
          % (len(breach), 100.0 * len(breach) / len(qc), len(qc)))

    print('')
    print('  --- prediction ledger at that epoch ---')
    for k in ('q_current', 'q_stop', 'q_safe', 'boost_commanded',
              'boost_effective', 'drain', 'pending_generation',
              'sumR_effective', 'zone', 'floor_bps', 'drain_max_bps',
              'pending_excess_bytes', 'protected_count',
              'invariant_violations', 'guard_exceeded'):
        if k in qc[i]:
            print('    %-22s %s' % (k, qc[i][k]))
    print('    %-22s %.0f B' % ('Q_low', Q_LOW))
    print('    %-22s %.0f B' % ('Q_high', Q_HIGH))
    print('    %-22s %.0f B' % ('Q_red', Q_RED))
    print('    %-22s %.0f B' % ('Q_abs', Q_ABS))

    print('')
    print('  --- run-up: 12 epochs before the breach ---')
    print('    %10s %9s %9s %9s %8s %8s %-13s'
          % ('t(us)', 'q_cur', 'q_stop', 'q_safe', 'boost', 'drain', 'zone'))
    for j in range(max(0, i - 12), i + 2):
        r = qc[j]
        print('    %10.1f %9.0f %9.0f %9.0f %8.4f %8.4f %-13s'
              % (num(r['time_ns']) / 1e3, num(r['q_current']),
                 num(r['q_stop']), num(r['q_safe']),
                 num(r['boost_effective']) / C, num(r['drain']) / C,
                 r['zone']))

    # Arrival ledger: what actually arrived versus what was served.
    if link:
        tb = num(qc[i]['time_ns'])
        win = [r for r in link
               if tb - 200000 <= num(r['time']) * 1e9 <= tb + 50000]
        if win:
            print('')
            print('  --- arrival ledger (link trace, 200 us before breach) ---')
            tx = sum(num(r.get('tx_bytes_delta', 0)) for r in win)
            span = (num(win[-1]['time']) - num(win[0]['time']))
            print('    samples=%d  span=%.2f us' % (len(win), span * 1e6))
            print('    tx bytes over window   = %.0f B' % tx)
            if span > 0:
                print('    served rate            = %.4f Gbps'
                      % (tx * 8 / span / 1e9))
            dq = num(win[-1]['queue_bytes']) - num(win[0]['queue_bytes'])
            print('    queue delta            = %+.0f B' % dq)
            if span > 0:
                print('    implied arrival rate   = %.4f Gbps'
                      % ((tx + dq) * 8 / span / 1e9))
                print('    implied excess over C  = %+.4f Gbps'
                      % (((tx + dq) * 8 / span) - C) )
            print('    ECN marks over window  = %.0f'
                  % sum(num(r.get('ecn_marks_delta', 0)) for r in win))
            print('    PFC pause ns           = %.0f'
                  % sum(num(r.get('pfc_pause_ns_delta', 0)) for r in win))

print('')
if any_breach:
    print('=== VERDICT: Q_abs still exceeded. ===')
    print('  Reporting the ledger as required. NOT widening Q_abs, NOT lowering')
    print('  MAX_BOOST, NOT changing rho.')
    sys.exit(1)
print('=== VERDICT: no epoch exceeded Q_abs in either cell. ===')
sys.exit(0)
