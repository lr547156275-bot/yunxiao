# -*- coding: utf-8 -*-
# Per-rate summary tables in the user's review format:
#   rows  = scenario x {mean FCT, p99 FCT, BCT, Throughput, CCT}
#   cols  = CBAP-SBA, HPCC, DCQCN-SN, DCQCN-LowQ, DCTCP-SN, TIMELY,
#           Best algorithm, CBAP vs best baseline (%)
# Definitions (v1-frozen):
#   FCT_i = last_ack_i - first_data_tx_i          (per flow)
#   BCT   = max(last_ack) - network_release       (batch)
#   CCT   = max(last_ack) - application_ready     (batch)
#   Thr   = fanin*size*8 / CCT                    (payload Gbit/s)
#   CBAP vs best baseline: time metrics (best_bl - cbap)/best_bl,
#   throughput (cbap - best_bl)/best_bl; positive = CBAP better.
# Emits reports/tables_v2/summary_{10,200,400}g.csv and one styled
# summary_tables.html.  Reads only formal-matrix raw outputs.
import csv
import os

V2 = '/work/v2_400g'
RS = V2 + '/results'
OUT = V2 + '/reports/tables_v2'
os.path.isdir(OUT) or os.makedirs(OUT)
SCEN = {'s0': (64, 262144), 's1': (64, 1048576), 's2': (64, 4194304),
        's3': (64, 16777216), 's4': (64, 4194304), 's5': (32, 8388608)}
ARMS = [('cbap', 'CBAP-SBA'), ('hpcc', 'HPCC'), ('dcqn', 'DCQCN-SN'),
        ('dcql', 'DCQCN-LowQ'), ('dctcp', 'DCTCP-SN'),
        ('timely', 'TIMELY')]
METRICS = ['mean FCT (ms)', 'p99 FCT (ms)', 'BCT (ms)',
           'Throughput (Gbit/s)', 'CCT (ms)']


def cell(tag, fanin, size):
    p = RS + '/' + tag + '/flow_timing.csv'
    if not os.path.isfile(p):
        return None
    fcts = []
    last = ready = release = 0.0
    with open(p) as fh:
        for r in csv.DictReader(fh):
            try:
                if r['flow_id'] == '0' or \
                        float(r['total_size_bytes']) != float(size):
                    continue
                la = float(r['last_ack_ns'])
                fcts.append((la - float(r['first_data_tx_ns'])) / 1e6)
                if la > last:
                    last = la
                ready = float(r['application_ready_ns'])
                release = float(r['network_release_ns'])
            except (KeyError, ValueError):
                continue
    if len(fcts) != fanin:
        return None
    fcts.sort()
    cct = (last - ready) / 1e6
    return {'mean FCT (ms)': sum(fcts) / len(fcts),
            'p99 FCT (ms)': fcts[int(round((len(fcts) - 1) * 0.99))],
            'BCT (ms)': (last - release) / 1e6,
            'Throughput (Gbit/s)': fanin * size * 8.0 / (cct * 1e6),
            'CCT (ms)': cct}


HTML = ['<html><head><meta charset="utf-8"><style>',
        'body{font-family:Segoe UI,Arial,sans-serif}',
        'table{border-collapse:collapse;margin:24px 0;font-size:13px}',
        'th{background:#1f4e79;color:#fff;padding:6px 12px;'
        'border:1px solid #b8cce4}',
        'td{padding:4px 12px;border:1px solid #b8cce4;text-align:right}',
        'td.s{text-align:left;background:#dce9f5;font-weight:bold}',
        'td.m{text-align:left}',
        'tr.alt td{background:#eef5fb}',
        'td.best{background:#d8e8d0;font-weight:bold}',
        'td.pos{background:#d8e8d0;color:#1a6b1a;font-weight:bold}',
        'td.neg{background:#f8d7cc;color:#b30000;font-weight:bold}',
        'td.cb{background:#e8f1fa}',
        'h2{font-family:Segoe UI,Arial}',
        '</style></head><body>',
        '<h1>CBAP-SBA v2 formal matrix — per-rate summary tables</h1>',
        '<p>FCT = last_ack − first_data_tx (per flow); BCT/CCT = batch '
        'max(last_ack) − release/ready; Throughput = batch payload / CCT. '
        'Positive last column = CBAP better than the best baseline.</p>']

for rate in (10, 200, 400):
    HTML.append('<h2>%d Gbps</h2><table>' % rate)
    HTML.append('<tr><th>Scenario</th><th>Metric</th>' +
                ''.join('<th>%s</th>' % n for _, n in ARMS) +
                '<th>Best algorithm</th>'
                '<th>CBAP vs best baseline</th></tr>')
    csvrows = [['scenario', 'metric'] + [n for _, n in ARMS] +
               ['best_algorithm', 'cbap_vs_best_baseline_pct']]
    for scen in ('s0', 's1', 's2', 's3', 's4', 's5'):
        fanin, size = SCEN[scen]
        vals = {}
        for arm, name in ARMS:
            vals[name] = cell('fm%dg_%s_%s' % (rate, scen, arm),
                              fanin, size)
        alt = False
        for met in METRICS:
            hi = met.startswith('Throughput')
            row = {n: (vals[n][met] if vals[n] else None)
                   for _, n in ARMS}
            ok = {n: v for n, v in row.items() if v is not None}
            best = (max if hi else min)(ok, key=lambda n: ok[n])
            bl = {n: v for n, v in ok.items() if n != 'CBAP-SBA'}
            bbn = (max if hi else min)(bl, key=lambda n: bl[n])
            cb = ok.get('CBAP-SBA')
            pct = None
            if cb is not None:
                pct = ((cb - bl[bbn]) / bl[bbn] if hi
                       else (bl[bbn] - cb) / bl[bbn]) * 100
            cls = ' class="alt"' if alt else ''
            tds = ['<td class="s">%s</td>' % scen.upper(),
                   '<td class="m">%s</td>' % met]
            for _, n in ARMS:
                v = row[n]
                c = 'best' if n == best else ('cb' if n == 'CBAP-SBA'
                                              else '')
                tds.append('<td class="%s">%s</td>'
                           % (c, '%.6f' % v if v is not None else 'n/a'))
            tds.append('<td class="m">%s</td>' % best)
            tds.append('<td class="%s">%s</td>'
                       % ('pos' if pct is not None and pct >= 0
                          else 'neg',
                          '%.2f%%' % pct if pct is not None else 'n/a'))
            HTML.append('<tr%s>%s</tr>' % (cls, ''.join(tds)))
            csvrows.append([scen.upper(), met] +
                           ['%.6f' % row[n] if row[n] is not None
                            else '' for _, n in ARMS] +
                           [best, '%.2f' % pct if pct is not None
                            else ''])
            alt = not alt
    HTML.append('</table>')
    with open('%s/summary_%dg.csv' % (OUT, rate), 'w',
              newline='') as fh:
        csv.writer(fh).writerows(csvrows)
    print('summary_%dg.csv written' % rate)
HTML.append('</body></html>')
open(OUT + '/summary_tables.html', 'w').write('\n'.join(HTML))
print('summary_tables.html written')
