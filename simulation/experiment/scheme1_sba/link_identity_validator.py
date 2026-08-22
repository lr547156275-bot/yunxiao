# -*- coding: utf-8 -*-
# Independent fail-fast validator for the FROZEN link-identity semantics.
#
# FROZEN SEMANTICS (do not change):
#   1. link_id is a CELL-LOCAL ordinal.  It is NEVER a join key across
#      algorithms or across cells.
#   2. The authoritative physical identity is
#          physical_link_key = (node_id, if_index)
#   3. Every cell manifest records
#          local_link_id -> node_id -> if_index -> physical_link_key
#   4. All CBAP/DCQCN per-link comparison, plotting and aggregation aligns on
#      physical_link_key.  Raw link_id is provenance only.
#   5. This validator enforces the four checks below.
#   6. S6 links are always named 84:1 and 83:1 -- never
#      "CBAP link 0 vs DCQCN link 0".
#
# Concrete motivation: in ckpt3 S6 the same physical link got OPPOSITE ordinals,
# because CBAP takes ids from the link file while DCQCN assigns a stable ordinal
# over the sorted (node,if) set:
#      CBAP :  84:1 -> 0 ,  83:1 -> 1     (id_source=link_file)
#      DCQCN:  84:1 -> 1 ,  83:1 -> 0     (id_source=stable_ordinal)
# Joining on link_id would silently compare 84:1 against 83:1.
#
# Usage:
#   python3 link_identity_validator.py <tx_csv> <expected_keys> [label]
#     expected_keys: comma list of node:if, e.g. "84:1,83:1"
import csv
import os
import sys

FAILS = []
OUT = []


def fail(msg):
    FAILS.append(msg)


def rep(k, v):
    OUT.append((k, v))


def main():
    if len(sys.argv) < 3:
        print('usage: link_identity_validator.py <tx_csv> <node:if,...> [label]')
        return 2
    p = sys.argv[1]
    if not os.path.isabs(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
    expected = set()
    for tok in sys.argv[2].split(','):
        tok = tok.strip()
        if tok:
            a, b = tok.split(':')
            expected.add((a, b))
    label = sys.argv[3] if len(sys.argv) > 3 else p

    if not os.path.exists(p):
        print('FATAL: %s missing' % p)
        return 2
    with open(p) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print('FATAL: trace empty -- cannot validate identity on no data')
        return 2

    print('=' * 74)
    print('LINK IDENTITY VALIDATOR -- %s' % label)
    print('=' * 74)
    print('  frozen: physical_link_key = (node_id, if_index)')
    print('  frozen: link_id is a cell-local ordinal, NEVER a join key')
    print('')

    # mapping local_link_id -> physical_link_key, and event counts
    id2key = {}
    key2id = {}
    counts = {}
    for r in rows:
        lid = r.get('link_id', '')
        node = r.get('node_id', '')
        iff = r.get('if_index', r.get('ifindex', ''))
        if node == '' or iff == '':
            continue
        key = (node, iff)
        id2key.setdefault(lid, set()).add(key)
        key2id.setdefault(key, set()).add(lid)
        counts[key] = counts.get(key, 0) + 1

    print('  local_link_id -> node_id -> if_index -> physical_link_key')
    for lid in sorted(id2key):
        for key in sorted(id2key[lid]):
            print('    %-3s -> %-5s -> %-3s -> %s:%s   events=%d'
                  % (lid, key[0], key[1], key[0], key[1], counts[key]))
    print('')

    observed = set(counts.keys())

    # CHECK 1: expected == observed, on physical keys
    missing = expected - observed
    extra = observed - expected
    if missing:
        fail('expected physical_link_key missing from trace: %s'
             % sorted('%s:%s' % k for k in missing))
    if extra:
        fail('unexpected physical_link_key in trace: %s'
             % sorted('%s:%s' % k for k in extra))
    rep('expected keys', sorted('%s:%s' % k for k in expected))
    rep('observed keys', sorted('%s:%s' % k for k in observed))
    rep('set match', 'YES' if not missing and not extra else 'NO')

    # CHECK 2: each local_link_id maps to exactly one physical key (and vice
    # versa, so the mapping is a bijection within this cell)
    for lid, keys in id2key.items():
        if len(keys) != 1:
            fail('local_link_id %s maps to %d physical keys: %s'
                 % (lid, len(keys), sorted('%s:%s' % k for k in keys)))
    for key, lids in key2id.items():
        if len(lids) != 1:
            fail('physical key %s:%s carries %d local_link_ids: %s'
                 % (key[0], key[1], len(lids), sorted(lids)))
    rep('id <-> key bijection', 'YES' if not FAILS else 'NO')

    # CHECK 3: every expected link has a non-zero event count
    for key in sorted(expected):
        n = counts.get(key, 0)
        if n == 0:
            fail('expected link %s:%s has zero events' % key)
    rep('per-link event counts',
        dict(('%s:%s' % k, counts[k]) for k in sorted(observed)))

    print('--- measured ---')
    for k, v in OUT:
        print('  %-26s %s' % (k, v))
    print('')
    print('--- verdict ---')
    if FAILS:
        for m in FAILS:
            print('  [FAIL] %s' % m)
        print('')
        print('  %d identity violation(s) -- HARD FAIL' % len(FAILS))
        return 1
    print('  [PASS] expected/observed physical keys match')
    print('  [PASS] local_link_id <-> physical_link_key is a bijection')
    print('  [PASS] every expected link has non-zero events')
    print('')
    print('  NOTE: any cross-cell or cross-algorithm comparison MUST align on')
    print('        physical_link_key; raw link_id is provenance only.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
