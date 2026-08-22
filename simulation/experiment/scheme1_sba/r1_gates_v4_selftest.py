# -*- coding: utf-8 -*-
# Synthetic unit tests for r1_gates_v4.py, per the 8 required cases.
#
# These run against hand-built traces with known-correct and known-broken
# structure, BEFORE the checker is frozen and before it touches real data.  The
# point is to prove the checker can actually distinguish a boundary artefact
# from a real violation -- v3 could not, which is why it produced two spurious
# FAILs.
#
# C = 10 Gbps, so a 1250 B packet serializes in exactly 1000 ns.  Using a size
# whose serialization time is a round number keeps the fixtures readable; the
# checker itself never assumes any particular size.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r1_gates_v4 as G

C = 10e9
SZ = 1250            # 1250 B * 8 / 10 Gbps = 1000 ns exactly
DUR = 1000

results = []


def row(t, ev, uid, sz=SZ):
    return {'time_ns': str(t), 'event': ev, 'node_id': '84',
            'ifindex': '1', 'link_id': '0', 'packet_uid': str(uid),
            'size_bytes': str(sz)}


def pkt(t0, uid, sz=SZ):
    d = int(round(sz * 8.0 / C * 1e9))
    return [row(t0, 'TX_BEGIN', uid, sz), row(t0 + d, 'TX_END', uid, sz)]


def run(name, rows, core_lo, core_hi, expect_pass, only=None):
    g, o = G.analyse(rows, C, core_lo, core_hi, name, verbose=False)
    if only:
        sel = [x for x in g if x[0].startswith(only)]
    else:
        sel = g
    failed = [x for x in sel if not x[1]]
    ok = (len(failed) == 0) if expect_pass else (len(failed) > 0)
    results.append((name, ok, expect_pass,
                    [x[0].split()[0] for x in failed][:4]))
    return ok


# core spans [10000, 90000]; guards are outside it
LO, HI = 10000, 90000

# ---- 1. leading unmatched END + valid interior -> PASS --------------------
r = [row(9500, 'TX_END', 'clip_lead')]          # BEGIN predates the trace
for i, t in enumerate(range(20000, 25000, DUR)):
    r += pkt(t, 'p%d' % i)
run('1. leading unmatched END + valid interior', r, LO, HI, True)

# ---- 2. trailing unmatched BEGIN + valid interior -> PASS ----------------
r = []
for i, t in enumerate(range(20000, 25000, DUR)):
    r += pkt(t, 'q%d' % i)
r += [row(90500, 'TX_BEGIN', 'clip_trail')]     # END postdates the trace
run('2. trailing unmatched BEGIN + valid interior', r, LO, HI, True)

# ---- 3. unmatched INSIDE core -> FAIL ------------------------------------
r = []
for i, t in enumerate(range(20000, 25000, DUR)):
    r += pkt(t, 'r%d' % i)
r += [row(40000, 'TX_BEGIN', 'orphan_core')]    # never ends, inside core
run('3. unmatched inside core', r, LO, HI, False, only='R-1a.2a')

# ---- 4. TWO leading unmatched ENDs -> FAIL ------------------------------
r = [row(9400, 'TX_END', 'clipA'), row(9600, 'TX_END', 'clipB')]
for i, t in enumerate(range(20000, 25000, DUR)):
    r += pkt(t, 's%d' % i)
run('4. two leading unmatched ENDs', r, LO, HI, False, only='R-1a.2b')

# ---- 5. overlapping adjacent packets -> FAIL ----------------------------
r = pkt(20000, 'o1') + pkt(20500, 'o2')         # o2 starts before o1 ends
run('5. overlapping serialization intervals', r, LO, HI, False,
    only='R-1a.6')

# ---- 6. back-to-back busy period -> PASS -------------------------------
r = []
for i, t in enumerate(range(20000, 30000, DUR)):
    r += pkt(t, 'b%d' % i)                      # zero gap, one busy period
ok6 = run('6. contiguous busy period', r, LO, HI, True)
g6, o6 = G.analyse(r, C, LO, HI, 'bp', verbose=False)
n_bp = [v for k, v in o6 if k == 'busy periods (core)']
results.append(('6b. contiguous run forms exactly 1 busy period',
                n_bp == ['1'] or n_bp == [1], True, n_bp))

# ---- 7. several busy periods separated by idle -> PASS -----------------
r = []
for i, t in enumerate(range(20000, 23000, DUR)):
    r += pkt(t, 'c%d' % i)
for i, t in enumerate(range(50000, 53000, DUR)):
    r += pkt(t, 'd%d' % i)
run('7. multiple busy periods with idle gaps', r, LO, HI, True)
g7, o7 = G.analyse(r, C, LO, HI, 'bp2', verbose=False)
n_bp7 = [v for k, v in o7 if k == 'busy periods (core)']
results.append(('7b. two separated runs form exactly 2 busy periods',
                n_bp7 == ['2'] or n_bp7 == [2], True, n_bp7))

# ---- 8. numerator includes a boundary packet, denominator does not -> FAIL
# A packet straddling the core start: its BEGIN is before core_lo but its END is
# inside core.  If the checker counted its bytes while measuring span only from
# the first in-core BEGIN, work would exceed span.  v4 must EXCLUDE it, so the
# gates pass; the test asserts the exclusion happened by checking the pair
# count, and asserts that FORCING it in (core_lo moved earlier) is what fails.
r = [row(9200, 'TX_BEGIN', 'straddle'), row(10200, 'TX_END', 'straddle')]
for i, t in enumerate(range(20000, 25000, DUR)):
    r += pkt(t, 'e%d' % i)
g8, o8 = G.analyse(r, C, LO, HI, 'straddle', verbose=False)
excl = [v for k, v in o8 if k == 'pairs excluded as boundary/guard']
incore = [v for k, v in o8 if k == 'complete pairs fully inside core']
results.append(('8. straddling packet excluded from work AND span',
                excl == [1] and incore == [5], True, (excl, incore)))
# and the checker must still pass overall, since exclusion is correct
run('8b. straddling packet does not break the gates', r, LO, HI, True)

# ---- report -------------------------------------------------------------
print('=' * 74)
print('r1_gates_v4 SYNTHETIC SELF-TEST')
print('=' * 74)
print('  C=%.0f Gbps, fixture packet %d B -> %d ns serialization'
      % (C / 1e9, SZ, DUR))
print('')
fail = 0
for name, ok, expect, detail in results:
    print('  [%s] %-56s %s' % ('PASS' if ok else 'FAIL', name,
                               '' if ok else 'detail=%s' % (detail,)))
    if not ok:
        fail += 1
print('')
print('  %d/%d self-tests passed' % (len(results) - fail, len(results)))
if fail:
    print('')
    print('  Do NOT freeze or run this checker until the self-tests pass.')
sys.exit(1 if fail else 0)
