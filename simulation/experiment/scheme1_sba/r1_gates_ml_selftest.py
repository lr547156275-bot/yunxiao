# -*- coding: utf-8 -*-
# Synthetic self-tests for the MULTI-LINK checker, plus a regression re-run of
# the single-link fixtures so S1-S5 behaviour is proven unchanged.
#
# Required cases:
#   * both links carry events                        -> PASS
#   * same packet_uid on different link_id           -> must NOT cross-pair
#   * one expected link missing                      -> FAIL
#   * duplicate attach (same link twice)             -> FAIL
#   * wrong link_id (unexpected link present)        -> FAIL
#   * each link passes individually; verdict is per-link, not merged
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r1_gates_v4 as V4
import r1_gates_ml as ML

C = 10e9
SZ = 1250            # 1250 B * 8 / 10 Gbps = 1000 ns exactly
DUR = 1000
LO, HI = 10000, 90000
HDR = 'time_ns,event,link_id,node_id,if_index,packet_uid,packet_bytes\n'

res = []


def pkt(t0, uid, link, node, iff, sz=SZ):
    d = int(round(sz * 8.0 / C * 1e9))
    return ['%d,TX_BEGIN,%s,%s,%s,%s,%d' % (t0, link, node, iff, uid, sz),
            '%d,TX_END,%s,%s,%s,%s,%d' % (t0 + d, link, node, iff, uid, sz)]


def write(lines):
    fd, p = tempfile.mkstemp(suffix='.csv', dir='/tmp')
    os.close(fd)
    with open(p, 'w') as f:
        f.write(HDR)
        f.write('\n'.join(lines) + '\n')
    return p


def run_ml(lines, expected, expect_pass, name):
    p = write(lines)
    r = subprocess.Popen(
        [sys.executable, os.path.join(HERE, 'r1_gates_ml.py'), p, str(int(C)),
         str(LO), str(HI), expected, name],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o = r.communicate()[0].decode('utf-8', 'replace')
    rc = r.returncode
    ok = (rc == 0) if expect_pass else (rc != 0)
    res.append((name, ok, 'rc=%d' % rc, o))
    os.unlink(p)
    return o


# ---- 1. both links carry events -> PASS ---------------------------------
L = []
for i, t in enumerate(range(20000, 25000, DUR)):
    L += pkt(t, 'a%d' % i, '0', '84', '1')
for i, t in enumerate(range(30000, 35000, DUR)):
    L += pkt(t, 'b%d' % i, '1', '83', '1')
o1 = run_ml(L, '0:84:1,1:83:1', True, '1. both links present')

# ---- 2. identical packet_uid on both links must not cross-pair ----------
# Same uid "shared" on link 0 at t=20000 and link 1 at t=60000.  If the checker
# paired by uid alone it would see BEGIN(link0)/END(link1) and compute a
# nonsense 40 us duration -> R-1a.4 would fail.  Per-link grouping must pass.
L = []
L += pkt(20000, 'shared', '0', '84', '1')
L += pkt(60000, 'shared', '1', '83', '1')
for i, t in enumerate(range(21000, 24000, DUR)):
    L += pkt(t, 'x%d' % i, '0', '84', '1')
for i, t in enumerate(range(61000, 64000, DUR)):
    L += pkt(t, 'y%d' % i, '1', '83', '1')
o2 = run_ml(L, '0:84:1,1:83:1', True, '2. same uid on two links, no cross-pair')
res.append(('2b. duration stayed 1000 ns (not 40000 ns)',
            'duration == size_bytes*8/C' in o2 and '0 deviate' in o2,
            '', ''))

# ---- 3. an expected link is missing -> FAIL -----------------------------
L = []
for i, t in enumerate(range(20000, 25000, DUR)):
    L += pkt(t, 'c%d' % i, '0', '84', '1')
o3 = run_ml(L, '0:84:1,1:83:1', False, '3. expected link missing')
res.append(('3b. missing link reported by identity',
            'MISSING' in o3 and 'NO DATA' in o3, '', ''))

# ---- 4. unexpected / wrong link_id present -> FAIL ----------------------
L = []
for i, t in enumerate(range(20000, 25000, DUR)):
    L += pkt(t, 'd%d' % i, '0', '84', '1')
for i, t in enumerate(range(30000, 33000, DUR)):
    L += pkt(t, 'e%d' % i, '7', '99', '3')       # not in expected set
o4 = run_ml(L, '0:84:1', False, '4. unexpected link_id present')
res.append(('4b. unexpected link named in output',
            'UNEXPECTED' in o4, '', ''))

# ---- 5. duplicate attach: same link emitted twice per packet -> FAIL ----
# A double-bound callback would duplicate every event on that link.
L = []
for i, t in enumerate(range(20000, 25000, DUR)):
    q = pkt(t, 'f%d' % i, '0', '84', '1')
    L += q + q                                    # duplicated rows
o5 = run_ml(L, '0:84:1', False, '5. duplicate attach (doubled events)')

# ---- 6. each link individually valid; verdict is per-link ---------------
# Link 0 is clean; link 1 has an overlap.  Overall must FAIL even though one
# link is perfect -- a single link must not represent the scenario.
L = []
for i, t in enumerate(range(20000, 25000, DUR)):
    L += pkt(t, 'g%d' % i, '0', '84', '1')
L += pkt(30000, 'h1', '1', '83', '1')
L += pkt(30500, 'h2', '1', '83', '1')             # overlaps h1
o6 = run_ml(L, '0:84:1,1:83:1', False, '6. one good link + one bad link')
res.append(('6b. good link still reported as passing its own gates',
            'link 0 (node=84 if=1, expected)' in o6, '', ''))

# ---- 7. two links each at full utilisation -> PASS ---------------------
# Back-to-back on both links simultaneously: 2 x 10 Gbps aggregate.  Must NOT
# be merged into a single 10 Gbps curve (that would report 200% and fail).
L = []
for i, t in enumerate(range(20000, 30000, DUR)):
    L += pkt(t, 'i%d' % i, '0', '84', '1')
    L += pkt(t, 'j%d' % i, '1', '83', '1')
o7 = run_ml(L, '0:84:1,1:83:1', True,
            '7. both links saturated, not merged into one curve')

# ---- 8. empty trace must not be reported as PASS ----------------------
p = write([])
r = subprocess.Popen(
    [sys.executable, os.path.join(HERE, 'r1_gates_ml.py'), p, str(int(C)),
     str(LO), str(HI), '0:84:1', 'empty'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
o8 = r.communicate()[0].decode('utf-8', 'replace')
res.append(('8. empty trace refuses to PASS', r.returncode != 0, '', ''))
os.unlink(p)

# ---- 9. single-link regression: rerun the frozen v4 self-test ----------
r = subprocess.Popen([sys.executable,
                      os.path.join(HERE, 'r1_gates_v4_selftest.py')],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
o9 = r.communicate()[0].decode('utf-8', 'replace')
res.append(('9. single-link v4 self-test still passes (no regression)',
            r.returncode == 0 and '11/11' in o9, '', ''))

# ---- report ------------------------------------------------------------
print('=' * 74)
print('MULTI-LINK CHECKER SELF-TEST')
print('=' * 74)
print('')
fail = 0
for name, ok, d, _ in res:
    print('  [%s] %-58s %s' % ('PASS' if ok else 'FAIL', name, d))
    if not ok:
        fail += 1
print('')
print('  %d/%d self-tests passed' % (len(res) - fail, len(res)))
if fail:
    print('')
    print('  Do NOT freeze or run against real data until these pass.')
sys.exit(1 if fail else 0)
