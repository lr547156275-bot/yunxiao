# -*- coding: utf-8 -*-
# Synthetic self-tests for r1_gates_ml_v2.py -- the 10 required cases.
#
# Runs BEFORE the checker is frozen and before it sees any real trace.
#
# Fixture arithmetic: C = 10 Gbps, so
#   1250 B -> 1000.0 ns exactly     (round number, easy boundaries)
#   1048 B ->  838.4 ns -> D=838    (truncated, the real S6 size)
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r1_gates_ml_v2 as V2

C = 10e9
SZ = 1250
DUR = 1000
CORE_LO = 10000
T_QLEN = 90000
T_STOP = 90000          # deliberately equal, the S6 situation
HDR = 'time_ns,event,link_id,node_id,if_index,packet_uid,packet_bytes\n'

res = []


def chk(name, ok, detail=''):
    res.append((name, ok, detail))


def pkt(t0, uid, link, node, iff, sz=SZ):
    d = V2.D(sz, C)
    return ['%d,TX_BEGIN,%s,%s,%s,%s,%d' % (t0, link, node, iff, uid, sz),
            '%d,TX_END,%s,%s,%s,%s,%d' % (t0 + d, link, node, iff, uid, sz)]


def begin_only(t0, uid, link, node, iff, sz=SZ):
    return ['%d,TX_BEGIN,%s,%s,%s,%s,%d' % (t0, link, node, iff, uid, sz)]


def write(lines):
    fd, p = tempfile.mkstemp(suffix='.csv', dir='/tmp')
    os.close(fd)
    with open(p, 'w') as f:
        f.write(HDR)
        if lines:
            f.write('\n'.join(lines) + '\n')
    return p


def run(lines, expected, name, expect_pass, qlen=T_QLEN, stop=T_STOP):
    p = write(lines)
    r = subprocess.Popen(
        [sys.executable, os.path.join(HERE, 'r1_gates_ml_v2.py'), p,
         str(int(C)), str(CORE_LO), str(qlen), str(stop), expected, name],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    o = r.communicate()[0].decode('utf-8', 'replace')
    ok = (r.returncode == 0) if expect_pass else (r.returncode != 0)
    chk(name, ok, 'rc=%d' % r.returncode)
    os.unlink(p)
    return o


# body: a clean run of complete pairs well inside core
def body(link, node, iff, n=5, t0=20000, tag='p'):
    L = []
    for i in range(n):
        L += pkt(t0 + i * DUR, '%s%s%d' % (tag, link, i), link, node, iff)
    return L


# ---- 1. BEGIN whose expected_end > stop -> PASS, marked clipped ----------
# core_hi = min(90000, 90000-1000) = 89000.  BEGIN at 89500 -> end 90500 > stop.
L = body('0', '84', '1') + begin_only(89500, 'clip0', '0', '84', '1')
o1 = run(L, '0:84:1', '1. expected_end > stop -> clipped', True)
chk('1b. ledger printed SIMULATION_END_CLIPPED',
    'SIMULATION_END_CLIPPED' in o1 and 'overshoot' in o1)
chk('1c. overshoot value correct (90500-90000=500)',
    'overshoot      = 500 ns past stop' in o1)

# ---- 2. expected_end == stop -> ns-3 same-instant semantics -------------
# BEGIN at 89000 -> end exactly 90000 == T_stop.  Condition is expected_end >=
# T_stop, so this IS clipped: ns-3 stops AT T_stop, and an event scheduled for
# exactly T_stop does not execute (Simulator::Stop cancels at that instant).
L = body('0', '84', '1') + begin_only(89000, 'eq0', '0', '84', '1')
o2 = run(L, '0:84:1', '2. expected_end == stop -> clipped (>= semantics)', True)
chk('2b. equality treated as clipped and documented',
    'expected END   = 90000' in o2 and 'overshoot      = 0 ns past stop' in o2)

# ---- 3. expected_end < stop but no END -> HARD FAIL --------------------
# BEGIN at 88000 -> end 89000 < 90000: the END should have happened.
L = body('0', '84', '1') + begin_only(88000, 'bad0', '0', '84', '1')
o3 = run(L, '0:84:1', '3. expected_end < stop, no END -> FAIL', False)
chk('3b. reported as illegal, not clipped',
    'HARD FAIL' in o3 and 'expected_end' in o3)

# ---- 4. unmatched BEGIN inside core -> HARD FAIL ----------------------
L = body('0', '84', '1') + begin_only(40000, 'core0', '0', '84', '1')
o4 = run(L, '0:84:1', '4. unmatched BEGIN inside core -> FAIL', False)
chk('4b. reason names in-core position',
    'inside core' in o4)

# ---- 5. two trailing unmatched BEGIN on one link -> HARD FAIL ---------
L = (body('0', '84', '1')
     + begin_only(89300, 'c1', '0', '84', '1')
     + begin_only(89600, 'c2', '0', '84', '1'))
o5 = run(L, '0:84:1', '5. two clipped BEGIN on one link -> FAIL', False)
chk('5b. max-1 rule cited', 'max 1' in o5)

# ---- 6. two links each with one legal clipped BEGIN -> PASS ----------
L = (body('0', '84', '1') + begin_only(89500, 'k0', '0', '84', '1')
     + body('1', '83', '1', t0=30000) + begin_only(89400, 'k1', '1', '83', '1'))
o6 = run(L, '0:84:1,1:83:1', '6. one clipped BEGIN per link -> PASS', True)
chk('6b. both links report a clip',
    o6.count('SIMULATION_END_CLIPPED') >= 2)

# ---- 7. one legal link + one illegal link -> overall FAIL ------------
L = (body('0', '84', '1')
     + body('1', '83', '1', t0=30000) + begin_only(40000, 'bad1', '1', '83', '1'))
o7 = run(L, '0:84:1,1:83:1', '7. one good link + one bad -> overall FAIL', False)
chk('7b. good link still shown passing its own gates',
    'link 0 (node=84 if=1)' in o7)

# ---- 8. complete pair straddling core_hi but ending before stop ------
# BEGIN 88500 -> END 89500.  core_hi=89000, so it straddles; END < stop so it is
# a COMPLETE pair.  It must be excluded from core but must NOT fail.
L = body('0', '84', '1') + pkt(88500, 'straddle', '0', '84', '1')
o8 = run(L, '0:84:1', '8. complete pair straddling core_hi -> excluded, not FAIL',
         True)
chk('8b. straddling pair excluded from core, no hard fail',
    'HARD FAIL' not in o8)

# ---- 9. single-link legacy fixtures still pass ---------------------
r = subprocess.Popen([sys.executable,
                      os.path.join(HERE, 'r1_gates_v4_selftest.py')],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
o9 = r.communicate()[0].decode('utf-8', 'replace')
chk('9. frozen single-link v4 self-test still 11/11',
    r.returncode == 0 and '11/11' in o9)
r = subprocess.Popen([sys.executable,
                      os.path.join(HERE, 'r1_gates_ml_selftest.py')],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
o9b = r.communicate()[0].decode('utf-8', 'replace')
chk('9b. multi-link v1 self-test still 13/13',
    r.returncode == 0 and '13/13' in o9b)

# ---- 10. D() arithmetic boundary tests ---------------------------
cases = [
    (1250, 10e9, 1000, 'round number'),
    (1048, 10e9, 838, 'S6/S3 real size: 838.4 truncates to 838'),
    (192, 10e9, 153, 'ACK-ish: 153.6 truncates to 153'),
    (60, 10e9, 48, '60 B min frame: 48.0 exact'),
    (1, 10e9, 0, 'sub-tick: 0.8 ns truncates to 0'),
]
for sz, c, want, why in cases:
    got = V2.D(sz, c)
    chk('10. D(%d B, %.0f Gbps) == %d ns  [%s]' % (sz, c / 1e9, want, why),
        got == want, 'got %d' % got)
# core_hi must NOT be min(T_qlen,T_stop)-Dmax when T_qlen is well before T_stop
L = body('0', '84', '1')
o10 = run(L, '0:84:1', '10b. T_qlen well before T_stop: no extra Dmax cut',
          True, qlen=50000, stop=90000)
# Assert the SEMANTICS, not the exact line wrapping: core_hi must equal T_qlen
# (50000), not min(T_qlen,T_stop) - Dmax (which would be 49000).
chk('10c. core_hi == T_qlen (50000) when T_qlen is binding, not 49000',
    'T_qlen is the binding limit' in o10
    and '= 50000' in o10
    and '= 49000' not in o10
    and "{'0': 50000}" in o10)

# ---- report ----------------------------------------------------
print('=' * 74)
print('r1_gates_ml_v2 SELF-TEST')
print('=' * 74)
print('  C=%.0f Gbps  tick=%d ns  core_lo=%d  T_qlen=%d  T_stop=%d'
      % (C / 1e9, V2.TICK_NS, CORE_LO, T_QLEN, T_STOP))
print('')
fail = 0
for name, ok, d in res:
    print('  [%s] %-60s %s' % ('PASS' if ok else 'FAIL', name, d))
    if not ok:
        fail += 1
print('')
print('  %d/%d self-tests passed' % (len(res) - fail, len(res)))
if fail:
    print('')
    print('  Do NOT freeze or run against real data until these pass.')
sys.exit(1 if fail else 0)
