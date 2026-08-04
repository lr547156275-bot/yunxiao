#!/usr/bin/env python3
from pathlib import Path


BASE = Path(__file__).resolve().parent
PERMUTATIONS = BASE / 'permutations'
RESULTS = BASE / 'results'

COLLISION = [
    ((0, 1, 2, 3, 4), (5, 6), (7,), ()),
    ((1, 2, 3, 4, 5), (6, 7), (0,), ()),
    ((2, 3, 4, 5, 6), (7, 0), (1,), ()),
    ((3, 4, 5, 6, 7), (0, 1), (2,), ()),
    ((4, 5, 6, 7, 0), (1, 2), (3,), ()),
]
ORACLE = [
    ((0, 1), (2, 3), (4, 5), (6, 7)),
    ((1, 2), (3, 4), (5, 6), (7, 0)),
    ((2, 3), (4, 5), (6, 7), (0, 1)),
    ((3, 4), (5, 6), (7, 0), (1, 2)),
    ((4, 5), (6, 7), (0, 1), (2, 3)),
]


def path_text(groups):
    assignments = {}
    for spine, flows in zip((18, 19, 20, 21), groups):
        for flow in flows:
            assignments[flow] = spine
    if set(assignments) != set(range(8)):
        raise ValueError('each permutation must assign F0-F7 exactly once')
    return ''.join('%d %d\n' % (flow, assignments[flow]) for flow in range(8))


def config_text(base_config, permutation, scheme):
    result_dir = 'experiment/rwmcr_problem1/results/permutation_%d' % permutation
    replacements = {
        'FIXED_PATH_FILE': 'experiment/rwmcr_problem1/permutations/permutation_%d/path_%s.txt' % (permutation, scheme),
        'FIXED_PATH_OUTPUT_FILE': '%s/path_%s.log' % (result_dir, scheme),
        'PORT_MONITOR_OUTPUT_FILE': '%s/port_%s.txt' % (result_dir, scheme),
        'TRACE_OUTPUT_FILE': '%s/trace_%s.tr' % (result_dir, scheme),
        'FCT_OUTPUT_FILE': '%s/fct_%s.txt' % (result_dir, scheme),
        'PFC_OUTPUT_FILE': '%s/pfc_%s.txt' % (result_dir, scheme),
        'QLEN_MON_FILE': '%s/legacy_qlen_%s.txt' % (result_dir, scheme),
    }
    output = []
    for line in base_config.splitlines():
        fields = line.split(None, 1)
        if fields and fields[0] in replacements:
            output.append('%s %s' % (fields[0], replacements[fields[0]]))
        else:
            output.append(line)
    return '\n'.join(output) + '\n'


def main():
    base_configs = {
        'collision': (BASE / 'config_collision.txt').read_text(),
        'oracle': (BASE / 'config_oracle.txt').read_text(),
    }
    for permutation in range(5):
        directory = PERMUTATIONS / ('permutation_%d' % permutation)
        directory.mkdir(parents=True, exist_ok=True)
        (RESULTS / ('permutation_%d' % permutation)).mkdir(parents=True, exist_ok=True)
        for scheme, groups in (('collision', COLLISION[permutation]), ('oracle', ORACLE[permutation])):
            (directory / ('path_%s.txt' % scheme)).write_text(path_text(groups))
            (directory / ('config_%s.txt' % scheme)).write_text(config_text(base_configs[scheme], permutation, scheme))
    print('generated 5 paired permutations under %s' % PERMUTATIONS)


if __name__ == '__main__':
    main()
