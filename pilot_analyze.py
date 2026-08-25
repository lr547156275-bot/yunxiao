# -*- coding: utf-8 -*-
# v2 pilot analyzer: one row per cell, grouped tables per (rate, size).
# Emits /work/v2_400g/reports/03_pilot_results.csv.  No selection logic --
# the pilot is comparison data; the 7-question analysis document is written
# from this table afterwards.
import csv
import glob
import os
import re

V2 = '/work/v2_400g'
RS = V2 + '/results'
P2W = 1000.0 / 952.0
SIZES = {'256k': 262144, '1m': 1048576, '4m': 4194304, '16m': 16777216}
ARM_ORDER = ['cbap', 'cbap0', 'hpcc', 'dcqs', 'dcqn', 'dcql']


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
for d in sorted(glob.glob(RS + '/pv*')):
    tag = os.path.basename(d)
    m = re.match(r'pv(\d+)g_(\w+?)_(cbap0|cbap|hpcc|dcqs|dcqn|dcql)'
                 r'(?:_b(\d+))?$', tag)
    if not m:
        continue
    rate = int(m.group(1))
    sname = m.group(2)
    arm = m.group(3)
    buf = int(m.group(4)) if m.group(4) else 64
    C = rate * 1e9
    sbytes = SIZES[sname]
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
    ideal_ms = 64 * sbytes * 8.0 * P2W / C * 1e3     # batch drain bound
    ratio = p99_cct / ideal_ms if p99_cct else None
    pfc = len(rd(d + '/pfc_events.csv'))
    retx = sum(int(float(r.get('retx_events', 0) or 0)) for r in fs)
    qpeak = 0.0
    for r in rd(d + '/selected_link_timeseries.csv'):
        q = f(r, 'queue_bytes', 0) or 0
        if q > qpeak:
            qpeak = q
    qdelay_us = qpeak * 8.0 / C * 1e6
    bg_tail = None
    bg_tot = None
    ts = [r for r in rd(d + '/selected_flow_timeseries.csv')
          if r.get('flow_id') == '0']
    if len(ts) >= 3:
        a, b = ts[-3], ts[-1]
        t0, t1 = f(a, 'time', 0), f(b, 'time', 0)
        u0, u1 = f(a, 'snd_una', 0), f(b, 'snd_una', 0)
        if t1 > t0:
            bg_tail = (u1 - u0) * 8.0 / (t1 - t0) / 1e9
        bg_tot = u1 / 1e9
    rows.append({'rate': rate, 'size': sname, 'arm': arm, 'buf': buf,
                 'tag': tag, 'n': len(ccts), 'mean_cct_ms': mean_cct,
                 'p99_cct_ms': p99_cct, 'ideal_ms': ideal_ms,
                 'p99_over_ideal': ratio, 'qpeak_mb': qpeak / 1048576.0,
                 'qdelay_us': qdelay_us, 'pfc': pfc, 'retx': retx,
                 'bg_tail_gbps': bg_tail, 'bg_total_gb': bg_tot})


def akey(r):
    return (r['rate'], SIZES[r['size']], r['buf'],
            ARM_ORDER.index(r['arm']) if r['arm'] in ARM_ORDER else 99)


rows.sort(key=akey)
groups = {}
for r in rows:
    groups.setdefault((r['rate'], r['size'], r['buf']), []).append(r)

for (rate, sname, buf), rs in sorted(groups.items(),
                                     key=lambda kv: (kv[0][0],
                                                     SIZES[kv[0][1]],
                                                     kv[0][2])):
    print('')
    print('== %dG x 64x%s  buffer=%dMB  (ideal drain %.3f ms) =='
          % (rate, sname, buf, rs[0]['ideal_ms']))
    print('%-6s %5s %9s %9s %9s %8s %9s %5s %5s %9s' %
          ('arm', 'n/64', 'meanCCT', 'p99CCT', 'p99/idl', 'Qpk_MB',
           'qdly_us', 'PFC', 'retx', 'bg_tailG'))
    for r in rs:
        print('%-6s %5d %9s %9s %9s %8.3f %9.1f %5d %5d %9s' %
              (r['arm'], r['n'],
               '%.4f' % r['mean_cct_ms'] if r['mean_cct_ms'] else 'n/a',
               '%.4f' % r['p99_cct_ms'] if r['p99_cct_ms'] else 'n/a',
               '%.3f' % r['p99_over_ideal'] if r['p99_over_ideal']
               else 'n/a',
               r['qpeak_mb'], r['qdelay_us'], r['pfc'], r['retx'],
               '%.1f' % r['bg_tail_gbps'] if r['bg_tail_gbps'] is not None
               else 'n/a'))

with open(V2 + '/reports/03_pilot_results.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['tag', 'rate_g', 'size', 'arm', 'buffer_mb', 'n_complete',
                'mean_cct_ms', 'p99_cct_ms', 'ideal_ms', 'p99_over_ideal',
                'qpeak_mb', 'qdelay_us', 'pfc', 'retx', 'bg_tail_gbps',
                'bg_total_gb'])
    for r in rows:
        w.writerow([r['tag'], r['rate'], r['size'], r['arm'], r['buf'],
                    r['n'], r['mean_cct_ms'], r['p99_cct_ms'],
                    round(r['ideal_ms'], 5), r['p99_over_ideal'],
                    round(r['qpeak_mb'], 4), round(r['qdelay_us'], 2),
                    r['pfc'], r['retx'], r['bg_tail_gbps'],
                    r['bg_total_gb']])
print('')
print('csv written: reports/03_pilot_results.csv (%d cells)' % len(rows))
incomplete = [r['tag'] for r in rows if r['n'] != 64]
if incomplete:
    print('INCOMPLETE cells (n!=64): %s' % ', '.join(incomplete))
else:
    print('all cells complete (64/64 incast flows)')
