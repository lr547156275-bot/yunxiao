#!/usr/bin/env python3
from pathlib import Path

from problem1_common import mean_ci95, queue_rows, read_fct, read_pfc, read_ports, run_metrics, sorted_fct_rows, write_csv


BASE = Path(__file__).resolve().parents[1]
RESULTS = BASE / 'results'
METRICS = (
    'stage_completion_time_ms',
    'mean_fct_ms',
    'p95_fct_ms',
    'max_fct_ms',
    'mean_normalized_fct',
    'max_normalized_fct',
    'total_spine_throughput_gbps',
    'max_queue_bytes',
    'p99_queue_bytes',
    'pause_event_count',
    'cumulative_pause_time_ns',
)


def main():
    per_run = []
    flow_rows = []
    all_queue = []
    all_pfc = []
    for permutation in range(5):
        directory = RESULTS / ('permutation_%d' % permutation)
        for scheme in ('collision', 'oracle'):
            fct = read_fct(directory / ('fct_%s.txt' % scheme), directory / ('path_%s.log' % scheme), scheme)
            ports = read_ports(directory / ('port_%s.txt' % scheme))
            pfc = read_pfc(directory / ('pfc_%s.txt' % scheme), scheme, permutation)
            metrics = run_metrics(fct, ports, pfc)
            row = {'permutation': permutation, 'scheme': scheme}
            row.update(metrics)
            per_run.append(row)
            all_pfc.append(pfc)
            all_queue.extend(queue_rows(ports, metrics['stage_start_ns'], metrics['stage_end_ns'], scheme, permutation))
            for fct_row in sorted_fct_rows(fct):
                flow_rows.append({
                    'permutation': permutation,
                    'scheme': scheme,
                    'sorted_index': fct_row['sorted_index'],
                    'flow_id': fct_row['flow_id'],
                    'fct_ms': fct_row['fct_ms'],
                    'standalone_fct_ms': fct_row['standalone_fct_ms'],
                    'normalized_fct': fct_row['normalized_fct'],
                })

    summary = []
    for scheme in ('collision', 'oracle'):
        scheme_rows = [row for row in per_run if row['scheme'] == scheme]
        for metric in METRICS:
            mean, stddev, half_width, lower, upper = mean_ci95(row[metric] for row in scheme_rows)
            summary.append({
                'scheme': scheme,
                'metric': metric,
                'n': len(scheme_rows),
                'mean': mean,
                'stddev': stddev,
                'ci95_half_width': half_width,
                'ci95_lower': lower,
                'ci95_upper': upper,
            })

    ratios = []
    for permutation in range(5):
        collision = next(row for row in per_run if row['permutation'] == permutation and row['scheme'] == 'collision')
        oracle = next(row for row in per_run if row['permutation'] == permutation and row['scheme'] == 'oracle')
        ratios.append(collision['stage_completion_time_ms'] / oracle['stage_completion_time_ms'])
    mean, stddev, half_width, lower, upper = mean_ci95(ratios)
    summary.append({
        'scheme': 'collision_over_oracle',
        'metric': 'stage_completion_ratio',
        'n': len(ratios),
        'mean': mean,
        'stddev': stddev,
        'ci95_half_width': half_width,
        'ci95_lower': lower,
        'ci95_upper': upper,
    })

    write_csv(RESULTS / 'permutation_summary.csv', summary)
    write_csv(RESULTS / 'permutation_flow_fct.csv', flow_rows)
    write_csv(RESULTS / 'permutation_queue.csv', all_queue)
    write_csv(RESULTS / 'permutation_pfc.csv', all_pfc)

    lines = [
        '# RWMCR Problem 1 permutation summary', '',
        '| P | Collision stage (ms) | Oracle stage (ms) | Ratio |',
        '|---:|---:|---:|---:|',
    ]
    for permutation, ratio in enumerate(ratios):
        collision = next(row for row in per_run if row['permutation'] == permutation and row['scheme'] == 'collision')
        oracle = next(row for row in per_run if row['permutation'] == permutation and row['scheme'] == 'oracle')
        lines.append('| %d | %.3f | %.3f | %.4f |' % (permutation, collision['stage_completion_time_ms'], oracle['stage_completion_time_ms'], ratio))
    lines.extend([
        '',
        'Stage ratio mean: **%.4f**, 95%% CI **[%.4f, %.4f]** (theory: 2.5).' % (mean, lower, upper),
        '',
        'The reported aggregate spine throughput is total monitored Leaf→Spine bytes divided by stage completion time.',
        '',
    ])
    (RESULTS / 'permutation_summary.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
