#!/usr/bin/env python3
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


SPINES = (18, 19, 20, 21)
T_CRIT_95_DF4 = 2.7764451051977987


def percentile(values, probability):
    values = sorted(values)
    if not values:
        return 0.0
    position = (len(values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(values[lower])
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def mean_ci95(values):
    values = list(values)
    mean = statistics.mean(values) if values else 0.0
    stddev = statistics.stdev(values) if len(values) > 1 else 0.0
    if len(values) == 5:
        critical = T_CRIT_95_DF4
    elif len(values) > 1:
        critical = 1.96
    else:
        critical = 0.0
    half_width = critical * stddev / math.sqrt(len(values)) if values else 0.0
    return mean, stddev, half_width, mean - half_width, mean + half_width


def ip_to_node(text):
    return (int(text, 16) >> 8) & 0xffff


def read_paths(path):
    rows = []
    with Path(path).open(newline='') as handle:
        reader = csv.DictReader(handle, delimiter=' ', skipinitialspace=True)
        for row in reader:
            rows.append({
                'flow_index': int(row['flow_index']),
                'src': int(row['src']),
                'dst': int(row['dst']),
                'sport': int(row['sport']),
                'dport': int(row['dport']),
                'src_leaf': int(row['src_leaf']),
                'forced_spine': int(row['forced_spine']),
                'out_if': int(row['out_if']),
                'start_time_s': float(row['start_time']),
            })
    return rows


def read_fct(fct_path, path_path, scheme):
    paths = read_paths(path_path)
    flow_by_key = {
        (row['src'], row['dst'], row['sport'], row['dport']): row
        for row in paths
    }
    rows = []
    with Path(fct_path).open() as handle:
        for line in handle:
            fields = line.split()
            if not fields:
                continue
            if len(fields) != 8:
                raise ValueError('unexpected FCT format in %s' % fct_path)
            src = ip_to_node(fields[0])
            dst = ip_to_node(fields[1])
            sport = int(fields[2])
            dport = int(fields[3])
            key = (src, dst, sport, dport)
            if key not in flow_by_key:
                raise ValueError('FCT tuple missing from path log: %r' % (key,))
            path_row = flow_by_key[key]
            fct_ns = int(fields[6])
            standalone_ns = int(fields[7])
            rows.append({
                'scheme': scheme,
                'flow_index': path_row['flow_index'],
                'flow_id': 'F%d' % path_row['flow_index'],
                'src': src,
                'dst': dst,
                'sport': sport,
                'dport': dport,
                'size_bytes': int(fields[4]),
                'start_time_ns': int(fields[5]),
                'fct_ns': fct_ns,
                'standalone_fct_ns': standalone_ns,
                'fct_ms': fct_ns / 1e6,
                'standalone_fct_ms': standalone_ns / 1e6,
                'normalized_fct': fct_ns / float(standalone_ns),
                'forced_spine': path_row['forced_spine'],
            })
    if len(rows) != 8:
        raise ValueError('%s contains %d FCT rows, expected 8' % (fct_path, len(rows)))
    return rows


def sorted_fct_rows(rows):
    result = []
    for index, row in enumerate(sorted(rows, key=lambda item: item['normalized_fct']), 1):
        copy = dict(row)
        copy['sorted_index'] = index
        result.append(copy)
    return result


def read_ports(path):
    rows = []
    with Path(path).open(newline='') as handle:
        reader = csv.DictReader(handle, delimiter=' ', skipinitialspace=True)
        required = {'time_ns', 'node_id', 'peer_id', 'if_index', 'tx_delta_bytes', 'throughput_bps', 'queue_bytes'}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError('unexpected port monitor format in %s' % path)
        for row in reader:
            rows.append({key: int(row[key]) for key in required})
    return rows


def queue_rows(port_rows, start_ns, end_ns, scheme, permutation=None):
    selected = [row for row in port_rows if start_ns <= row['time_ns'] <= end_ns]
    result = []
    groups = [('all', selected)]
    groups.extend((str(spine), [row for row in selected if row['peer_id'] == spine]) for spine in SPINES)
    for peer, rows in groups:
        values = [row['queue_bytes'] for row in rows]
        output = {
            'scheme': scheme,
            'peer_id': peer,
            'sample_count': len(values),
            'max_queue_bytes': max(values) if values else 0,
            'p99_queue_bytes': percentile(values, 0.99),
            'mean_queue_bytes': statistics.mean(values) if values else 0.0,
        }
        if permutation is not None:
            output['permutation'] = permutation
        result.append(output)
    return result


def read_pfc(path, scheme, permutation=None):
    events = []
    path = Path(path)
    if path.exists() and path.stat().st_size:
        with path.open(newline='') as handle:
            reader = csv.DictReader(handle, delimiter=' ', skipinitialspace=True)
            required = {'time_ns', 'node_id', 'if_index', 'q_index', 'event_type'}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError('unexpected PFC format in %s' % path)
            for row in reader:
                events.append({key: int(row[key]) for key in required})
    pause_count = sum(row['event_type'] == 1 for row in events)
    resume_count = sum(row['event_type'] == 0 for row in events)
    active = {}
    cumulative = 0
    paired = 0
    for row in sorted(events, key=lambda item: item['time_ns']):
        key = (row['node_id'], row['if_index'], row['q_index'])
        if row['event_type'] == 1:
            if key not in active:
                active[key] = row['time_ns']
        elif key in active:
            cumulative += row['time_ns'] - active.pop(key)
            paired += 1
    output = {
        'scheme': scheme,
        'pause_event_count': pause_count,
        'resume_event_count': resume_count,
        'paired_pause_count': paired,
        'unmatched_pause_count': len(active),
        'cumulative_pause_time_ns': cumulative,
    }
    if permutation is not None:
        output['permutation'] = permutation
    return output


def run_metrics(fct_rows, port_rows, pfc_row):
    start_ns = min(row['start_time_ns'] for row in fct_rows)
    end_ns = max(row['start_time_ns'] + row['fct_ns'] for row in fct_rows)
    duration_ns = end_ns - start_ns
    active_ports = [row for row in port_rows if start_ns <= row['time_ns'] <= end_ns]
    total_bytes = sum(row['tx_delta_bytes'] for row in active_ports)
    queue_values = [row['queue_bytes'] for row in active_ports]
    fcts = [row['fct_ms'] for row in fct_rows]
    normalized = [row['normalized_fct'] for row in fct_rows]
    return {
        'stage_completion_time_ms': duration_ns / 1e6,
        'mean_fct_ms': statistics.mean(fcts),
        'p95_fct_ms': percentile(fcts, 0.95),
        'max_fct_ms': max(fcts),
        'mean_normalized_fct': statistics.mean(normalized),
        'max_normalized_fct': max(normalized),
        'total_spine_throughput_gbps': total_bytes * 8.0 / duration_ns if duration_ns else 0.0,
        'max_queue_bytes': max(queue_values) if queue_values else 0,
        'p99_queue_bytes': percentile(queue_values, 0.99),
        'pause_event_count': pfc_row['pause_event_count'],
        'resume_event_count': pfc_row['resume_event_count'],
        'cumulative_pause_time_ns': pfc_row['cumulative_pause_time_ns'],
        'stage_start_ns': start_ns,
        'stage_end_ns': end_ns,
    }


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
