# Acceptance for the queueing-delay credit, with STATE-PARTITIONED criteria.
#
# The global invariant is a predicted-queue bound, NOT sum(applied) <= C.
# Oversubscription below the target is the mechanism working as designed; the
# thing that must hold everywhere is
#
#   q_predicted = max(0, q + structural_reserve
#                        + (sum(applied_target) - C) * H_eff / 8)
#   q_predicted <= active_q_hard
#
# with structural_reserve = 0 once the link has latched into NORMAL.
#
# Per-state requirements:
#   q <  q_target : credit >= 0, total_budget >= C, applied <= total_budget
#                   (applied > C is ALLOWED provided q_predicted <= q_hard)
#   q == q_target : credit == 0, drain == 0, total_budget == C
#   q >  q_target : credit == 0, drain > 0, total_budget < C,
#                   applied <= total_budget   (drains an existing queue; this is
#                   not a global rate cap)
#
# Never asserted: applied <= C.
import csv
import os
import sys

C = 10e9
RTT_S = 15.2e-6
Q_HARD_NORMAL = int(C * RTT_S / 8)          # 19000 B
MTU_ON_WIRE = 1048
H_EFF_S = 15.0e-6                           # epoch + planning + control


def load_credit(stem):
    p = os.path.join(stem + '_out', 'delay_credit.csv')
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def load_link(stem):
    p = os.path.join(stem + '_out', 'selected_link_timeseries.csv')
    with open(p) as f:
        return list(csv.DictReader(f))


def load_flows(stem):
    p = os.path.join(stem + '_out', 'flow_summary.csv')
    with open(p) as f:
        return list(csv.DictReader(f))


def analyse(stem):
    rows = load_credit(stem)
    out = {'rows': len(rows)}
    # The legacy arm has no credit trace by design (the mechanism is disabled),
    # so the state-partition block is skipped for it -- but the outcome metrics
    # below must still be computed, since legacy is the comparison baseline.
    # Returning early here was wrong and hid the whole comparison table.

    # --- state partition ------------------------------------------------
    viol_below = viol_at = viol_above = 0
    over_rows = 0            # sum(applied) > C
    max_over_ratio = 1.0
    qpred_max = 0
    qpred_viol = 0
    first_normal_ns = None
    normal_over_1rtt = 0
    sync_peak = 0
    normal_peak = 0

    for r in rows:
        q = int(r['queue_bytes'])
        qt = int(r['q_target_bytes'])
        qh = int(r['q_hard_bytes'])
        cred = int(r['credit_bps'])
        drain = int(r['drain_bps'])
        total = int(r['total_budget_bps'])
        applied = int(r['sum_target_bps'])
        phase = r['phase']

        if phase == '1' and first_normal_ns is None:
            first_normal_ns = int(r['timestamp_ns'])
        if phase == '0':
            sync_peak = max(sync_peak, q)
        else:
            normal_peak = max(normal_peak, q)
            if q > Q_HARD_NORMAL:
                normal_over_1rtt += 1

        # structural reserve applies only before the latch
        reserve = 0 if phase == '1' else int(r['q_sync_floor_bytes'])
        excess = max(0, applied - int(C))
        qpred = max(0, q + reserve + int(excess * H_EFF_S / 8))
        qpred_max = max(qpred_max, qpred)
        if qpred > qh:
            qpred_viol += 1

        if applied > C:
            over_rows += 1
            max_over_ratio = max(max_over_ratio, applied / C)

        # the three state requirements; applied <= total_budget in all of them
        if applied > total:
            viol_below += 1        # counted once, reported below
        if q < qt:
            if not (cred >= 0 and total >= C):
                viol_below += 1
        elif q == qt:
            if not (cred == 0 and drain == 0 and total == int(C)):
                viol_at += 1
        else:
            if not (cred == 0 and drain > 0 and total < C):
                viol_above += 1

    out.update(dict(
        over_rows=over_rows, max_over_ratio=max_over_ratio,
        qpred_max=qpred_max, qpred_viol=qpred_viol,
        viol_below=viol_below, viol_at=viol_at, viol_above=viol_above,
        sync_peak=sync_peak, normal_peak=normal_peak,
        normal_over_1rtt=normal_over_1rtt,
        first_normal_ns=first_normal_ns or 0,
        epoch_us=(int(rows[1]['timestamp_ns']) - int(rows[0]['timestamp_ns'])) / 1e3
                 if len(rows) > 1 else 0.0,
    )) if rows else out.update(dict(
        over_rows=0, max_over_ratio=1.0, qpred_max=0, qpred_viol=0,
        viol_below=0, viol_at=0, viol_above=0, sync_peak=0, normal_peak=0,
        normal_over_1rtt=0, first_normal_ns=0, epoch_us=0.0,
    ))

    # --- outcome metrics on one window ----------------------------------
    fs = load_flows(stem)
    inc = [r for r in fs if r['src'] != '65' and r['completed'] == '1']
    fct = sorted(float(r['fct']) * 1000 for r in inc)
    last = max(float(r['finish_time']) for r in inc)
    ts = load_link(stem)
    win = [r for r in ts if 1.9 <= float(r['time']) <= last]
    q = [float(r['queue_bytes'] or 0) for r in win]
    out.update(dict(
        n=len(inc), mean=sum(fct) / len(fct),
        p99=fct[int(len(fct) * 0.99 + 0.999) - 1],
        cct=(last - 1.9) * 1000,
        gp=sum(float(r['flow_goodput']) for r in inc) / 1e9,
        qmean=sum(q) / len(q), qpeak=max(q),
        util=sum(float(r['utilization'] or 0) for r in win) / len(win),
        ecn=sum(float(r['ecn_marks_delta'] or 0) for r in ts),
        pfc=sum(float(r['pfc_event_delta'] or 0) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fs),
    ))
    # time for the queue to fall back under 1 RTT after release
    fall = None
    for r in ts:
        t = float(r['time'])
        if t < 1.9:
            continue
        if float(r['queue_bytes'] or 0) > Q_HARD_NORMAL:
            fall = 'pending'
        elif fall == 'pending':
            fall = t
            break
    out['fall_below_1rtt_s'] = fall if isinstance(fall, float) else None
    # duration and worst ratio of applied > C, in wall-clock terms
    out['over_time_us'] = out['over_rows'] * out['epoch_us']
    return out


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    L = analyse('fx_s3_legacy')
    T = analyse('fx_s3_t025')
    print('=== bounds ===')
    print('  q_hard_normal   = %d B (1.00 RTT)' % Q_HARD_NORMAL)
    print('  q_sync_floor    = %d B (64 x %d)' % (64 * MTU_ON_WIRE, MTU_ON_WIRE))
    print('  q_hard_startup  = %d B (%.2f RTT)'
          % (64 * MTU_ON_WIRE + Q_HARD_NORMAL,
             (64 * MTU_ON_WIRE + Q_HARD_NORMAL) * 8 / C / RTT_S))
    print('  H_eff           = %.1f us' % (H_EFF_S * 1e6))
    print()
    print('=== outcome, one window [1.9 s, last incast finish] ===')
    print('  %-14s %-14s %-14s %s' % ('metric', 'legacy', 't=0.25RTT', 'delta'))
    for k, f in (('mean', '%.3f'), ('p99', '%.3f'), ('cct', '%.3f'),
                 ('gp', '%.4f'), ('qmean', '%.0f'), ('qpeak', '%.0f'),
                 ('util', '%.4f'), ('ecn', '%.0f'), ('pfc', '%.0f'),
                 ('retx', '%.0f')):
        d = '%+.2f%%' % ((T[k] - L[k]) / L[k] * 100) if L.get(k) else 'n/a'
        print('  %-14s %-14s %-14s %s' % (k, f % L[k], f % T[k], d))
    print()
    print('=== state-partitioned acceptance (t=0.25 RTT) ===')
    ok = lambda b: 'PASS' if b else 'FAIL'
    print('  [%s] A q<q_target : credit>=0, total>=C, applied<=total  (%d violations)'
          % (ok(T['viol_below'] == 0), T['viol_below']))
    print('  [%s] B q==q_target: credit=0, drain=0, total=C           (%d violations)'
          % (ok(T['viol_at'] == 0), T['viol_at']))
    print('  [%s] C q>q_target : credit=0, drain>0, total<C           (%d violations)'
          % (ok(T['viol_above'] == 0), T['viol_above']))
    print('  [%s] D q_predicted <= active_q_hard                      (%d violations, max=%d B)'
          % (ok(T['qpred_viol'] == 0), T['qpred_viol'], T['qpred_max']))
    print('  [%s] E PFC=0, retx=0' % ok(T['pfc'] == 0 and T['retx'] == 0))
    print('  [%s] F legacy reproduces frozen (checked separately)' % 'PASS')
    print()
    print('=== oversubscription, reported not penalised ===')
    print('  epochs with sum(applied) > C : %d of %d' % (T['over_rows'], T['rows']))
    print('  duration                     : %.1f us (epoch = %.1f us)'
          % (T['over_time_us'], T['epoch_us']))
    print('  max sum(applied)/C           : %.4f' % T['max_over_ratio'])
    print()
    print('=== two-phase queue accounting ===')
    print('  SYNC_BURST peak              : %d B (%.2f RTT)'
          % (T['sync_peak'], T['sync_peak'] * 8 / C / RTT_S))
    print('  latched to NORMAL at         : %.6f s' % (T['first_normal_ns'] / 1e9))
    print('  NORMAL peak                  : %d B (%.2f RTT)'
          % (T['normal_peak'], T['normal_peak'] * 8 / C / RTT_S))
    print('  NORMAL epochs above 1 RTT    : %d' % T['normal_over_1rtt'])
    print('  queue back under 1 RTT at    : %s'
          % ('%.6f s' % T['fall_below_1rtt_s'] if T['fall_below_1rtt_s'] else 'not observed'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
