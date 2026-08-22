# -*- coding: utf-8 -*-
# R-1a/b/c MULTI-LINK v2 -- explicit simulation-end boundary model.
#
# Supersedes r1_gates_ml.py (ec374d80...), whose S6 result (13/14 per link) is
# retained and labelled CHECKER_SIMULATION_END_BOUNDARY_INCOMPLETE.  That
# version set core_hi = QLEN_MON_END; for S6 QLEN_MON_END == SIMULATOR_STOP_TIME
# exactly, so the trailing guard had zero width and a packet whose TX_END could
# not physically occur (the simulator had stopped) was counted as an in-core
# unmatched BEGIN.
#
# The per-link R-1a/b/c FORMULAS are imported from the frozen r1_gates_v4.py
# (924e1594...) and are neither reimplemented nor altered.  v2 adds only:
#   * per-link Dmax, derived from the REAL packet_bytes in that link's trace
#     and that link's C -- never a hardcoded 1200 ns;
#   * core_hi_l = min(T_qlen, T_stop - Dmax_l)   [NOT min(T_qlen,T_stop)-Dmax];
#   * pairing on the FULL trace by (link_id,node_id,if_index,packet_uid) BEFORE
#     any core windowing;
#   * a SIMULATION_END_CLIPPED ledger with six mandatory conditions;
#   * hard failure for every other unmatched case.
#
# Arithmetic note, verified against this build rather than assumed:
#   DataRate::CalculateTxTime returns bytes*8/bps as an exact double
#   (data-rate.cc), Seconds() converts it at Time::NS resolution, and the
#   default resolution is Time::NS (time.cc:153).  ns-3 TRUNCATES, so
#   1048 B @ 10 Gbps = 838.4 ns is observed as 838 ns, and 192 B = 153.6 ns is
#   observed as 153 ns.  Both confirmed in the S6 trace
#   (duration=838 x 985340, duration=153 x 60).  D() therefore uses floor, not
#   ceil; ceil would over-predict by 1 ns and misclassify boundary packets.
#
# Usage: python3 r1_gates_ml_v2.py <tx_csv> <C_bps> <core_lo> <t_qlen_end>
#                                  <t_stop_ns> <expected_links> [label]
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r1_gates_v4 as V4          # frozen per-link formulas

TICK_NS = V4.TICK_NS              # 1 ns, from the frozen module


def D(bytes_, C, tick=TICK_NS):
    """Serialization time in ns as the simulator computes it.

    exact = bytes*8/C seconds -> ns; ns-3 stores it at Time::NS resolution by
    truncation (verified: 838.4 -> 838, 153.6 -> 153).  Returned in whole ticks.
    """
    exact_ns = bytes_ * 8.0 / C * 1e9
    return int(math.floor(exact_ns / tick)) * tick


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def norm(rows):
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
    if len(sys.argv) < 7:
        print('usage: r1_gates_ml_v2.py <tx_csv> <C_bps> <core_lo> '
              '<t_qlen_end> <t_stop_ns> <expected_links> [label]')
        return 2
    tx = sys.argv[1]
    P = tx if os.path.isabs(tx) else os.path.join(HERE, tx)
    C = float(sys.argv[2])
    core_lo = int(sys.argv[3])
    t_qlen = int(sys.argv[4])
    t_stop = int(sys.argv[5])
    expected = [tuple(x.split(':')) for x in sys.argv[6].split(',') if x]
    label = sys.argv[7] if len(sys.argv) > 7 else tx

    if not os.path.exists(P):
        print('FATAL: %s missing' % P)
        return 2
    rows = norm(load(P))
    if not rows:
        print('FATAL: trace empty -- refusing to report PASS on no data')
        return 2

    print('=' * 78)
    print('R-1a/b/c MULTI-LINK v2 -- %s' % label)
    print('=' * 78)
    print('  per-link formulas : frozen r1_gates_v4.py')
    print('  C (per link)      : %.4f Gbps' % (C / 1e9))
    print('  T_qlen (QLEN_MON_END) : %d ns' % t_qlen)
    print('  T_stop (SIM stop)     : %d ns' % t_stop)
    print('  tick                  : %d ns (ns-3 Time::NS, truncating)' % TICK_NS)
    print('  core_lo               : %d ns' % core_lo)
    print('')

    # ---- STEP 1: pair on the FULL trace, keyed by link identity + uid -----
    groups = {}
    for r in rows:
        k = (r['link_id'], r['node_id'], r['ifindex'])
        groups.setdefault(k, []).append(r)
    obs = sorted(groups.keys())
    exp = sorted(expected)
    missing = [x for x in exp if x not in obs]
    extra = [x for x in obs if x not in exp]
    set_ok = (not missing) and (not extra)
    print('  expected links : %s' % [':'.join(x) for x in exp])
    print('  observed links : %s' % [':'.join(x) for x in obs])
    print('  set match      : %s%s%s'
          % ('YES' if set_ok else 'NO',
             '' if not missing else '  MISSING=%s' % [':'.join(x) for x in missing],
             '' if not extra else '  UNEXPECTED=%s' % [':'.join(x) for x in extra]))
    print('')

    hard_fail = []
    if not set_ok:
        hard_fail.append('link identity mismatch')

    # ---- STEP 2: per-link Dmax and core_hi, from REAL packet_bytes -------
    print('-' * 78)
    print('PER-LINK BOUNDARY MODEL (Dmax derived from real packet_bytes)')
    print('-' * 78)
    core_hi = {}
    dmax = {}
    for k in obs:
        sizes = [int(r['size_bytes']) for r in groups[k]
                 if r['event'] == 'TX_BEGIN' and r['size_bytes'] != '']
        if not sizes:
            sizes = [int(r['size_bytes']) for r in groups[k]
                     if r['size_bytes'] != '']
        mx = max(sizes) if sizes else 0
        dm = D(mx, C)
        dmax[k] = dm
        ch = min(t_qlen, t_stop - dm)
        core_hi[k] = ch
        print('  link %s (node=%s if=%s)' % k)
        print('    C_l                = %.4f Gbps  <- argv capacity' % (C / 1e9))
        print('    max packet_bytes   = %d B        <- max over this link\'s '
              'TX_BEGIN rows' % mx)
        print('    tick               = %d ns' % TICK_NS)
        print('    exact  %d*8/C      = %.4f ns' % (mx, mx * 8.0 / C * 1e9))
        print('    Dmax_l (truncated) = %d ns' % dm)
        print('    core_hi_l = min(T_qlen, T_stop - Dmax_l)'
              ' = min(%d, %d) = %d' % (t_qlen, t_stop - dm, ch))
        if ch == t_qlen:
            print('      (T_qlen is the binding limit; no extra Dmax subtracted)')
        else:
            print('      (T_stop - Dmax is binding; T_qlen was at/after stop)')
    print('')

    # ---- STEP 3: unmatched classification with the six conditions -------
    print('-' * 78)
    print('SIMULATION_END_CLIPPED LEDGER')
    print('-' * 78)
    clipped = {}
    for k in obs:
        beg = {}
        end = {}
        dup_b = 0
        dup_e = 0
        for r in groups[k]:
            uid = r['packet_uid']
            t = int(r['time_ns'])
            sz = int(r['size_bytes']) if r['size_bytes'] != '' else 0
            if r['event'] == 'TX_BEGIN':
                if uid in beg:
                    dup_b += 1
                beg[uid] = (t, sz)
            elif r['event'] == 'TX_END':
                if uid in end:
                    dup_e += 1
                end[uid] = (t, sz)
        ub = [(t, uid, sz) for uid, (t, sz) in beg.items() if uid not in end]
        ue = [(t, uid, sz) for uid, (t, sz) in end.items() if uid not in beg]
        ch = core_hi[k]

        # condition set for a legitimate simulation-end clip
        cl = []
        for (t, uid, sz) in ub:
            exp_end = t + D(sz, C)
            c1 = ch <= t < t_stop
            c2 = exp_end >= t_stop
            if c1 and c2:
                cl.append((t, uid, sz, exp_end))
        bad_b = [x for x in ub if x not in
                 [(t, uid, sz) for (t, uid, sz, _) in cl]]

        ok = True
        if len(cl) > 1:
            print('  link %s: HARD FAIL -- %d trailing unmatched BEGIN '
                  '(max 1)' % (k[0], len(cl)))
            hard_fail.append('link %s: %d clipped BEGIN' % (k[0], len(cl)))
            ok = False
        for (t, uid, sz) in bad_b:
            exp_end = t + D(sz, C)
            why = ('inside core (begin < core_hi)' if t < ch
                   else 'expected_end %d < T_stop %d' % (exp_end, t_stop))
            print('  link %s: HARD FAIL -- unmatched BEGIN uid=%s t=%d: %s'
                  % (k[0], uid, t, why))
            hard_fail.append('link %s: illegal unmatched BEGIN uid=%s'
                             % (k[0], uid))
            ok = False
        ue_core = [x for x in ue if x[0] >= core_lo and x[0] <= ch]
        if ue_core:
            print('  link %s: HARD FAIL -- %d unmatched END inside core'
                  % (k[0], len(ue_core)))
            hard_fail.append('link %s: unmatched END in core' % k[0])
            ok = False
        if dup_b or dup_e:
            print('  link %s: HARD FAIL -- duplicate BEGIN=%d END=%d'
                  % (k[0], dup_b, dup_e))
            hard_fail.append('link %s: duplicate events' % k[0])
            ok = False

        for (t, uid, sz, exp_end) in cl:
            print('  link %s (node=%s if=%s): SIMULATION_END_CLIPPED' % k)
            print('    uid            = %s' % uid)
            print('    packet_bytes   = %d B' % sz)
            print('    TX_BEGIN       = %d ns' % t)
            print('    expected END   = %d ns  (= BEGIN + D(%d,C)=%d)'
                  % (exp_end, sz, D(sz, C)))
            print('    T_stop         = %d ns' % t_stop)
            print('    overshoot      = %d ns past stop' % (exp_end - t_stop))
            print('    core_hi_l      = %d ns  (BEGIN is at/after it: %s)'
                  % (ch, 'yes' if t >= ch else 'NO'))
            print('    excluded from  : core pairing, work/span, service '
                  'curve, busy-period utilisation, capacity verdict')
            print('    reason         : TX_END cannot occur -- simulator '
                  'stopped before serialization completes')
        clipped[k] = cl
        # leading unmatched END (BEGIN predates the trace) is reported by v4
        if ue and not ue_core:
            print('  link %s: %d leading unmatched END (BOUNDARY_CLIPPED, '
                  'pre-trace)' % (k[0], len(ue)))
    print('')

    # ---- STEP 4: per-link R-1a/b/c on the CORE subset -------------------
    per_link = {}
    for k in obs:
        ch = core_hi[k]
        clip_uids = set(uid for (_, uid, _, _) in clipped.get(k, []))
        # Drop only the clipped BEGIN rows; never delete or fabricate a TX_END.
        rs = [r for r in groups[k] if r['packet_uid'] not in clip_uids]
        print('-' * 78)
        print('LINK %s (node=%s if=%s)  rows=%d (excluded %d clipped BEGIN)  '
              'core=[%d, %d]' % (k[0], k[1], k[2], len(rs),
                                 len(groups[k]) - len(rs), core_lo, ch))
        print('-' * 78)
        g, o = V4.analyse(rs, C, core_lo, ch, '%s link %s' % (label, k[0]),
                          verbose=True)
        nf = V4.emit('%s -- LINK %s' % (label, k[0]), C, g, o)
        per_link[k] = (len(g) - nf, len(g), nf)
        print('')

    # ---- verdict --------------------------------------------------------
    print('=' * 78)
    print('MULTI-LINK v2 VERDICT')
    print('=' * 78)
    all_pass = set_ok and len(obs) > 0 and not hard_fail
    for k in obs:
        p, t, f = per_link[k]
        print('  link %s (node=%s if=%s): %d/%d gates, clipped=%d'
              % (k[0], k[1], k[2], p, t, len(clipped.get(k, []))))
        if f:
            all_pass = False
    for k in missing:
        print('  link %s: NO DATA -- expected but never observed' % ':'.join(k))
        all_pass = False
    print('')
    print('  expected links covered : %d/%d' % (len(exp) - len(missing), len(exp)))
    print('  SIMULATION_END_CLIPPED : %s'
          % dict((k[0], len(v)) for k, v in clipped.items()))
    print('  core_hi per link       : %s'
          % dict((k[0], core_hi[k]) for k in obs))
    print('  Dmax per link          : %s'
          % dict((k[0], dmax[k]) for k in obs))
    if hard_fail:
        print('  HARD FAILURES          : %s' % hard_fail)
    print('  OVERALL R-1a/b/c       : %s' % ('PASS' if all_pass else 'FAIL'))
    if not all_pass:
        print('')
        print('  A single link passing does NOT represent the scenario.')
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
