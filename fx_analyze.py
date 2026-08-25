# -*- coding: utf-8 -*-
# Frontier-extension analyzer: fx* cells (ultra-low-threshold baselines)
# printed side by side with the corresponding FORMAL matrix rows (cbap and
# the prior baseline arms) so the rate-for-queue tradeoff is read in one
# table.  Emits reports/05_frontier_ext_results.csv (fx rows only; the
# formal csv is untouched).
import csv
import glob
import os
import re

V2 = '/work/v2_400g'
RS = V2 + '/results'
P2W = 1000.0 / 952.0
SCEN = {'s0': (64, 262144), 's1': (64, 1048576), 's2': (64, 4194304),
        's3': (64, 16777216), 's4': (64, 4194304)}
ORDER = ['cbap', 'hpcc', 'hpccx', 'dcqn', 'dcql', 'dcqx', 'dctcp',
         'dctcpx', 'timely']


def rd(p):
    if not os.path.isfile(p):
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


def f(r, k, d=None):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return d


def cell_metrics(tag, rate, scen):
    d = os.path.join(RS, tag)
    if not os.path.isdir(d):
        return None
    C = rate * 1e9
    fanin, sbytes = SCEN[scen]
    ft = rd(d + '/flow_timing.csv')
    fs = rd(d + '/flow_summary.csv')
    incast = [r for r in ft if r.get('flow_id') != '0' and
              f(r, 'total_size_bytes', 0) == float(sbytes)]
    ccts = []
    for r in incast:
        la = f(r, 'last_ack_ns')
        ref = f(r, 'application_ready_ns', 0) or \
            f(r, 'network_release_ns', 0) or 0
        if la and ref:
            ccts.append((la - ref) / 1e6)
    ccts.sort()
    qpeak = 0.0
    for r in rd(d + '/selected_link_timeseries.csv'):
        q = f(r, 'queue_bytes', 0) or 0
        if q > qpeak:
            qpeak = q
    bg_tail = None
    ts = [r for r in rd(d + '/selected_flow_timeseries.csv')
          if r.get('flow_id') == '0']
    if len(ts) >= 3:
        a, b = ts[-3], ts[-1]
        t0, t1 = f(a, 'time', 0), f(b, 'time', 0)
        u0, u1 = f(a, 'snd_una', 0), f(b, 'snd_una', 0)
        if t1 > t0:
            bg_tail = (u1 - u0) * 8.0 / (t1 - t0) / 1e9
    ideal = fanin * sbytes * 8.0 * P2W / C * 1e3
    return {'n': len(ccts), 'fanin': fanin,
            'mean': sum(ccts) / len(ccts) if ccts else None,
            'p99': ccts[int(round((len(ccts) - 1) * 0.99))] if ccts
            else None,
            'ideal': ideal,
            'qpk': qpeak / 1048576.0,
            'qdly': qpeak * 8.0 / C * 1e6,
            'pfc': len(rd(d + '/pfc_events.csv')),
            'retx': sum(int(float(r.get('retx_events', 0) or 0))
                        for r in fs),
            'bg': bg_tail}


groups = {}
for d in sorted(glob.glob(RS + '/fx*')):
    m = re.match(r'fx(\d+)g_(s\d)_(\w+)$', os.path.basename(d))
    if m:
        groups.setdefault((int(m.group(1)), m.group(2)), [])

out_rows = []
for (rate, scen) in sorted(groups):
    fanin, sbytes = SCEN[scen]
    print('')
    print('== %dG %s (%dx%.0fKiB)  ideal %.3f ms  '
          '[fm = formal matrix, fx = ultra-low-threshold extension] =='
          % (rate, scen, fanin, sbytes / 1024.0,
             fanin * sbytes * 8.0 * P2W / (rate * 1e9) * 1e3))
    print('%-8s %-3s %6s %9s %9s %8s %9s %6s %5s %8s' %
          ('arm', 'src', 'n', 'meanCCT', 'p99CCT', 'Qpk_MB', 'qdly_us',
           'PFC', 'retx', 'bg_tailG'))
    for arm in ORDER:
        for pre, src in (('fm', 'fm'), ('fx', 'fx')):
            tag = '%s%dg_%s_%s' % (pre, rate, scen, arm)
            mtr = cell_metrics(tag, rate, scen)
            if mtr is None:
                continue
            print('%-8s %-3s %3d/%2d %9s %9s %8.3f %9.1f %6d %5d %8s' %
                  (arm, src, mtr['n'], mtr['fanin'],
                   '%.4f' % mtr['mean'] if mtr['mean'] else 'n/a',
                   '%.4f' % mtr['p99'] if mtr['p99'] else 'n/a',
                   mtr['qpk'], mtr['qdly'], mtr['pfc'], mtr['retx'],
                   '%.1f' % mtr['bg'] if mtr['bg'] is not None else 'n/a'))
            if pre == 'fx':
                out_rows.append([tag, rate, scen, arm, mtr['n'],
                                 mtr['fanin'], mtr['mean'], mtr['p99'],
                                 round(mtr['ideal'], 5),
                                 mtr['p99'] / mtr['ideal'] if mtr['p99']
                                 else None,
                                 round(mtr['qpk'], 4),
                                 round(mtr['qdly'], 2), mtr['pfc'],
                                 mtr['retx'], mtr['bg']])

with open(V2 + '/reports/05_frontier_ext_results.csv', 'w',
          newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['tag', 'rate_g', 'scenario', 'arm', 'n_complete', 'fanin',
                'mean_cct_ms', 'p99_cct_ms', 'ideal_ms', 'p99_over_ideal',
                'qpeak_mb', 'qdelay_us', 'pfc', 'retx', 'bg_tail_gbps'])
    for r in out_rows:
        w.writerow(r)
print('')
print('05_frontier_ext_results.csv written (%d fx cells)' % len(out_rows))
inc = [r[0] for r in out_rows if r[4] != r[5]]
if inc:
    print('INCOMPLETE fx cells: %s' % ', '.join(inc))
else:
    print('all fx cells complete')
