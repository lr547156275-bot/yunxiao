# Generate comparison charts as SVG from final_results.csv.
#
# Usage (python2 or python3, stdlib only):
#   python2 make_charts.py [final_report_dir]
#
# SVG rather than PNG deliberately: it is plain text, needs no plotting library
# or bitmap font, renders natively in any browser, and is vector output suitable
# for a paper.  The container has no matplotlib and hand-rasterising there would
# have added risk without improving the numbers.
#
# Emits into <final_report_dir>/charts/:
#   grouped bar charts   -- one metric, algorithms grouped per scenario
#   line charts          -- one metric across scenarios, one line per algorithm
#   Pareto scatter       -- the three trade-off pairings
# Every chart also writes the exact CSV it was drawn from, so the numbers are
# checkable without trusting the renderer.
import csv
import os
import sys

TAGS = ['s1', 's2', 's3', 's6', 's4', 's5']
TAG_LABEL = {
    's1': 'S1\n16x256K',
    's2': 'S2\n64x256K',
    's3': 'S3\n64x1M',
    's6': 'S6\ndual-bn',
    's4': 'S4\n64x1M/95%',
    's5': 'S5\n64x4M',
}
ALGOS = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
LABEL = {'dcqcn': 'DCQCN', 'dctcp': 'DCTCP', 'timely': 'TIMELY',
         'hpcc': 'HPCC', 'cbapsba': 'CBAP-SBA'}
# Colour-blind-safe palette; CBAP-SBA is the last and most saturated so it
# stands out as the algorithm under evaluation.
COLOR = {'dcqcn': '#4C72B0', 'dctcp': '#8172B2', 'timely': '#937860',
         'hpcc': '#55A868', 'cbapsba': '#C44E52'}

W, H = 900, 460
ML, MR, MT, MB = 88, 190, 46, 62      # margins: right holds the legend


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def nice_ticks(vmax, n=5):
    """Round axis maximum up to a readable step."""
    if vmax <= 0:
        return [0, 1], 1.0
    raw = vmax / float(n)
    mag = 10 ** int(('%e' % raw).split('e')[1])
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    else:
        step = 10 * mag
    top = step
    while top < vmax:
        top += step
    ticks = []
    v = 0.0
    while v <= top + step * 0.001:
        ticks.append(v)
        v += step
    return ticks, top


def fmt_tick(v, top):
    if top >= 1e6:
        return '%.1fM' % (v / 1e6) if v else '0'
    if top >= 1000:
        return '%.0fk' % (v / 1000) if v else '0'
    if top >= 10:
        return '%.0f' % v
    if top >= 1:
        return '%.1f' % v
    return '%.2f' % v


def svg_head(title, subtitle):
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="Helvetica,Arial,sans-serif">'
         % (W, H, W, H),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H),
         '<text x="%d" y="24" font-size="17" font-weight="bold" '
         'fill="#222">%s</text>' % (ML - 48, esc(title))]
    if subtitle:
        s.append('<text x="%d" y="40" font-size="11.5" fill="#666">%s</text>'
                 % (ML - 48, esc(subtitle)))
    return s


def axes(out, ticks, top, log=False):
    px0, px1 = ML, W - MR
    py0, py1 = H - MB, MT
    for t in ticks:
        y = py0 - (t / top) * (py0 - py1)
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#e4e4e4" '
                   'stroke-width="1"/>' % (px0, y, px1, y))
        out.append('<text x="%d" y="%.1f" font-size="10.5" fill="#666" '
                   'text-anchor="end">%s</text>' % (px0 - 8, y + 3.5,
                                                    fmt_tick(t, top)))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333" '
               'stroke-width="1.3"/>' % (px0, py0, px1, py0))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333" '
               'stroke-width="1.3"/>' % (px0, py0, px0, py1))


def legend(out, algos):
    x = W - MR + 18
    y = MT + 10
    for a in algos:
        out.append('<rect x="%d" y="%d" width="13" height="13" fill="%s" '
                   'rx="2"/>' % (x, y, COLOR[a]))
        out.append('<text x="%d" y="%d" font-size="11.5" fill="#333">%s</text>'
                   % (x + 19, y + 11, LABEL[a]))
        y += 22


def ylabel(out, text):
    cy = (MT + (H - MB)) / 2
    out.append('<text x="18" y="%d" font-size="11.5" fill="#444" '
               'text-anchor="middle" transform="rotate(-90 18 %d)">%s</text>'
               % (cy, cy, esc(text)))


def bar_chart(path, title, subtitle, unit, values, note=''):
    """values[(tag, algo)] -> number.  Algorithms grouped within each scenario."""
    vals = [v for v in values.values() if v is not None]
    if not vals:
        return False
    ticks, top = nice_ticks(max(vals))
    out = svg_head(title, subtitle)
    axes(out, ticks, top)
    ylabel(out, unit)
    px0, px1 = ML, W - MR
    py0, py1 = H - MB, MT
    span = (px1 - px0) / float(len(TAGS))
    bw = span * 0.72 / len(ALGOS)
    for i, tag in enumerate(TAGS):
        gx = px0 + i * span
        for j, a in enumerate(ALGOS):
            v = values.get((tag, a))
            if v is None:
                continue
            hgt = (v / top) * (py0 - py1)
            x = gx + span * 0.14 + j * bw
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                       'fill="%s" rx="1.5"><title>%s %s: %.4g</title></rect>'
                       % (x, py0 - hgt, bw * 0.9, hgt, COLOR[a],
                          tag.upper(), LABEL[a], v))
        for k, line in enumerate(TAG_LABEL[tag].split('\n')):
            out.append('<text x="%.1f" y="%d" font-size="%s" fill="#444" '
                       'text-anchor="middle">%s</text>'
                       % (gx + span / 2, py0 + 17 + k * 13,
                          '11.5' if k == 0 else '9.5', esc(line)))
    legend(out, ALGOS)
    if note:
        out.append('<text x="%d" y="%d" font-size="10" fill="#888">%s</text>'
                   % (ML, H - 8, esc(note)))
    out.append('</svg>')
    _write(path, out)
    return True


def line_chart(path, title, subtitle, unit, values, note=''):
    """One line per algorithm across scenarios."""
    vals = [v for v in values.values() if v is not None]
    if not vals:
        return False
    ticks, top = nice_ticks(max(vals))
    out = svg_head(title, subtitle)
    axes(out, ticks, top)
    ylabel(out, unit)
    px0, px1 = ML, W - MR
    py0, py1 = H - MB, MT
    span = (px1 - px0) / float(len(TAGS))
    xs = [px0 + span * (i + 0.5) for i in range(len(TAGS))]
    for a in ALGOS:
        pts = []
        for i, tag in enumerate(TAGS):
            v = values.get((tag, a))
            if v is None:
                continue
            pts.append((xs[i], py0 - (v / top) * (py0 - py1), v, tag))
        if len(pts) < 2:
            continue
        d = ' '.join('%s%.1f,%.1f' % ('M' if k == 0 else 'L', p[0], p[1])
                     for k, p in enumerate(pts))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4" '
                   'stroke-linejoin="round"/>' % (d, COLOR[a]))
        for p in pts:
            out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" '
                       'stroke="#fff" stroke-width="1.4"><title>%s %s: '
                       '%.4g</title></circle>'
                       % (p[0], p[1], COLOR[a], p[3].upper(), LABEL[a], p[2]))
    for i, tag in enumerate(TAGS):
        for k, line in enumerate(TAG_LABEL[tag].split('\n')):
            out.append('<text x="%.1f" y="%d" font-size="%s" fill="#444" '
                       'text-anchor="middle">%s</text>'
                       % (xs[i], py0 + 17 + k * 13,
                          '11.5' if k == 0 else '9.5', esc(line)))
    legend(out, ALGOS)
    if note:
        out.append('<text x="%d" y="%d" font-size="10" fill="#888">%s</text>'
                   % (ML, H - 8, esc(note)))
    out.append('</svg>')
    _write(path, out)
    return True


def pareto_chart(path, title, xlabel, ylabel_, xs_ys, note=''):
    """Scatter: one marker per (scenario, algorithm), shape-free, colour by algo."""
    pts = [(x, y, t, a) for (t, a), (x, y) in xs_ys.items()
           if x is not None and y is not None]
    if not pts:
        return False
    xmax = max(p[0] for p in pts)
    ymax = max(p[1] for p in pts)
    xt, xtop = nice_ticks(xmax)
    yt, ytop = nice_ticks(ymax)
    out = svg_head(title, 'one marker per scenario x algorithm; '
                          'lower-left or lower-right is better depending on axis')
    px0, px1 = ML, W - MR
    py0, py1 = H - MB, MT
    for t in yt:
        y = py0 - (t / ytop) * (py0 - py1)
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#e4e4e4"/>'
                   % (px0, y, px1, y))
        out.append('<text x="%d" y="%.1f" font-size="10.5" fill="#666" '
                   'text-anchor="end">%s</text>'
                   % (px0 - 8, y + 3.5, fmt_tick(t, ytop)))
    for t in xt:
        x = px0 + (t / xtop) * (px1 - px0)
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#eee"/>'
                   % (x, py0, x, py1))
        out.append('<text x="%.1f" y="%d" font-size="10.5" fill="#666" '
                   'text-anchor="middle">%s</text>'
                   % (x, py0 + 17, fmt_tick(t, xtop)))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333" '
               'stroke-width="1.3"/>' % (px0, py0, px1, py0))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333" '
               'stroke-width="1.3"/>' % (px0, py0, px0, py1))
    for x, y, tag, a in pts:
        cx = px0 + (x / xtop) * (px1 - px0)
        cy = py0 - (y / ytop) * (py0 - py1)
        out.append('<circle cx="%.1f" cy="%.1f" r="6" fill="%s" '
                   'fill-opacity="0.85" stroke="#fff" stroke-width="1.3">'
                   '<title>%s %s: (%.4g, %.4g)</title></circle>'
                   % (cx, cy, COLOR[a], tag.upper(), LABEL[a], x, y))
        out.append('<text x="%.1f" y="%.1f" font-size="8.5" fill="#555">%s</text>'
                   % (cx + 8, cy + 3, tag.upper()))
    out.append('<text x="%.1f" y="%d" font-size="11.5" fill="#444" '
               'text-anchor="middle">%s</text>'
               % ((px0 + px1) / 2, H - 24, esc(xlabel)))
    ylabel(out, ylabel_)
    legend(out, ALGOS)
    if note:
        out.append('<text x="%d" y="%d" font-size="10" fill="#888">%s</text>'
                   % (ML, H - 8, esc(note)))
    out.append('</svg>')
    _write(path, out)
    return True


def _write(path, lines):
    f = open(path, 'w')
    try:
        f.write('\n'.join(lines) + '\n')
    finally:
        f.close()


def dump_csv(path, values, metric, unit):
    f = open(path, 'w')
    try:
        w = csv.writer(f)
        w.writerow(['scenario', 'algorithm', 'metric', 'value', 'unit'])
        for tag in TAGS:
            for a in ALGOS:
                v = values.get((tag, a))
                if v is not None:
                    w.writerow([tag, LABEL[a], metric, '%.6f' % v, unit])
    finally:
        f.close()


def load(report_dir):
    rows = {}
    p = os.path.join(report_dir, 'final_results.csv')
    f = open(p)
    try:
        for r in csv.DictReader(f):
            rows[(r['scenario_tag'], r['algorithm'])] = r
    finally:
        f.close()
    return rows


def pick(rows, key, scale=1.0):
    out = {}
    for k, r in rows.items():
        v = r.get(key)
        if v in (None, ''):
            continue
        try:
            out[k] = float(v) * scale
        except ValueError:
            pass
    return out


CHARTS = [
    # (filename, kind, title, metric key, unit label, scale, note)
    ('01_fct_mean_bar', 'bar', 'Incast mean FCT', 'fct_mean_ms',
     'mean FCT (ms)', 1.0, 'lower is better'),
    ('02_fct_p99_bar', 'bar', 'Incast p99 FCT', 'fct_p99_ms',
     'p99 FCT (ms)', 1.0, 'lower is better'),
    ('03_fct_p50_bar', 'bar', 'Incast median (p50) FCT', 'fct_p50_ms',
     'p50 FCT (ms)', 1.0, 'lower is better'),
    ('04_cct_bar', 'bar', 'Collective completion time', 'cct_ms',
     'CCT (ms)', 1.0, 'time from release until the slowest member finishes'),
    ('05_goodput_bar', 'bar', 'Incast aggregate goodput', 'incast_agg_gbps',
     'goodput (Gbps)', 1.0, 'total bytes over the completion span; higher is better'),
    ('06_bg_retention_bar', 'bar', 'Background throughput retention',
     'bg_retention_pct', 'retention (%)', 1.0,
     'during the collective vs before; the three ECN baselines read 100% only '
     'because their collectives cannot displace the background flow'),
    ('07_bg_min_bar', 'bar', 'Background minimum instantaneous throughput',
     'bg_min_gbps', 'minimum (Gbps)', 1.0, 'higher is better'),
    ('08_queue_p99_bar', 'bar', 'Bottleneck queue p99', 'queue_p99_bytes',
     'queue p99 (bytes)', 1.0, 'measured over the collective occupancy window'),
    ('09_queue_peak_bar', 'bar', 'Bottleneck queue peak', 'queue_peak_bytes',
     'queue peak (bytes)', 1.0, 'Qmax (migration tolerance) is 400,000 B'),
    ('10_util_bar', 'bar', 'Bottleneck link utilisation', 'util_mean',
     'utilisation', 1.0, ''),
    ('11_jain_bar', 'bar', 'Intra-collective fairness (Jain)',
     'incast_fairness_jain', 'Jain index', 1.0, '1.0 = perfectly equal'),
    ('12_bg_debt_bar', 'bar', 'Background service debt',
     'bg_service_debt_bytes', 'debt (bytes)', 1.0,
     'bytes still owed at a scenario-fixed window; 0 means the flow completed'),
    ('13_fct_mean_line', 'line', 'Incast mean FCT across scenarios',
     'fct_mean_ms', 'mean FCT (ms)', 1.0, 'lower is better'),
    ('14_fct_p99_line', 'line', 'Incast p99 FCT across scenarios',
     'fct_p99_ms', 'p99 FCT (ms)', 1.0, 'lower is better'),
    ('15_goodput_line', 'line', 'Incast aggregate goodput across scenarios',
     'incast_agg_gbps', 'goodput (Gbps)', 1.0, 'higher is better'),
    ('16_bg_retention_line', 'line', 'Background retention across scenarios',
     'bg_retention_pct', 'retention (%)', 1.0, ''),
    ('17_queue_p99_line', 'line', 'Queue p99 across scenarios',
     'queue_p99_bytes', 'queue p99 (bytes)', 1.0, ''),
    ('18_bg_recovery_bar', 'bar', 'Background 90% recovery time',
     'bg_recovery90_ms', 'recovery (ms)', 1.0,
     '0 means the background flow never dipped below 90% of baseline'),
]

PARETOS = [
    ('19_pareto_retention_vs_p99fct', 'Pareto: background retention vs incast p99 FCT',
     'bg_retention_pct', 'background retention (%)',
     'fct_p99_ms', 'incast p99 FCT (ms)',
     'better is right and down: keeps background throughput while finishing fast'),
    ('20_pareto_debt_vs_cct', 'Pareto: background service debt vs CCT',
     'bg_service_debt_bytes', 'background service debt (bytes)',
     'cct_ms', 'CCT (ms)', 'better is left and down'),
    ('21_pareto_queue_vs_goodput', 'Pareto: queue p99 vs incast goodput',
     'queue_p99_bytes', 'queue p99 (bytes)',
     'incast_agg_gbps', 'incast aggregate goodput (Gbps)',
     'better is left and up: high goodput without deep queues'),
]

SUB = ('5 algorithms x 6 scenarios, one deterministic run each '
       '(no random source; seed inert)')


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'final_report')
    outdir = os.path.join(report, 'charts')
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    rows = load(report)
    print('loaded %d cells' % len(rows))
    made = 0
    for name, kind, title, key, unit, scale, note in CHARTS:
        vals = pick(rows, key, scale)
        fn = bar_chart if kind == 'bar' else line_chart
        if fn(os.path.join(outdir, name + '.svg'), title, SUB, unit, vals, note):
            dump_csv(os.path.join(outdir, name + '.csv'), vals, key, unit)
            made += 1
        else:
            print('  skipped %s (no data for %s)' % (name, key))
    for name, title, xk, xl, yk, yl, note in PARETOS:
        xv = pick(rows, xk)
        yv = pick(rows, yk)
        pairs = dict((k, (xv[k], yv[k])) for k in xv if k in yv)
        if pareto_chart(os.path.join(outdir, name + '.svg'), title, xl, yl,
                        pairs, note):
            f = open(os.path.join(outdir, name + '.csv'), 'w')
            try:
                w = csv.writer(f)
                w.writerow(['scenario', 'algorithm', xk, yk])
                for tag in TAGS:
                    for a in ALGOS:
                        if (tag, a) in pairs:
                            x, y = pairs[(tag, a)]
                            w.writerow([tag, LABEL[a], '%.6f' % x, '%.6f' % y])
            finally:
                f.close()
            made += 1
    print('wrote %d charts (+ matching CSVs) to %s' % (made, outdir))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
