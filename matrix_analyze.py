# -*- coding: utf-8 -*-
# v2 formal-matrix analyzer: one row per fm* cell, grouped tables per
# (rate, scenario, buffer).  Emits reports/final_results_v2.csv and flags
# every gate violation.  No selection logic and no tuning.
import csv
import glob
import os
import re

V2 = '/work/v2_400g'
RS = V2 + '/results'
P2W = 1000.0 / 952.0
SCEN = {'s0': (64, 262144), 's1': (64, 1048576), 's2': (64, 4194304),
        's3': (64, 16777216), 's4': (64, 4194304), 's5': (32, 8388608)}
ARM_ORDER = ['cbap', 'cbap0', 'hpcc', 'dcqn', 'dcql', 'dctcp', 'timely',
             'dcqs']
DABS_US = {10: 826.0, 200: 105.0, 400: 84.0}


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


rows = []
for d in sorted(glob.glob(RS + '/fm*')):
    tag = os.path.basename(d)
    m = re.match(r'fm(\d+)g_(s\d)_(\w+?)(?:_b(\d+))?$', tag)
    if not m:
        continue
    rate = int(m.group(1))
    scen = m.group(2)
    arm = m.group(3)
    buf = int(m.group(4)) if m.group(4) else 64
    C = rate * 1e9
    fanin, sbytes = SCEN[scen]
    ft = rd(d + '/flow_timing.csv')
    fs = rd(d + '/flow_summary.csv')
    incast = [r for r in ft if r.get('flow_id') != '0' and
              f(r, 'total_size_bytes', 0) == float(sbytes)]
    ccts = []
    for r in incast:
        la = f(r, 'last_ack_ns')
        ref = f(r, 'application_ready_ns', 0) or 0
        if not ref:
            ref = f(r, 'network_release_ns', 0) or 0
        if la and ref:
            ccts.append((la - ref) / 1e6)
    ccts.sort()
    mean_cct = sum(ccts) / len(ccts) if ccts else None
    p99_cct = ccts[int(round((len(ccts) - 1) * 0.99))] if ccts else None
    ideal_ms = fanin * sbytes * 8.0 * P2W / C * 1e3
    ratio = p99_cct / ideal_ms if p99_cct else None
    pfc = len(rd(d + '/pfc_events.csv'))
    retx = sum(int(float(r.get('retx_events', 0) or 0)) for r in fs)
    qpeak = 0.0
    for r in rd(d + '/selected_link_timeseries.csv'):
        q = f(r, 'queue_bytes', 0) or 0
        if q > qpeak:
            qpeak = q
    qdelay_us = qpeak * 8.0 / C * 1e6
    bg_tail = bg_tot = None
    ts = [r for r in rd(d + '/selected_flow_timeseries.csv')
          if r.get('flow_id') == '0']
    if len(ts) >= 3:
        a, b = ts[-3], ts[-1]
        t0, t1 = f(a, 'time', 0), f(b, 'time', 0)
        u0, u1 = f(a, 'snd_una', 0), f(b, 'snd_una', 0)
        if t1 > t0:
            bg_tail = (u1 - u0) * 8.0 / (t1 - t0) / 1e9
        bg_tot = u1 / 1e9
    gates = []
    if len(ccts) != fanin:
        gates.append('incomplete %d/%d' % (len(ccts), fanin))
    if retx != 0:
        gates.append('retx=%d' % retx)
    if arm.startswith('cbap') and qdelay_us > DABS_US[rate]:
        gates.append('CBAP over Q_abs (%.0fus > %.0fus)'
                     % (qdelay_us, DABS_US[rate]))
    if bg_tail is None:
        gates.append('bg tail unmeasured')
    rows.append({'rate': rate, 'scen': scen, 'arm': arm, 'buf': buf,
                 'tag': tag, 'n': len(ccts), 'fanin': fanin,
                 'mean_cct_ms': mean_cct, 'p99_cct_ms': p99_cct,
                 'ideal_ms': ideal_ms, 'p99_over_ideal': ratio,
                 'qpeak_mb': qpeak / 1048576.0, 'qdelay_us': qdelay_us,
                 'pfc': pfc, 'retx': retx, 'bg_tail_gbps': bg_tail,
                 'bg_total_gb': bg_tot,
                 'gates': ';'.join(gates) or 'PASS'})


def akey(r):
    return (r['rate'], r['scen'], r['buf'],
            ARM_ORDER.index(r['arm']) if r['arm'] in ARM_ORDER else 99)


rows.sort(key=akey)
groups = {}
for r in rows:
    groups.setdefault((r['rate'], r['scen'], r['buf']), []).append(r)
for (rate, scen, buf), rs in sorted(groups.items()):
    fanin, sbytes = SCEN[scen]
    print('')
    print('== %dG %s (%dx%.0fKiB) buffer=%dMB  ideal %.3f ms =='
          % (rate, scen, fanin, sbytes / 1024.0, buf, rs[0]['ideal_ms']))
    print('%-7s %6s %9s %9s %8s %8s %9s %5s %5s %9s  %s' %
          ('arm', 'n', 'meanCCT', 'p99CCT', 'p99/idl', 'Qpk_MB',
           'qdly_us', 'PFC', 'retx', 'bg_tailG', 'gates'))
    for r in rs:
        print('%-7s %3d/%2d %9s %9s %8s %8.3f %9.1f %5d %5d %9s  %s' %
              (r['arm'], r['n'], r['fanin'],
               '%.4f' % r['mean_cct_ms'] if r['mean_cct_ms'] else 'n/a',
               '%.4f' % r['p99_cct_ms'] if r['p99_cct_ms'] else 'n/a',
               '%.3f' % r['p99_over_ideal'] if r['p99_over_ideal']
               else 'n/a',
               r['qpeak_mb'], r['qdelay_us'], r['pfc'], r['retx'],
               '%.1f' % r['bg_tail_gbps'] if r['bg_tail_gbps'] is not None
               else 'n/a', r['gates']))

with open(V2 + '/reports/final_results_v2.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['tag', 'rate_g', 'scenario', 'arm', 'buffer_mb', 'fanin',
                'n_complete', 'mean_cct_ms', 'p99_cct_ms', 'ideal_ms',
                'p99_over_ideal', 'qpeak_mb', 'qdelay_us', 'pfc', 'retx',
                'bg_tail_gbps', 'bg_total_gb', 'gates'])
    for r in rows:
        w.writerow([r['tag'], r['rate'], r['scen'], r['arm'], r['buf'],
                    r['fanin'], r['n'], r['mean_cct_ms'], r['p99_cct_ms'],
                    round(r['ideal_ms'], 5), r['p99_over_ideal'],
                    round(r['qpeak_mb'], 4), round(r['qdelay_us'], 2),
                    r['pfc'], r['retx'], r['bg_tail_gbps'],
                    r['bg_total_gb'], r['gates']])
print('')
print('final_results_v2.csv written (%d cells)' % len(rows))
bad = [r for r in rows if r['gates'] != 'PASS']
if bad:
    print('GATE VIOLATIONS (%d):' % len(bad))
    for r in bad:
        print('  %s: %s' % (r['tag'], r['gates']))
else:
    print('all gates PASS')
