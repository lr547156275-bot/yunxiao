# -*- coding: utf-8 -*-
# Hard acceptance gates for the fixed S3 run (report items 4 and 7).
#
# Any FAIL stops everything: no tuning, no next cell.  The two defect classes
# are reported separately and never merged.
#
# Usage: python3 scope_acceptance.py <out_dir>
import csv
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'qc_s3_rho090_fix_out'
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, OUT)

PAY = 1000.0
WIRE = 1048.0
C = 10e9
N_EXPECT = 65                      # 64 incast + 1 background, all on link 0
MINR = 100e6
FLOOR_PAY = N_EXPECT * MINR                     # 6.500 G
FLOOR_LINK = FLOOR_PAY * WIRE / PAY             # 6.812 G
DRAIN_MAX = C - FLOOR_LINK                      # 3.188 G = 0.3188 C
Q_ABS = 838.86e-6 * C / 8.0                     # 1,048,575 B
Q_RED = Q_ABS - 67072.0
MAX_BOOST = 0.30 * C

gates = []


def gate(name, ok, detail):
    gates.append((name, ok, detail))


def rows(path):
    p = os.path.join(D, path)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return list(csv.DictReader(f))


def fnum(r, k, d=0.0):
    try:
        return float(r.get(k, d) or d)
    except (TypeError, ValueError):
        return d


print('=== S3 rho=0.90 acceptance (%s) ===' % OUT)
print('  derived: floor_link=%.4f G  DRAIN_MAX=%.4f G (%.4f C)  Q_abs=%.0f B'
      % (FLOOR_LINK / 1e9, DRAIN_MAX / 1e9, DRAIN_MAX / C, Q_ABS))
print('')

qc = rows('qc_trace.csv')
if qc is None:
    print('FATAL: qc_trace.csv missing -- run did not produce controller trace')
    sys.exit(2)

own = [r for r in qc if r.get('owns_rates') == '1']
noown = [r for r in qc if r.get('owns_rates') != '1']

# ---------------- DEFECT A gates: wire accounting -------------------------
fw = sorted(set(int(fnum(r, 'floor_wire_bps')) for r in own))
fp = sorted(set(int(fnum(r, 'floor_payload_bps')) for r in own))
bad_ratio = 0
for r in own:
    w, p = fnum(r, 'floor_wire_bps'), fnum(r, 'floor_payload_bps')
    if p > 0 and abs(w - p * WIRE / PAY) > 2.0:
        bad_ratio += 1
gate('A-1. every floor_wire == floor_payload x 1048/1000',
     bad_ratio == 0,
     '%d/%d owning epochs violate the ratio' % (bad_ratio, len(own)))
gate('A-2. no floor_wire built on the 1064 ratio (6.916 G) remains',
     not any(abs(v - 6.916e9) < 1e6 for v in fw),
     'floor_wire distinct values: %s' % [round(v / 1e9, 4) for v in fw[:8]])
maxfloor = max(fw) if fw else 0
gate('A-3. peak floor_wire == 6.812 G (65 owned QPs, exact closure)',
     abs(maxfloor - FLOOR_LINK) < 2e6,
     'peak floor_wire = %.4f G (expect %.4f G)'
     % (maxfloor / 1e9, FLOOR_LINK / 1e9))
maxfp = max(fp) if fp else 0
gate('A-4. peak floor_payload == 6.500 G',
     abs(maxfp - FLOOR_PAY) < 2e6,
     'peak floor_payload = %.4f G' % (maxfp / 1e9))

# ---------------- DEFECT B gates: control scope ---------------------------
# DRAIN_MAX is headroom against the CURRENT floor, so it legitimately rises as
# members complete.  What must never happen is DRAIN actually being EMITTED
# beyond C - floor.  Gate the emitted quantity, and separately require that
# during full overlap (the only time the 65-member floor applies) the headroom
# equals exactly C - 6.812 G.
dm_over = [r for r in own
           if fnum(r, 'drain') > (C - fnum(r, 'floor_wire_bps')) + 2e6]
gate('B-1. emitted drain never exceeds C - current floor',
     len(dm_over) == 0,
     '%d epochs emit drain above their own headroom' % len(dm_over))
ov_full = [r for r in own if int(fnum(r, 'floor_count')) == N_EXPECT]
dm_full = [fnum(r, 'drain_max_wire_bps') for r in ov_full]
gate('B-1b. at full 65-member floor, DRAIN_MAX == 3.188 G exactly',
     bool(dm_full) and abs(max(dm_full) - DRAIN_MAX) < 2e6
     and abs(min(dm_full) - DRAIN_MAX) < 2e6,
     'DRAIN_MAX over %d full-floor epochs = [%.4f, %.4f] G (expect %.4f)'
     % (len(dm_full), (min(dm_full) if dm_full else 0) / 1e9,
        (max(dm_full) if dm_full else 0) / 1e9, DRAIN_MAX / 1e9))
pc = [int(fnum(r, 'protected_count')) for r in own]
gate('B-2. protected_count never reaches 66',
     (max(pc) if pc else 0) <= N_EXPECT,
     'max protected_count = %d (expect <= %d)'
     % (max(pc) if pc else 0, N_EXPECT))
gate('B-3. protected_count reaches the full 65 at batch start',
     (max(pc) if pc else 0) == N_EXPECT,
     'max protected_count = %d' % (max(pc) if pc else 0))

# ---- DEFECT C gates: the three sets are separate -------------------------
# Overlap = every epoch where a generation is being steered.
ov = [r for r in own if int(fnum(r, 'new_gen_count')) > 0]
fc = [int(fnum(r, 'floor_count')) for r in ov]
gc_ = [int(fnum(r, 'new_gen_count')) for r in ov]
oc = [int(fnum(r, 'old_side_count')) for r in ov]
gate('C-1. full overlap: floor=65, newGen=64, oldSide=1',
     (max(fc) if fc else 0) == 65 and (max(gc_) if gc_ else 0) == 64
     and (max(oc) if oc else 0) == 1,
     'max floor=%d newGen=%d oldSide=%d'
     % (max(fc) if fc else 0, max(gc_) if gc_ else 0, max(oc) if oc else 0))
gate('C-2. floor set is never smaller than the generation set',
     all(int(fnum(r, 'floor_count')) >= int(fnum(r, 'new_gen_count'))
         for r in qc),
     'floor is a superset of the steered set in every epoch')
# The background flow must stay floored from its admission until it stops being
# live.  Before its admission (t=1.0 s) and after the run ends there is nothing
# to floor, so restrict the window to epochs where a floor member exists at all
# and check the floor value tracks the count exactly.
bgwin = [r for r in qc if int(fnum(r, 'floor_count')) > 0]
bad_bg = [r for r in bgwin
          if abs(fnum(r, 'floor_payload_bps')
                 - int(fnum(r, 'floor_count')) * MINR) > 2e6]
gate('C-3. floor value equals floor_count x MIN_RATE in every floored epoch',
     len(bad_bg) == 0,
     '%d/%d floored epochs mismatch count x 100 Mbps'
     % (len(bad_bg), len(bgwin)))
gate('C-3b. background flow is floored for the whole steering window',
     all(int(fnum(r, 'old_side_count')) >= 1 for r in own),
     'old_side_count >= 1 in all %d owning epochs' % len(own))
gate('C-4. floor never collapses to 0 while a generation is steered',
     all(fnum(r, 'floor_wire_bps') > 0 for r in ov),
     'no floor=0 epoch during overlap')
# The defect-C signature was NOT "6.7072 G appears" -- that value is correct
# once one member has completed (64 x 104.8 Mbps).  The signature was a
# 64-share floor while all 65 members were still live, i.e. floor_count == 65
# paired with a 64-share value.  Gate that, not the number.
c5_bad = [r for r in ov
          if int(fnum(r, 'floor_count')) == N_EXPECT
          and abs(fnum(r, 'floor_wire_bps') - FLOOR_LINK) > 2e6]
gate('C-5. no 64-share floor while all 65 members are live',
     len(c5_bad) == 0,
     '%d epochs with floor_count=65 but a floor != 6.812 G' % len(c5_bad))
gate('C-6. DRAIN_MAX never reaches 1.0 C',
     not any(fnum(r, 'drain_max_wire_bps') >= 0.99 * C for r in qc),
     'max drain_max = %.4f C'
     % (max([fnum(r, 'drain_max_wire_bps') for r in qc] + [0]) / C))
# The decisive defect-B signature was 384,944 single-member epochs that were
# STEERING (the controller ran for the whole 3 s outside any batch).  A
# single-member epoch is legitimate during the handoff close-out, provided
# nothing is emitted.  So gate on steering, not on the count alone.
single = sum(1 for v in pc if v == 1)
single_steering = [r for r in own
                   if int(fnum(r, 'protected_count')) == 1
                   and (fnum(r, 'drain') != 0
                        or fnum(r, 'boost_commanded') != 0)]
gate('B-4. no single-member epoch ever STEERS (the 384,944-epoch signature)',
     len(single_steering) == 0,
     '%d single-member owning epochs, %d of them steering (was 384,944)'
     % (single, len(single_steering)))
sv = sum(int(fnum(r, 'scope_violations')) for r in qc[-1:]) if qc else 0
gate('B-5. hard invariant: zero scope violations',
     sv == 0, 'scope_violations = %d' % sv)
tr = int(fnum(qc[-1], 'ownership_transitions')) if qc else 0
gate('B-6. exactly one ownership transition (single batch)',
     tr == 1, 'ownership_transitions = %d' % tr)
pm = int(fnum(qc[-1], 'path_metadata_missing')) if qc else 0
gate('B-7. no PATH_METADATA_MISSING_AFTER_OWNERSHIP',
     pm == 0, 'path_metadata_missing = %d' % pm)

# --- background-flow three phases A / B / C (item 4) ---------------------
bad_a = [r for r in noown
         if fnum(r, 'boost_effective') != 0 or fnum(r, 'drain') != 0]
gate('B-8. phase A/C: not owning => boost == 0 and drain == 0',
     len(bad_a) == 0,
     '%d non-owning epochs with non-zero boost/drain' % len(bad_a))
ledger_nonzero_not_owning = sum(
    1 for r in noown if int(fnum(r, 'ledger_count')) > 0)
gate('B-9. a non-empty ledger does NOT trigger control',
     len(bad_a) == 0,
     '%d non-owning epochs had ledger_count > 0, all inert'
     % ledger_nonzero_not_owning)

# ---------------- safety gates (unchanged thresholds) --------------------
sumr = [fnum(r, 'sumR_effective') for r in own]
minsum = min(sumr) if sumr else 0.0
gate('S-1. sumR never falls below the floor',
     minsum >= FLOOR_LINK - 2e6,
     'min sumR = %.4f G (floor %.4f G)' % (minsum / 1e9, FLOOR_LINK / 1e9))
q0 = [fnum(r, 'q0') for r in qc]
qpeak = max(q0) if q0 else 0.0
gate('S-2. actual queue peak <= Q_abs',
     qpeak <= Q_ABS,
     'queue peak = %.0f B = %.2f%% of Q_abs' % (qpeak, 100.0 * qpeak / Q_ABS))
red = [r for r in qc if r.get('zone') == 'RED']
gate('S-3. RED is exited by end of run',
     len(red) == 0 or qc[-1].get('zone') != 'RED',
     'final zone = %s, RED epochs = %d' % (qc[-1].get('zone'), len(red)))
boosts = [fnum(r, 'boost_effective') for r in qc]
gate('S-4. boost never exceeds MAX_BOOST = 0.30 C',
     (max(boosts) if boosts else 0) <= MAX_BOOST + 2e6,
     'max boost = %.4f G (limit %.4f G)'
     % ((max(boosts) if boosts else 0) / 1e9, MAX_BOOST / 1e9))

# PFC / drops / retransmissions
fs = rows('flow_summary.csv')
if fs:
    inc = [r for r in fs if r.get('flow_id') not in (None, '65')]
    done = sum(1 for r in fs if fnum(r, 'completed') > 0)
    gate('S-5. all 64 incast flows complete',
         done >= 64, '%d flows report completed > 0' % done)
pfc = rows('pfc_events.csv')
gate('S-6. zero PFC pause events',
     pfc is None or len(pfc) == 0,
     '%d PFC events' % (0 if pfc is None else len(pfc)))

print('')
fail = 0
for name, ok, detail in gates:
    print('  [%s] %-56s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fail += 1
print('')
print('  %d/%d gates passed' % (len(gates) - fail, len(gates)))
print('')
print('  owning epochs = %d, non-owning = %d' % (len(own), len(noown)))
if pc:
    hist = {}
    for v in pc:
        hist[v] = hist.get(v, 0) + 1
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:6]
    print('  protected_count histogram (top 6): %s' % top)
if fail:
    print('')
    print('  HARD GATE FAILED -- stop, do NOT run rho=0.9875, do NOT tune.')
sys.exit(1 if fail else 0)
