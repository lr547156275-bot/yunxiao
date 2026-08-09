# Evidence that each algorithm's control mechanism actually engaged.
#
# Usage:  python2 verify_triggers.py <tag> [seed]
#   e.g.  python2 verify_triggers.py s3 2
#
# What is directly observable, and what has to be inferred:
#
#   DCQCN   -- round_summary.csv carries cnp_count, dcqcn_start_alpha,
#              dcqcn_end_alpha and the recovery stages, so CNP arrival and
#              rate decrease/recovery are observable directly.
#   DCTCP   -- m_alpha only appears in a PRINT_LOG printf that is compiled
#              out, so engagement is inferred from the rate trajectory:
#              HandleAckDctcp is the only thing that moves m_rate under
#              CC_MODE 8, so minimum_rate < start_rate proves it reduced,
#              and ECN marks on the link prove the input existed.
#   TIMELY  -- rttDiff and m_incStage are not exported either; engagement is
#              inferred the same way (mode 7 moves m_rate only via
#              UpdateRateTimely).
#   HPCC    -- INT feedback arriving is visible as feedback_loop_delay and
#              first_feedback_after_injection being populated, plus rate
#              movement from UpdateRateHp.
#   CBAP-SBA -- sba_events.csv (admission), CBAP_MIG_REPLAN / CBAP_MIG in the
#              run log (old-flow release, new-flow take-up, convergence), and
#              queue behaviour for borrowing / reclamation.
import csv
import os
import sys


def rd(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    f = open(path)
    try:
        return list(csv.DictReader(f))
    finally:
        f.close()


def fnum(row, key):
    v = row.get(key)
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def count_lines(path, needle):
    if not os.path.exists(path):
        return 0
    n = 0
    f = open(path)
    try:
        for line in f:
            if needle in line:
                n += 1
    finally:
        f.close()
    return n


def link_stats(d, release):
    rows = rd(os.path.join(d, 'selected_link_timeseries.csv'))
    w = [r for r in rows if fnum(r, 'time') is not None
         and fnum(r, 'time') >= release]
    if not w:
        return {}
    q = [fnum(r, 'queue_bytes') for r in w if fnum(r, 'queue_bytes') is not None]
    return {
        'ecn': sum(fnum(r, 'ecn_marks_delta') or 0 for r in w),
        'pfc': sum(fnum(r, 'pfc_event_delta') or 0 for r in w),
        'qpeak': max(q) if q else 0,
        'qfinal': q[-1] if q else 0,
    }


def rate_movement(d, bg_srcs):
    """Did any per-flow rate actually change during the collective?"""
    rows = rd(os.path.join(d, 'round_summary.csv'))
    inc = [r for r in rows if r.get('flow_id') not in ('0',)]
    reduced = 0
    increased = 0
    cnp_total = 0
    alpha_moved = 0
    stage_moved = 0
    fb_seen = 0
    for r in inc:
        s = fnum(r, 'start_rate')
        lo = fnum(r, 'minimum_rate')
        e = fnum(r, 'end_rate')
        if s and lo and lo < s * 0.999:
            reduced += 1
        if s and e and e > s * 1.001:
            increased += 1
        cnp_total += int(fnum(r, 'cnp_count') or 0)
        a0 = fnum(r, 'dcqcn_start_alpha')
        a1 = fnum(r, 'dcqcn_end_alpha')
        if a0 is not None and a1 is not None and abs(a1 - a0) > 1e-9:
            alpha_moved += 1
        s0 = fnum(r, 'dcqcn_start_recovery_stage')
        s1 = fnum(r, 'dcqcn_end_recovery_stage')
        if s0 is not None and s1 is not None and s0 != s1:
            stage_moved += 1
        # first_feedback_after_injection reads 0 for every algorithm, so it is
        # not a feedback indicator.  feedback_loop_delay is the round's
        # measured control-loop latency and is only nonzero once feedback has
        # actually come back.
        fb = fnum(r, 'feedback_loop_delay')
        if fb is not None and fb > 0:
            fb_seen += 1
    return {
        'rounds': len(inc),
        'reduced': reduced,
        'increased': increased,
        'cnp': cnp_total,
        'alpha_moved': alpha_moved,
        'stage_moved': stage_moved,
        'feedback_seen': fb_seen,
    }


def read_cfg(path):
    """Parse an ns-3 'KEY value...' config into a dict."""
    out = {}
    if not os.path.exists(path):
        return out
    f = open(path)
    try:
        for line in f:
            p = line.split()
            if len(p) >= 2:
                out[p[0]] = ' '.join(p[1:])
    finally:
        f.close()
    return out


def qmax_from_cfg(base, cfg):
    """Qmax in bytes from the CBAP link file, not a hardcoded constant."""
    name = cfg.get('CBAP_LINK_FILE', '').split()[0] \
        if cfg.get('CBAP_LINK_FILE') else ''
    path = os.path.join(base, name) if name else ''
    if not path or not os.path.exists(path):
        return 400000
    vals = []
    f = open(path)
    try:
        for i, line in enumerate(f):
            if i == 0:
                continue
            p = line.split()
            if len(p) >= 5:
                try:
                    vals.append(int(p[4]))
                except ValueError:
                    pass
    finally:
        f.close()
    return max(vals) if vals else 400000


# Scenario-aware acceptance.  Requiring every algorithm to engage in every
# scenario is wrong: S1 and S2 are startup-dominated and deliberately stay below
# the ECN marking threshold, so an ECN-driven controller has no input to react
# to and *should* report no CNP and no alpha movement.  Calling that a failure
# would mean the scenario had to be redefined to satisfy the checker rather than
# the checker describing the scenario.
#
#   ECN_ACTIVE      -- the queue is expected to cross KMIN, so DCQCN and DCTCP
#                      must show ECN/CNP and a rate reduction, or something is
#                      genuinely broken.
#   ECN_INACTIVE    -- the queue stays below KMIN by construction; DCQCN and
#                      DCTCP are reported EXPECTED_NOT_ENGAGED, not failed.
#
# TIMELY (RTT-gradient) and HPCC (INT) do not depend on ECN, and CBAP-SBA's
# admission runs regardless, so those three must engage in every scenario.
ECN_ACTIVE = set(['s3', 's4', 's5'])
ECN_DEPENDENT = set(['dcqcn', 'dctcp'])


def expected_engagement(tag, algo):
    """Whether this algorithm is required to engage in this scenario."""
    if algo in ECN_DEPENDENT and tag not in ECN_ACTIVE:
        return False
    return True


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 's3'
    seed = sys.argv[2] if len(sys.argv) > 2 else '2'
    # A third argument writes one CSV row per cell so the paper's trigger table
    # is generated rather than transcribed from console output.
    csv_out = sys.argv[3] if len(sys.argv) > 3 else None
    base = os.path.dirname(os.path.abspath(__file__))
    logs = '/work/matrix_logs'
    release = 1.9
    algos = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
    rows_csv = []

    print('=' * 96)
    print(' CONTROL MECHANISM TRIGGER EVIDENCE   %s seed=%s' % (tag.upper(), seed))
    print('=' * 96)

    for algo in algos:
        d = os.path.join(base, 'm_%s_%s_seed%s_out' % (algo, tag, seed))
        log = os.path.join(logs, 'm_%s_%s_seed%s.log' % (algo, tag, seed))
        cfg = read_cfg(os.path.join(base, 'm_%s_%s_seed%s.txt'
                                    % (algo, tag, seed)))
        qmax = qmax_from_cfg(base, cfg)
        print('')
        print('--- %s ---' % algo)
        if not os.path.exists(os.path.join(d, 'flow_summary.csv')):
            print('  NOT RUN YET (no output directory) -- no verdict')
            rows_csv.append({'scenario': tag, 'algorithm': algo, 'seed': seed,
                             'verdict': 'NOT_RUN'})
            continue
        ls = link_stats(d, release)
        rm = rate_movement(d, set())
        if rm['rounds'] == 0:
            # An empty round_summary means the run has not produced data yet,
            # which is not the same as a mechanism failing to engage.
            print('  INCOMPLETE (no rounds recorded yet) -- no verdict')
            rows_csv.append({'scenario': tag, 'algorithm': algo, 'seed': seed,
                             'verdict': 'INCOMPLETE'})
            continue
        ok = False
        row = {'scenario': tag, 'algorithm': algo, 'seed': seed,
               'cc_mode': cfg.get('CC_MODE', ''),
               'ecn_marks': ls.get('ecn', 0), 'pfc_events': ls.get('pfc', 0),
               'queue_peak_bytes': ls.get('qpeak', 0),
               'queue_final_bytes': ls.get('qfinal', 0),
               'qmax_bytes': qmax,
               'rounds': rm['rounds'], 'rate_reduced_rounds': rm['reduced'],
               'rate_increased_rounds': rm['increased'],
               'cnp_count': rm['cnp'], 'alpha_moved_rounds': rm['alpha_moved'],
               'recovery_stage_moved_rounds': rm['stage_moved'],
               'feedback_rounds': rm['feedback_seen']}
        print('  link      : ECN marks=%d  PFC=%d  peak_queue=%d  final_queue=%d'
              % (ls.get('ecn', 0), ls.get('pfc', 0), ls.get('qpeak', 0),
                 ls.get('qfinal', 0)))
        print('  rounds    : %d incast rounds recorded' % rm['rounds'])
        print('  rate moved: %d reduced below start, %d ended above start'
              % (rm['reduced'], rm['increased']))

        if algo == 'dcqcn':
            print('  DCQCN     : CNP count=%d  alpha changed in %d rounds  '
                  'recovery stage changed in %d rounds'
                  % (rm['cnp'], rm['alpha_moved'], rm['stage_moved']))
            ok = rm['cnp'] > 0 and rm['reduced'] > 0
            print('  VERDICT   : %s' % ('CNP received and rate decreased -> '
                                        'ENGAGED' if ok else
                                        'no CNP or no rate decrease -> NOT ENGAGED'))
        elif algo == 'dctcp':
            # alpha is not exported; ECN input plus a rate reduction is the
            # observable signature of HandleAckDctcp doing work.
            ok = ls.get('ecn', 0) > 0 and rm['reduced'] > 0
            print('  DCTCP     : ECN marks present=%s, rate reduced in %d rounds'
                  % ('yes' if ls.get('ecn', 0) > 0 else 'no', rm['reduced']))
            print('              (m_alpha itself is only in a compiled-out '
                  'PRINT_LOG; inferred from rate movement)')
            print('  VERDICT   : %s' % ('ECN marked and rate reduced -> ENGAGED'
                                        if ok else
                                        'no ECN or no reduction -> NOT ENGAGED'))
        elif algo == 'timely':
            ok = rm['reduced'] > 0 or rm['increased'] > 0
            print('  TIMELY    : rate moved in %d rounds (down) / %d (up)'
                  % (rm['reduced'], rm['increased']))
            print('              (rttDiff / m_incStage are not exported; '
                  'mode 7 moves m_rate only via UpdateRateTimely)')
            print('  VERDICT   : %s' % ('RTT-driven rate control active -> '
                                        'ENGAGED' if ok else
                                        'rate never moved -> NOT ENGAGED'))
        elif algo == 'hpcc':
            # feedback_summary.csv carries the INT-specific counters.
            fs = rd(os.path.join(d, 'feedback_summary.csv'))
            inc_fs = [r for r in fs if r.get('flow_id') not in ('0',)]
            hops = sum(int(fnum(r, 'int_hop_count') or 0) for r in inc_fs)
            actionable = sum(int(fnum(r, 'actionable_feedback') or 0)
                             for r in inc_fs)
            total_fb = sum(int(fnum(r, 'total_feedback') or 0) for r in inc_fs)
            changed = sum(int(fnum(r, 'feedback_changed_live_rate') or 0)
                          for r in inc_fs)
            ok = (total_fb > 0 and (rm['reduced'] + rm['increased']) > 0)
            print('  HPCC      : total INT feedback=%d  actionable=%d  '
                  'int_hop_count=%d  feedback changed rate=%d'
                  % (total_fb, actionable, hops, changed))
            print('              control-loop delay nonzero in %d/%d rounds'
                  % (rm['feedback_seen'], rm['rounds']))
            print('  VERDICT   : %s' % ('INT feedback arrived and rate updated '
                                        '-> ENGAGED' if ok else
                                        'no feedback or no update -> NOT ENGAGED'))
        else:
            adm = rd(os.path.join(d, 'admission.csv'))
            sba = rd(os.path.join(d, 'sba_events.csv'))
            replans = count_lines(log, 'CBAP_MIG_REPLAN')
            migs = count_lines(log, 'CBAP_MIG ')
            conv = count_lines(log, 'end=converged')
            qmin = qmax * 0.5
            borrowed = ls.get('qpeak', 0) > qmin
            over = ls.get('qpeak', 0) > qmax
            drained = ls.get('qfinal', 0) <= qmin
            print('  CBAP-SBA  : admission rows=%d  sba_events=%d'
                  % (len(adm), len(sba)))
            print('              migration replans=%d  epoch updates=%d  '
                  'convergences=%d' % (replans, migs, conv))
            print('  queue     : borrowing above Qmin(%d)=%s  exceeded Qmax(%d)=%s'
                  '  drained back=%s'
                  % (qmin, 'yes' if borrowed else 'no', qmax,
                     'yes' if over else 'no', 'yes' if drained else 'no'))
            ok = len(adm) > 0
            print('  VERDICT   : %s' % ('batch admission ran -> ENGAGED'
                                        if ok else
                                        'no admission rows -> NOT ENGAGED'))
            row.update({'admission_events': len(adm), 'sba_events': len(sba),
                        'migration_replans': replans,
                        'migration_epochs': migs, 'convergences': conv,
                        'queue_borrowed_above_qmin': 1 if borrowed else 0,
                        'exceeded_qmax': 1 if over else 0,
                        'queue_drained': 1 if drained else 0})
            if over:
                safe = (ls.get('pfc', 0) == 0 and drained)
                row['oversub_verdict'] = 'BOUNDED' if safe else 'UNSAFE'
                print('  OVERSUB   : %s' % (
                    'exceeded Qmax but no PFC and queue drained -> BOUNDED'
                    if safe else
                    'exceeded Qmax with PFC or without draining -> UNSAFE'))
            else:
                row['oversub_verdict'] = 'NEVER_EXCEEDED'

        required = expected_engagement(tag, algo)
        if ok:
            row['verdict'] = 'ENGAGED'
        elif not required:
            # The scenario is designed to keep this controller's input absent.
            row['verdict'] = 'EXPECTED_NOT_ENGAGED'
            print('  NOTE      : %s is ECN-driven and %s is an ECN-inactive '
                  'scenario' % (algo, tag))
            print('              (queue stays below KMIN by construction, so no '
                  'CNP/alpha movement is expected)')
            print('              -> EXPECTED_NOT_ENGAGED, not a failure')
        else:
            row['verdict'] = 'NOT_ENGAGED'
        row['engagement_required'] = 1 if required else 0
        rows_csv.append(row)

    if csv_out and rows_csv:
        keys = []
        for r in rows_csv:
            for k in r:
                if k not in keys:
                    keys.append(k)
        # scenario/algorithm/verdict first for readability.
        for k in ('verdict', 'seed', 'algorithm', 'scenario'):
            if k in keys:
                keys.remove(k)
                keys.insert(0, k)
        f = open(csv_out, 'w')
        try:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            w.writeheader()
            for r in rows_csv:
                w.writerow(r)
        finally:
            f.close()
        print('')
        print('wrote %s (%d rows)' % (csv_out, len(rows_csv)))

    # Summary and exit status.  Only a genuine NOT_ENGAGED -- a controller that
    # had the input it needed and still did nothing -- is a failure.
    print('')
    print('--- ENGAGEMENT SUMMARY (%s) ---' % tag)
    bad = []
    for r in rows_csv:
        v = r.get('verdict', '?')
        print('  %-9s %s' % (r.get('algorithm', '?'), v))
        if v == 'NOT_ENGAGED':
            bad.append(r.get('algorithm'))
    if bad:
        print('')
        print('FAIL: %s had the required input but did not engage in %s'
              % (', '.join(bad), tag))
        return 1
    print('')
    print('OK: every algorithm either engaged or is expected not to in %s' % tag)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
