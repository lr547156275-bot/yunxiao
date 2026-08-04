#!/usr/bin/env python3
from pathlib import Path

from problem1_common import queue_rows, read_fct, read_pfc, read_ports, run_metrics, sorted_fct_rows, write_csv


BASE = Path(__file__).resolve().parents[1]
RESULTS = BASE / 'results'


def main():
    all_fct = []
    all_queue = []
    all_pfc = []
    summaries = []
    for scheme in ('collision', 'oracle'):
        fct = read_fct(RESULTS / ('fct_%s.txt' % scheme), RESULTS / ('path_%s.log' % scheme), scheme)
        ports = read_ports(RESULTS / ('ports_%s.log' % scheme))
        pfc = read_pfc(RESULTS / ('pfc_%s.txt' % scheme), scheme)
        metrics = run_metrics(fct, ports, pfc)
        sorted_rows = sorted_fct_rows(fct)
        all_fct.extend({key: row[key] for key in ('scheme', 'sorted_index', 'flow_id', 'fct_ms', 'standalone_fct_ms', 'normalized_fct')} for row in sorted_rows)
        all_queue.extend(queue_rows(ports, metrics['stage_start_ns'], metrics['stage_end_ns'], scheme))
        all_pfc.append(pfc)
        summary = {'scheme': scheme}
        summary.update({key: value for key, value in metrics.items() if not key.endswith('_ns') or key == 'cumulative_pause_time_ns'})
        summaries.append(summary)

    write_csv(RESULTS / 'flow_fct.csv', all_fct)
    write_csv(RESULTS / 'queue_summary.csv', all_queue)
    write_csv(RESULTS / 'pfc_summary.csv', all_pfc)
    write_csv(RESULTS / 'single_run_summary.csv', summaries)

    by_scheme = {row['scheme']: row for row in summaries}
    ratio = by_scheme['collision']['stage_completion_time_ms'] / by_scheme['oracle']['stage_completion_time_ms']
    lines = [
        '# RWMCR Problem 1 single-run summary', '',
        '| Scheme | Stage (ms) | Mean FCT (ms) | P95 FCT (ms) | Max FCT (ms) | Mean normalized FCT | Max queue (B) | P99 queue (B) | Pause | Resume | Pause time (ns) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    queue_all = {row['scheme']: row for row in all_queue if row['peer_id'] == 'all'}
    for row in summaries:
        queue = queue_all[row['scheme']]
        pfc = next(item for item in all_pfc if item['scheme'] == row['scheme'])
        combined = dict(row)
        combined.update(queue)
        combined.update(pfc)
        lines.append('| {scheme} | {stage_completion_time_ms:.3f} | {mean_fct_ms:.3f} | {p95_fct_ms:.3f} | {max_fct_ms:.3f} | {mean_normalized_fct:.3f} | {max_queue_bytes:.0f} | {p99_queue_bytes:.1f} | {pause_event_count} | {resume_event_count} | {cumulative_pause_time_ns} |'.format(**combined))
    lines.extend(['', 'Collision/oracle stage ratio: **%.4f**' % ratio, ''])
    (RESULTS / 'single_run_summary.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
