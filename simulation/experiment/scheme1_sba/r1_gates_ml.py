# -*- coding: utf-8 -*-
# R-1a/b/c, MULTI-LINK entry point.
#
# Groups the trace by (link_id, node_id, if_index) FIRST, then runs the frozen
# per-link R-1a/b/c logic from r1_gates_v4.py on each bottleneck separately.
# Two independent 10 Gbps links are never merged into one service curve.
#
# The per-link gate FORMULAS are imported from r1_gates_v4.py (frozen
# 924e1594...) and are not reimplemented or altered here.  This file adds only:
#   * grouping by link identity,
#   * the (link_id,node_id,if_index,packet_uid) pairing key -- achieved by
#     analysing each link's rows in isolation, so identical packet_uids on two
#     links cannot cross-pair,
#   * expected-vs-observed link set reconciliation,
#   * the overall verdict = AND over all expected links.
#
# Usage: python3 r1_gates_ml.py <tx_csv> <C_bps> <core_lo> <core_hi>
#                              <expected_links> [label]
#   expected_links: comma list of link_id:node_id:if_index, e.g. "0:84:1,1:83:1"
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r1_gates_v4 as V4          # frozen per-link formulas


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def norm(rows):
    """Map the ML column names onto what the frozen v4 analyser expects."""
    out = []
    for r in rows:
        out.append({
            'time_ns': r['time_ns'],
            'event': r['event'],
            'node_id': r.get('node_id', ''),
            'ifindex': r.get('if_index', r.get('ifindex', '')),
            'link_id': r.get('link_id', ''),
            'packet_uid': r['packet_uid'],
            'size_bytes': r.get('packet_bytes', r.get('size_bytes', '')),
        })
    return out


def main():
    if len(sys.argv) < 6:
        print('usage: r1_gates_ml.py <tx_csv> <C_bps> <core_lo> <core_hi> '
              '<expected_links> [label]')
        return 2
    tx = sys.argv[1]
    P = tx if os.path.isabs(tx) else os.path.join(HERE, tx)
    C = float(sys.argv[2])
    lo = int(sys.argv[3])
    hi = int(sys.argv[4])
    expected = [tuple(x.split(':')) for x in sys.argv[5].split(',') if x]
    label = sys.argv[6] if len(sys.argv) > 6 else tx

    if not os.path.exists(P):
        print('FATAL: %s missing' % P)
        return 2
    rows = norm(load(P))
    if not rows:
        print('FATAL: trace empty -- refusing to report PASS on no data')
        return 2

    print('=' * 78)
    print('R-1a/b/c MULTI-LINK -- %s' % label)
    print('=' * 78)
    print('  per-link formulas from frozen r1_gates_v4.py')
    print('  C            : %.4f Gbps per link' % (C / 1e9))
    print('  core         : [%d, %d] ns' % (lo, hi))
    print('  time epsilon : %d ns (one simulator tick)' % V4.TICK_NS)
    print('')

    # ---- group by link identity ------------------------------------------
    groups = {}
    for r in rows:
        k = (r['link_id'], r['node_id'], r['ifindex'])
        groups.setdefault(k, []).append(r)

    obs = sorted(groups.keys())
    exp = sorted(expected)
    print('  expected links : %s' % [':'.join(x) for x in exp])
    print('  observed links : %s' % [':'.join(x) for x in obs])
    missing = [x for x in exp if x not in obs]
    extra = [x for x in obs if x not in exp]
    set_ok = (not missing) and (not extra)
    print('  set match      : %s%s%s'
          % ('YES' if set_ok else 'NO',
             '' if not missing else '  MISSING=%s' % [':'.join(x) for x in missing],
             '' if not extra else '  UNEXPECTED=%s' % [':'.join(x) for x in extra]))
    print('')

    # cross-link uid overlap is legitimate and must not cross-pair
    uid_sets = dict((k, set(r['packet_uid'] for r in v))
                    for k, v in groups.items())
    if len(obs) >= 2:
        shared = set.intersection(*[uid_sets[k] for k in obs])
        print('  packet_uids seen on >1 link : %d (legitimate; pairing is '
              'per-link)' % len(shared))
        print('')

    # ---- per-link evaluation --------------------------------------------
    per_link = {}
    for k in obs:
        rs = groups[k]
        flows = len(set(r['packet_uid'] for r in rs))
        print('-' * 78)
        print('LINK %s  (node=%s if=%s)  rows=%d distinct_uid=%d'
              % (k[0], k[1], k[2], len(rs), flows))
        print('-' * 78)
        g, o = V4.analyse(rs, C, lo, hi, '%s link %s' % (label, k[0]),
                          verbose=True)
        nfail = V4.emit('%s -- LINK %s' % (label, k[0]), C, g, o)
        per_link[k] = (len(g) - nfail, len(g), nfail)
        print('')

    # ---- overall verdict ------------------------------------------------
    print('=' * 78)
    print('MULTI-LINK VERDICT')
    print('=' * 78)
    all_pass = set_ok and len(obs) > 0
    for k in obs:
        p, t, f = per_link[k]
        tag = 'expected' if k in exp else 'UNEXPECTED'
        print('  link %s (node=%s if=%s, %s): %d/%d gates'
              % (k[0], k[1], k[2], tag, p, t))
        if f:
            all_pass = False
    for k in missing:
        print('  link %s: NO DATA -- expected but never observed'
              % ':'.join(k))
        all_pass = False
    print('')
    print('  expected links covered : %d/%d' % (len(exp) - len(missing), len(exp)))
    print('  OVERALL R-1a/b/c       : %s' % ('PASS' if all_pass else 'FAIL'))
    if not all_pass:
        print('')
        print('  A single link passing does NOT represent the scenario.')
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
