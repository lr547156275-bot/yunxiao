#!/usr/bin/env python3
import csv
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from problem1_common import SPINES, mean_ci95, read_fct, read_paths, read_ports


BASE = Path(__file__).resolve().parents[1]
RESULTS = BASE / 'results'
COLORS = {18: '#d95f02', 19: '#1b9e77', 20: '#7570b3', 21: '#e7298a'}
SCHEME_COLORS = {'collision': '#e67e22', 'oracle': '#3498db'}
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def font(size, bold=False):
    path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


TITLE = font(31, True)
PANEL_TITLE = font(25, True)
LABEL = font(18)
TICK = font(15)
LEGEND = font(16)


def text_center(draw, xy, text, selected_font, fill='#222222'):
    width, height = draw.textsize(text, font=selected_font)
    draw.text((xy[0] - width / 2, xy[1] - height / 2), text, font=selected_font, fill=fill)


def panel_frame(draw, box, title):
    draw.rectangle(box, fill='white', outline='#c9d1d9', width=2)
    draw.text((box[0] + 22, box[1] + 16), title, font=PANEL_TITLE, fill='#222222')


def throughput_panel(draw, box, scheme, letter):
    panel_frame(draw, box, '(%s) %s: Leaf16 to Spine throughput' % (letter, scheme.capitalize()))
    fct = read_fct(RESULTS / ('fct_%s.txt' % scheme), RESULTS / ('path_%s.log' % scheme), scheme)
    rows = read_ports(RESULTS / ('ports_%s.log' % scheme))
    start_ns = min(row['start_time_ns'] for row in fct)
    end_ns = max(row['start_time_ns'] + row['fct_ns'] for row in fct)
    duration_ms = (end_ns - start_ns) / 1e6
    left, right = box[0] + 78, box[2] - 25
    top, bottom = box[1] + 90, box[3] - 58
    width, height = right - left, bottom - top
    for value in range(0, 101, 25):
        y = bottom - height * value / 105.0
        draw.line((left, y, right, y), fill='#e6e9ed', width=1)
        text_center(draw, (left - 27, y), str(value), TICK)
    for index in range(6):
        value = duration_ms * index / 5.0
        x = left + width * index / 5.0
        draw.line((x, top, x, bottom), fill='#eef0f2', width=1)
        text_center(draw, (x, bottom + 22), '%.0f' % value, TICK)
    draw.line((left, top, left, bottom), fill='#555555', width=2)
    draw.line((left, bottom, right, bottom), fill='#555555', width=2)
    text_center(draw, ((left + right) / 2, box[3] - 18), 'Time from flow start (ms)', LABEL)
    draw.text((box[0] + 7, top - 28), 'Gbps', font=LABEL, fill='#333333')

    bin_ns = 250000
    bins = defaultdict(lambda: defaultdict(int))
    for row in rows:
        relative = row['time_ns'] - start_ns
        if 0 <= relative <= end_ns - start_ns:
            bins[row['peer_id']][relative // bin_ns] += row['tx_delta_bytes']
    maximum_bin = int((end_ns - start_ns) // bin_ns)
    for spine in SPINES:
        points = []
        for bin_index in range(maximum_bin + 1):
            time_ms = (bin_index + 0.5) * bin_ns / 1e6
            throughput = bins[spine][bin_index] * 8.0 / bin_ns
            x = left + width * min(time_ms / duration_ms, 1.0)
            y = bottom - height * min(throughput / 105.0, 1.0)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=COLORS[spine], width=3)
    legend_x = right - 390
    for index, spine in enumerate(SPINES):
        x = legend_x + index * 98
        draw.line((x, box[1] + 65, x + 25, box[1] + 65), fill=COLORS[spine], width=4)
        draw.text((x + 31, box[1] + 54), 'S%d' % spine, font=LEGEND, fill='#333333')


def normalized_fct_panel(draw, box):
    panel_frame(draw, box, '(c) Sorted normalized FCT across 5 permutations')
    grouped = defaultdict(list)
    with (RESULTS / 'permutation_flow_fct.csv').open(newline='') as handle:
        for row in csv.DictReader(handle):
            grouped[(row['scheme'], int(row['sorted_index']))].append(float(row['normalized_fct']))
    stats = {}
    for key, values in grouped.items():
        stats[key] = mean_ci95(values)
    ymax = max(stats[key][4] for key in stats) * 1.08
    left, right = box[0] + 82, box[2] - 30
    top, bottom = box[1] + 90, box[3] - 58
    width, height = right - left, bottom - top
    for index in range(6):
        value = ymax * index / 5.0
        y = bottom - height * index / 5.0
        draw.line((left, y, right, y), fill='#e6e9ed', width=1)
        text_center(draw, (left - 31, y), '%.1f' % value, TICK)
    for sorted_index in range(1, 9):
        x = left + width * (sorted_index - 1) / 7.0
        draw.line((x, top, x, bottom), fill='#f0f1f3', width=1)
        text_center(draw, (x, bottom + 22), str(sorted_index), TICK)
    draw.line((left, top, left, bottom), fill='#555555', width=2)
    draw.line((left, bottom, right, bottom), fill='#555555', width=2)
    text_center(draw, ((left + right) / 2, box[3] - 18), 'Sorted flow index', LABEL)
    draw.text((box[0] + 5, top - 29), 'Normalized FCT', font=LABEL, fill='#333333')
    for scheme in ('collision', 'oracle'):
        points = []
        color = SCHEME_COLORS[scheme]
        for sorted_index in range(1, 9):
            mean, _, half_width, lower, upper = stats[(scheme, sorted_index)]
            x = left + width * (sorted_index - 1) / 7.0
            y = bottom - height * mean / ymax
            y_low = bottom - height * lower / ymax
            y_high = bottom - height * upper / ymax
            draw.line((x, y_low, x, y_high), fill=color, width=2)
            draw.line((x - 6, y_low, x + 6, y_low), fill=color, width=2)
            draw.line((x - 6, y_high, x + 6, y_high), fill=color, width=2)
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)
            points.append((x, y))
        draw.line(points, fill=color, width=4)
    legend_x = right - 255
    for index, scheme in enumerate(('collision', 'oracle')):
        x = legend_x + index * 130
        y = box[1] + 65
        draw.line((x, y, x + 30, y), fill=SCHEME_COLORS[scheme], width=4)
        draw.text((x + 38, y - 10), scheme.capitalize(), font=LEGEND, fill='#333333')


def make_final():
    image = Image.new('RGB', (2400, 820), '#f5f7fa')
    draw = ImageDraw.Draw(image)
    throughput_panel(draw, (20, 20, 790, 800), 'collision', 'a')
    throughput_panel(draw, (815, 20, 1585, 800), 'oracle', 'b')
    normalized_fct_panel(draw, (1610, 20, 2380, 800))
    image.save(RESULTS / 'problem1_final.png', dpi=(300, 300))
    image.save(RESULTS / 'problem1_final.pdf', 'PDF', resolution=300.0)


def bar_chart(draw, box, title, categories, collision, oracle, ylabel):
    panel_frame(draw, box, title)
    left, right = box[0] + 80, box[2] - 30
    top, bottom = box[1] + 70, box[3] - 60
    width, height = right - left, bottom - top
    ymax = max(collision + oracle + [1]) * 1.15
    for index in range(5):
        value = ymax * index / 4.0
        y = bottom - height * index / 4.0
        draw.line((left, y, right, y), fill='#e6e9ed', width=1)
        text_center(draw, (left - 32, y), '%.2g' % value, TICK)
    group_width = width / len(categories)
    for index, category in enumerate(categories):
        center = left + group_width * (index + 0.5)
        for offset, value, color in ((-18, collision[index], SCHEME_COLORS['collision']), (18, oracle[index], SCHEME_COLORS['oracle'])):
            bar_width = 30
            bar_height = height * value / ymax
            draw.rectangle((center + offset - bar_width / 2, bottom - bar_height, center + offset + bar_width / 2, bottom), fill=color)
        text_center(draw, (center, bottom + 22), str(category), TICK)
    draw.text((box[0] + 8, top - 30), ylabel, font=LABEL, fill='#333333')
    legend_x = right - 210
    draw.rectangle((legend_x, box[1] + 47, legend_x + 18, box[1] + 62), fill=SCHEME_COLORS['collision'])
    draw.text((legend_x + 25, box[1] + 43), 'Collision', font=LEGEND, fill='#333333')
    draw.rectangle((legend_x + 112, box[1] + 47, legend_x + 130, box[1] + 62), fill=SCHEME_COLORS['oracle'])
    draw.text((legend_x + 137, box[1] + 43), 'Oracle', font=LEGEND, fill='#333333')


def make_diagnostics():
    image = Image.new('RGB', (1800, 1200), '#f5f7fa')
    draw = ImageDraw.Draw(image)
    path_counts = {}
    port_bytes = {}
    for scheme in ('collision', 'oracle'):
        path_counts[scheme] = Counter(row['forced_spine'] for row in read_paths(RESULTS / ('path_%s.log' % scheme)))
        totals = Counter()
        for row in read_ports(RESULTS / ('ports_%s.log' % scheme)):
            totals[row['peer_id']] += row['tx_delta_bytes']
        port_bytes[scheme] = totals
    bar_chart(draw, (20, 20, 880, 580), 'Configured path count', list(SPINES), [path_counts['collision'][s] for s in SPINES], [path_counts['oracle'][s] for s in SPINES], 'Flows')
    bar_chart(draw, (920, 20, 1780, 580), 'Measured transmitted bytes', list(SPINES), [port_bytes['collision'][s] / 1e9 for s in SPINES], [port_bytes['oracle'][s] / 1e9 for s in SPINES], 'GB')
    queue = {}
    with (RESULTS / 'queue_summary.csv').open(newline='') as handle:
        for row in csv.DictReader(handle):
            if row['peer_id'] == 'all':
                queue[row['scheme']] = row
    bar_chart(draw, (20, 620, 880, 1180), 'Queue during active stage', ['Max', 'P99'], [float(queue['collision']['max_queue_bytes']), float(queue['collision']['p99_queue_bytes'])], [float(queue['oracle']['max_queue_bytes']), float(queue['oracle']['p99_queue_bytes'])], 'Bytes')
    pfc = {}
    with (RESULTS / 'pfc_summary.csv').open(newline='') as handle:
        for row in csv.DictReader(handle):
            pfc[row['scheme']] = row
    bar_chart(draw, (920, 620, 1780, 1180), 'PFC events', ['Pause', 'Resume'], [float(pfc['collision']['pause_event_count']), float(pfc['collision']['resume_event_count'])], [float(pfc['oracle']['pause_event_count']), float(pfc['oracle']['resume_event_count'])], 'Events')
    image.save(RESULTS / 'problem1_diagnostics.png', dpi=(200, 200))


if __name__ == '__main__':
    make_final()
    make_diagnostics()
    print(RESULTS / 'problem1_final.png')
    print(RESULTS / 'problem1_final.pdf')
    print(RESULTS / 'problem1_diagnostics.png')
