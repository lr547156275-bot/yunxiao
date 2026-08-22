# -*- coding: utf-8 -*-
# TOP-LEVEL ACCEPTANCE, v2.  Pure composition and counting layer.
#
# WHAT THIS FILE DOES AND DOES NOT DO
# -----------------------------------
# It does ONE thing: run the 19 unchanged top-level gates from the frozen
# independent_acceptance.py, replace that file's legacy top-level R-1 ONE-FOR-ONE
# with the composite verdict of the frozen r1_gates_v4.py, and report 20.
#
# It modifies nothing.  independent_acceptance.py and r1_gates_v4.py are IMPORTED
# and executed as-is; no formula, guard, window, tolerance or threshold in either
# is touched here.  The recorder, controller, configs, rho, C, MIN_RATE,
# MAX_BOOST and all output data are untouched.
#
# THE REPLACEMENT
# ---------------
#   LEGACY_R1 : "max sampled service_rate_bps <= C", read from
#               port_summary.csv:service_rate_bps (5 us fixed-window aggregate).
#               Ruled INVALID_GATE_PACKET_COMPLETION_QUANTIZATION: a 5 us window
#               holds 5.9637 packets of 1048 B, so a window completing 6 whole
#               packets measures 6288*8/5us = 10.0608 Gbps.  The gate cannot
#               distinguish that sampling artefact from a real overrun.
#   REPLACED BY: r1_gates_v4.py, evaluated on real per-packet TX_BEGIN/TX_END
#               events.  Its 14 subchecks collapse to ONE top-level verdict:
#               all 14 pass -> R-1 PASS; any subcheck fails -> R-1 FAIL.
#
# COUNTING RULE (explicit, to prevent inflation)
#   top-level = 19 unchanged gates + 1 composite R-1 = 20.
#   The 14 subchecks are NEVER added to the 19.  33 is not a valid total.
#
# Usage: python3 independent_acceptance_v2.py <out_dir> <expect_incast> \
#                <tx_csv> <core_lo_ns> <core_hi_ns> [capacity_bps] [label]
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LEGACY_ENTRY = 'independent_acceptance.py'
LEGACY_SHA = '59dfdb2786a44fa2818f8d9191bdca3b46afec3f0bd2434cded01044b86fb4f1'
R1ABC_ENTRY = 'r1_gates_v4.py'
R1ABC_SHA = '924e1594a8df551d699910382f7be9883fa23b730bc2cf70becc5c7dc6c1944b'
R1ABC_SELFTEST_SHA = '30d7f49c57280a1dde1da051da98161a54fa3ec476a4cd2ab47ce9e483646212'
RECORDER_SHA = '54a11a1d3df4177fc93e72000ba0f6e0276ab58bd72f1e00c94d30bfc95aa73d'

# The single legacy gate that is superseded, identified by its exact name.
LEGACY_R1_NAME = 'R-1. served rate never exceeds link capacity C'

if len(sys.argv) < 6:
    print('usage: independent_acceptance_v2.py <out_dir> <expect_incast> '
          '<tx_csv> <core_lo_ns> <core_hi_ns> [C_bps] [label]')
    sys.exit(2)

OUT = sys.argv[1]
EXPECT = sys.argv[2]
TX = sys.argv[3]
LO = sys.argv[4]
HI = sys.argv[5]
C = sys.argv[6] if len(sys.argv) > 6 else '10000000000'
LABEL = sys.argv[7] if len(sys.argv) > 7 else OUT


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


# ---- integrity: refuse to run if either frozen checker has moved ----------
errs = []
for name, want in ((LEGACY_ENTRY, LEGACY_SHA), (R1ABC_ENTRY, R1ABC_SHA)):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        errs.append('%s missing' % name)
        continue
    got = sha256(p)
    if got != want:
        errs.append('%s SHA mismatch: got %s want %s' % (name, got, want))
if errs:
    print('FATAL: frozen checker integrity failure')
    for e in errs:
        print('  ' + e)
    sys.exit(2)

print('=' * 78)
print('TOP-LEVEL ACCEPTANCE v2 -- %s' % LABEL)
print('=' * 78)
print('  LEGACY_R1            = SUPERSEDED_BY_PACKET_AWARE_R1ABC')
print('  LEGACY_CHECKER_SHA   = %s' % LEGACY_SHA)
print('  R1ABC_CHECKER_SHA    = %s' % R1ABC_SHA)
print('  R1ABC_SELFTEST_SHA   = %s' % R1ABC_SELFTEST_SHA)
print('  RECORDER_SHA         = %s' % RECORDER_SHA)
print('  counting rule        = 19 unchanged gates + 1 composite R-1 = 20')
print('                         (the 14 R-1a/b/c subchecks are NOT added)')
print('')

# ---- part 1: the 19 unchanged gates -------------------------------------
# Run the frozen legacy entry point as a subprocess so it executes byte-for-byte
# as frozen, then parse its gate lines.  Nothing is re-implemented here.
print('-' * 78)
print('PART 1 -- 19 unchanged top-level gates (from frozen %s)' % LEGACY_ENTRY)
print('-' * 78)
p1 = subprocess.Popen(
    [sys.executable, os.path.join(HERE, LEGACY_ENTRY), OUT, EXPECT, LABEL],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=HERE)
o1 = p1.communicate()[0].decode('utf-8', 'replace')
print(o1)

legacy_gates = []
lines = o1.split('\n')
for i, ln in enumerate(lines):
    s = ln.strip()
    if s.startswith('[PASS] ') or s.startswith('[FAIL] '):
        verdict = s[1:5]
        name = s[7:].strip()
        legacy_gates.append((name, verdict == 'PASS'))

kept = [g for g in legacy_gates if g[0] != LEGACY_R1_NAME]
dropped = [g for g in legacy_gates if g[0] == LEGACY_R1_NAME]

# ---- part 2: the composite R-1 -----------------------------------------
print('-' * 78)
print('PART 2 -- composite R-1 (from frozen %s)' % R1ABC_ENTRY)
print('-' * 78)
p2 = subprocess.Popen(
    [sys.executable, os.path.join(HERE, R1ABC_ENTRY), TX, C, LO, HI,
     LABEL + ' [R-1a/b/c]'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=HERE)
o2 = p2.communicate()[0].decode('utf-8', 'replace')
r1_rc = p2.returncode
print(o2)

sub = []
for ln in o2.split('\n'):
    s = ln.strip()
    if s.startswith('[PASS] ') or s.startswith('[FAIL] '):
        sub.append((s[7:].strip(), s[1:5] == 'PASS'))
sub_pass = sum(1 for x in sub if x[1])
r1_composite = (len(sub) > 0 and sub_pass == len(sub) and r1_rc == 0)

# ---- part 3: composition and counting ---------------------------------
print('=' * 78)
print('COMPOSITION')
print('=' * 78)
if len(dropped) == 1:
    print('  legacy gate replaced ONE-FOR-ONE:')
    print('    "%s"' % LEGACY_R1_NAME)
    print('    legacy verdict was: %s  (SUPERSEDED, not counted)'
          % ('PASS' if dropped[0][1] else 'FAIL'))
else:
    print('  WARNING: expected exactly 1 legacy R-1 line, found %d'
          % len(dropped))
print('  unchanged gates carried forward : %d' % len(kept))
print('  composite R-1 subchecks         : %d/%d' % (sub_pass, len(sub)))
print('  composite R-1 verdict           : %s'
      % ('PASS' if r1_composite else 'FAIL'))
print('')

kept_pass = sum(1 for g in kept if g[1])
total = len(kept) + 1
total_pass = kept_pass + (1 if r1_composite else 0)

failed = [g[0] for g in kept if not g[1]]
if not r1_composite:
    failed.append('R-1 composite (packet-aware) -- failing subchecks: %s'
                  % [x[0].split()[0] for x in sub if not x[1]])

print('  R-1 composite = %s (%d/%d subchecks)'
      % ('PASS' if r1_composite else 'FAIL', sub_pass, len(sub)))
print('  TOP_LEVEL_ACCEPTANCE = %d/%d' % (total_pass, total))
if failed:
    print('')
    print('  FAILED:')
    for f in failed:
        print('    - %s' % f)
    print('')
    print('  HARD GATE FAILED -- stop; retain full trace; do not continue.')
if len(dropped) != 1 or total != 20:
    print('')
    print('  STRUCTURAL WARNING: expected 20 top-level gates '
          '(19 kept + 1 composite), got %d' % total)
sys.exit(0 if (total_pass == total and total == 20) else 1)
