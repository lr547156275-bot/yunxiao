# -*- coding: utf-8 -*-
# v2 400G screening analyzer, round 2 (post bg-freeze fix).  Discovers every
# scrv2_* cell, applies the FROZEN selection rules over the union:
#   safety gates first : PFC == 0, retx == 0, bottleneck queue never above
#                        Q_abs, all 64 incast flows complete, AND the
#                        background flow is alive post-batch (>= 70% of its
#                        0.8C cap) -- this last gate was vacuous in round 1
#                        because a u32 truncation froze bg entirely.
#   primary metric     : mean CCT of the 64-flow batch
#                        (CCT = last_ack - application_ready)
#   tie rule           : within 0.3% of best -> prefer smaller BMAX, then
#                        smaller D_target
# Epoch-sweep cells (_e1/_e2) are reported but excluded from the D x B
# selection.  No parameter is retuned here; selection over the declared grid.
import csv
import glob
import os
import re

V2 = '/work/v2_400g'
RS = V2 + '/results'
Q_ABS = 4000000.0          # 400G x 80us / 8
BG_CAP = 320e9             # 0.8 x 400G wire
rows = []


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


cells = sorted(os.path.basename(d) for d in glob.glob(RS + '/scrv2_*')
               if os.path.isdir(d))
for tag in cells:
    m = re.match(r'scrv2_d(\d+)_b(\d+)(?:_e(\d+))?$', tag)
    if not m:
        continue
    dt, bm = int(m.group(1)), int(m.group(2))
    epoch = int(m.group(3)) if m.group(3) else 5
    d = os.path.join(RS, tag)
    ft = rd(d + '/flow_timing.csv')
    fs = rd(d + '/flow_summary.csv')
    incast = [r for r in ft if f(r, 'total_size_bytes', 0) == 4194304.0]
    done = [r for r in incast if f(r, 'application_ready_ns') and
            f(r, 'last_ack_ns')]
    ccts = sorted((f(r, 'last_ack_ns') - f(r, 'application_ready_ns')) / 1e6
                  for r in done)
    pfc = len(rd(d + '/pfc_events.csv'))
    retx = sum(int(float(r.get('retx_events', 0) or 0)) for r in fs)
    qpeak = 0.0
    for r in rd(d + '/selected_link_timeseries.csv'):
        q = f(r, 'queue_bytes', 0) or 0
        if q > qpeak:
            qpeak = q
    # bg liveness: sending rate over the tail of the run, from the last two
    # timeseries samples of flow 0 (snd_una delta / time delta)
    bg_tail_gbps = None
    bg_total_gb = None
    ts = [r for r in rd(d + '/selected_flow_timeseries.csv')
          if r.get('flow_id') == '0']
    if len(ts) >= 3:
        a, b = ts[-3], ts[-1]
        t0, t1 = f(a, 'time', 0), f(b, 'time', 0)
        u0, u1 = f(a, 'snd_una', 0), f(b, 'snd_una', 0)
        if t1 > t0:
            bg_tail_gbps = (u1 - u0) * 8.0 / (t1 - t0) / 1e9
        bg_total_gb = u1 / 1e9
    gates = []
    if len(done) != 64:
        gates.append('incomplete %d/64' % len(done))
    if pfc != 0:
        gates.append('PFC=%d' % pfc)
    if retx != 0:
        gates.append('retx=%d' % retx)
    if qpeak > Q_ABS:
        gates.append('Qpeak %.0f > Q_abs' % qpeak)
    if bg_tail_gbps is None:
        gates.append('bg tail unmeasured')
    elif bg_tail_gbps < 0.7 * BG_CAP / 1e9 * 0.952:   # payload-domain cap
        gates.append('bg starved (%.1fG tail)' % bg_tail_gbps)
    mean_cct = sum(ccts) / len(ccts) if ccts else None
    p99_cct = ccts[int(round((len(ccts) - 1) * 0.99))] if ccts else None
    rows.append({'tag': tag, 'dt': dt, 'bm': bm, 'epoch': epoch,
                 'mean_cct_ms': mean_cct, 'p99_cct_ms': p99_cct,
                 'qpeak_mb': qpeak / 1048576.0, 'pfc': pfc, 'retx': retx,
                 'bg_tail_gbps': bg_tail_gbps, 'bg_total_gb': bg_total_gb,
                 'gates': ';'.join(gates) or 'PASS'})

print('%-20s %3s %9s %9s %8s %5s %5s %9s %8s  %s' %
      ('cell', 'ep', 'meanCCT', 'p99CCT', 'Qpk_MB', 'PFC', 'retx',
       'bg_tailG', 'bg_totGB', 'gates'))
for r in rows:
    print('%-20s %3d %9s %9s %8.3f %5d %5d %9s %8s  %s' %
          (r['tag'], r['epoch'],
           '%.4f' % r['mean_cct_ms'] if r['mean_cct_ms'] else 'n/a',
           '%.4f' % r['p99_cct_ms'] if r['p99_cct_ms'] else 'n/a',
           r['qpeak_mb'], r['pfc'], r['retx'],
           '%.1f' % r['bg_tail_gbps'] if r['bg_tail_gbps'] is not None
           else 'n/a',
           '%.2f' % r['bg_total_gb'] if r['bg_total_gb'] is not None
           else 'n/a', r['gates']))

with open(V2 + '/reports/04_screening_results.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['cell', 'd_target_us', 'bmax_millis', 'epoch_us',
                'mean_cct_ms', 'p99_cct_ms', 'qpeak_mb', 'pfc', 'retx',
                'bg_tail_gbps', 'bg_total_gb', 'gates'])
    for r in rows:
        w.writerow([r['tag'], r['dt'], r['bm'], r['epoch'],
                    r['mean_cct_ms'], r['p99_cct_ms'],
                    round(r['qpeak_mb'], 4), r['pfc'], r['retx'],
                    r['bg_tail_gbps'], r['bg_total_gb'], r['gates']])

print('')
pool = [r for r in rows if r['epoch'] == 5 and r['gates'] == 'PASS'
        and r['mean_cct_ms']]
if not pool:
    print('SCREENING VERDICT: NO CELL PASSES THE SAFETY GATES -- stop, '
          'report, do not pick a winner')
else:
    best = min(r['mean_cct_ms'] for r in pool)
    ties = [r for r in pool if (r['mean_cct_ms'] - best) / best <= 0.003]
    ties.sort(key=lambda r: (r['bm'], r['dt']))
    w = ties[0]
    print('best mean CCT %.4f ms; %d candidate(s) within the 0.3%% tie band'
          % (best, len(ties)))
    for r in ties:
        print('  tie: %s  meanCCT %.4f ms' % (r['tag'], r['mean_cct_ms']))
    print('SCREENING WINNER (frozen rules, union grid): %s  '
          '(D_target=%dus BMAX=%.3f, mean CCT %.4f ms, p99 %.4f ms)'
          % (w['tag'], w['dt'], w['bm'] / 1000.0, w['mean_cct_ms'],
             w['p99_cct_ms']))
    eps = [r for r in rows if r['epoch'] != 5]
    if eps:
        base = [r for r in rows if r['dt'] == 8 and r['bm'] == 20
                and r['epoch'] == 5]
        print('epoch sweep on d08_b020 (informational, not in selection):')
        if base and base[0]['mean_cct_ms']:
            print('  epoch=5us  meanCCT %.4f ms' % base[0]['mean_cct_ms'])
        for r in sorted(eps, key=lambda x: x['epoch']):
            print('  epoch=%dus meanCCT %s  gates=%s'
                  % (r['epoch'],
                     '%.4f ms' % r['mean_cct_ms'] if r['mean_cct_ms']
                     else 'n/a', r['gates']))
    print('winner is a CANDIDATE pending your review; pilot generation '
          'stays gated until you approve it.')
