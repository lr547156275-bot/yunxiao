# -*- coding: utf-8 -*-
# Per-cell metric extraction for the Pareto sweep.  Writes results.csv.
#
# Definitions fixed by earlier corrections in this project:
#   * flow_summary 'fct' is in SECONDS
#   * BCT = max(finish) - min(start) over COMPLETED incast flows
#   * CCT = max(finish) - min(application_ready) from admission.csv (batch != 0);
#           falls back to BCT when there is no admission record (DCQCN/HPCC)
#   * batch goodput = 8 * sum(bytes) / BCT     (NOT the sum of per-flow rates)
#   * utilisation = busy / BACKLOGGED window (the batch), not the whole run
#   * queue comes from selected_link_timeseries.csv, which every arm writes
import csv
import hashlib
import os
import sys

B = '/work/simulation/experiment/scheme1_sba'
C = 10e9
Q_ABS = 1048575          # 838.86 us * C / 8
M_SAFE = 67072
Q_HIGH = Q_ABS - M_SAFE  # 981503
OUT = os.path.join(B, 'pareto_results.csv')


def pctl(v, q):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, int(q * (len(s) - 1)))]


def sha(p):
    if not os.path.isfile(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()[:16]


def cfgval(cfg, key):
    if not os.path.isfile(cfg):
        return None
    for ln in open(cfg):
        w = ln.split()
        if len(w) >= 2 and w[0] == key:
            return w[1]
    return None


def flows(d):
    p = os.path.join(d, 'flow_summary.csv')
    if not os.path.isfile(p):
        return None
    inc, bg = [], []
    for r in csv.DictReader(open(p)):
        try:
            sz = int(float(r['total_size_bytes']))
        except (KeyError, ValueError):
            continue
        def f(k):
            try:
                return float(r[k])
            except (KeyError, ValueError, TypeError):
                return None
        rec = dict(sz=sz, fct=f('fct'), st=f('start_time'), fin=f('finish_time'),
                   ak=f('acked_bytes') or 0.0, gp=f('flow_goodput') or 0.0,
                   dn=str(r.get('completed', '0')).strip() not in ('0', 'false', ''),
                   rx=int(float(r.get('retx_events') or 0)))
        (bg if sz >= (1 << 30) else inc).append(rec)
    done = [x for x in inc if x['dn'] and x['fct'] is not None]
    if not done:
        return None
    t0 = min(x['st'] for x in done if x['st'] is not None)
    t1 = max(x['fin'] for x in done if x['fin'] is not None)
    bct = t1 - t0
    tb = sum(x['sz'] for x in done)
    fv = sorted(x['fct'] for x in done)
    return dict(n_inc=len(inc), done=len(done), t0=t0, t1=t1, bct=bct,
                bytes=tb, gp=8.0 * tb / bct if bct > 0 else 0.0,
                fct_mean=sum(fv) / len(fv), fct_p95=pctl(fv, .95),
                fct_p99=pctl(fv, .99), fct_max=fv[-1],
                fct_spread=fv[-1] - fv[0],
                retx=sum(x['rx'] for x in inc) + sum(x['rx'] for x in bg),
                bg_ak=(bg[0]['ak'] if bg else None),
                bg_dn=(bg[0]['dn'] if bg else None),
                bg_fct=(bg[0]['fct'] if bg and bg[0]['dn'] else None))


def cct_start(d, fallback):
    p = os.path.join(d, 'admission.csv')
    if not os.path.isfile(p):
        return fallback
    best = None
    for r in csv.DictReader(open(p)):
        if str(r.get('batch_id')) == '0':
            continue                      # batch 0 is the background flow
        try:
            v = float(r['application_ready_ns']) / 1e9
        except (KeyError, ValueError):
            continue
        best = v if best is None else min(best, v)
    return best if best is not None else fallback


def busy(d, lo, hi):
    p = os.path.join(d, 'tx_serialization.csv')
    if not os.path.isfile(p):
        return None
    beg, pr = {}, []
    for r in csv.DictReader(open(p)):
        k = (r['node_id'], r['if_index'], r['packet_uid'])
        t = int(r['time_ns'])
        if r['event'] == 'TX_BEGIN':
            beg[k] = (t, int(r['packet_bytes']))
        elif r['event'] == 'TX_END' and k in beg:
            b, nb = beg.pop(k)
            pr.append((b, t, nb))
    pr = sorted(x for x in pr if x[0] >= lo and x[1] <= hi)
    if not pr:
        return None
    bs, g, cs, ce = 0, [], pr[0][0], pr[0][1]
    for (s, e, nb) in pr[1:]:
        if s > ce:
            bs += ce - cs
            g.append(s - ce)
            cs = s
        ce = max(ce, e)
    bs += ce - cs
    span = pr[-1][1] - pr[0][0]
    return dict(util=bs / float(span) if span else None,
                wire=sum(x[2] for x in pr) * 8.0 / (span / 1e9),
                ngap=len(g), gtot=sum(g), gmax=max(g) if g else 0,
                g50=pctl(g, .5), g99=pctl(g, .99))


def queue(d, sample_us):
    p = os.path.join(d, 'selected_link_timeseries.csv')
    if not os.path.isfile(p):
        return None
    v = []
    for r in csv.DictReader(open(p)):
        try:
            v.append(float(r['queue_bytes']))
        except (KeyError, ValueError):
            pass
    if not v:
        return None
    over = [x for x in v if x > Q_HIGH]
    run = best = 0
    for x in v:
        run = run + 1 if x > Q_HIGH else 0
        best = max(best, run)
    return dict(mean=sum(v) / len(v), p95=pctl(v, .95), p99=pctl(v, .99),
                max=max(v), n=len(v),
                over_n=len(over), over_us=len(over) * sample_us,
                over_run_us=best * sample_us)


def rates(d):
    p = os.path.join(d, 'applied_rate_audit.csv')
    if not os.path.isfile(p):
        return None
    rs = [r for r in csv.DictReader(open(p))]
    def m(k):
        v = []
        for r in rs:
            try:
                v.append(float(r[k]))
            except (KeyError, ValueError, TypeError):
                pass
        return pctl(v, .5)
    return dict(target=m('planner_target_sum_bps'),
                applied=m('applied_rate_sum_bps'),
                budget=m('input_budget_bps'),
                unalloc=m('full_unallocated_bps'), epochs=len(rs))


def pfc(d):
    p = os.path.join(d, 'pfc_events.csv')
    return max(0, sum(1 for _ in open(p)) - 1) if os.path.isfile(p) else 0


def drops(tag):
    p = '/tmp/pa_%s.txt' % tag
    if not os.path.isfile(p):
        return 0
    return sum(1 for ln in open(p) if 'Drop:' in ln)


rows = []
for dn in sorted(os.listdir(B)):
    if not (dn.startswith('pa_') and dn.endswith('_out')):
        continue
    d = os.path.join(B, dn)
    if not os.path.isfile(os.path.join(d, 'DONE')):
        print('SKIP %s (no DONE)' % dn)
        continue
    tag = dn[3:-4]
    cfg = os.path.join(B, 'pa_%s.txt' % tag)
    f = flows(d)
    if not f:
        print('SKIP %s (no usable flow_summary)' % dn)
        continue
    su = float(cfgval(cfg, 'CRFM_TRACE_SAMPLE_US') or 10)
    bu = busy(d, int(f['t0'] * 1e9), int(f['t1'] * 1e9))
    q = queue(d, su)
    ra = rates(d)
    p = pfc(d)
    dr = drops(tag)
    wire = bu['wire'] if bu else None
    row = dict(
        cell=tag,
        cc_mode=cfgval(cfg, 'CC_MODE'),
        cbap=cfgval(cfg, 'CBAP_ENABLE'),
        rho=cfgval(cfg, 'CBAP_RHO'),
        cap_frac=cfgval(cfg, 'CBAP_STEADY_CAP_FRACTION') or '-',
        max_boost=cfgval(cfg, 'CBAP_QC_MAX_BOOST_RATIO'),
        phase=cfgval(cfg, 'CBAP_PHASE_SPREAD_ENABLE') or '0',
        steady_cap=cfgval(cfg, 'CBAP_STEADY_CAP_ENABLE') or '0',
        completed=f['done'], n_incast=f['n_inc'],
        cct_ms=1e3 * (f['t1'] - cct_start(d, f['t0'])),
        bct_ms=1e3 * f['bct'],
        batch_goodput_gbps=f['gp'] / 1e9,
        fct_mean_us=1e6 * f['fct_mean'], fct_p95_us=1e6 * f['fct_p95'],
        fct_p99_us=1e6 * f['fct_p99'], fct_spread_us=1e6 * f['fct_spread'],
        bg_acked_mb=(f['bg_ak'] / 1e6) if f['bg_ak'] else None,
        bg_completed=f['bg_dn'],
        bg_fct_ms=(1e3 * f['bg_fct']) if f['bg_fct'] else None,
        utilisation=bu['util'] if bu else None,
        wire_rate_gbps=(wire / 1e9) if wire else None,
        gap_count=bu['ngap'] if bu else None,
        gap_total_us=(bu['gtot'] / 1e3) if bu else None,
        gap_p50_ns=bu['g50'] if bu else None,
        gap_max_ns=bu['gmax'] if bu else None,
        q_mean_b=q['mean'] if q else None, q_p95_b=q['p95'] if q else None,
        q_p99_b=q['p99'] if q else None, q_max_b=q['max'] if q else None,
        qdelay_mean_us=(q['mean'] * 8 / C * 1e6) if q else None,
        qdelay_p99_us=(q['p99'] * 8 / C * 1e6) if q else None,
        qdelay_max_us=(q['max'] * 8 / C * 1e6) if q else None,
        over_qhigh_samples=q['over_n'] if q else None,
        over_qhigh_us=q['over_us'] if q else None,
        over_qhigh_longest_us=q['over_run_us'] if q else None,
        target_gbps=(ra['target'] / 1e9) if ra and ra['target'] else None,
        applied_gbps=(ra['applied'] / 1e9) if ra and ra['applied'] else None,
        budget_gbps=(ra['budget'] / 1e9) if ra and ra['budget'] else None,
        unalloc_gbps=(ra['unalloc'] / 1e9) if ra and ra['unalloc'] else None,
        pfc=p, drops=dr, retx=f['retx'],
        sha_config=sha(cfg),
        sha_flow=sha(os.path.join(B, 's3_flow.txt')),
        sha_link=sha(os.path.join(B, 's3_cbap_link.txt')),
        sha_path=sha(os.path.join(B, 's3_cbap_path.txt')),
        sha_binary=sha('/work/simulation/build/scratch/third'),
        sha_lib=sha('/work/simulation/build/libns3.18-point-to-point-debug.so'))
    # three-stage loss, all in Gbps
    if row['target_gbps'] and row['applied_gbps']:
        row['loss_target_to_applied_gbps'] = row['target_gbps'] - row['applied_gbps']
    else:
        row['loss_target_to_applied_gbps'] = None
    if row['applied_gbps'] and row['wire_rate_gbps']:
        row['loss_applied_to_wire_gbps'] = row['applied_gbps'] - row['wire_rate_gbps']
    else:
        row['loss_applied_to_wire_gbps'] = None
    rows.append(row)

if not rows:
    print('no completed cells')
    sys.exit(1)
keys = list(rows[0].keys())
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('wrote %s  (%d cells)' % (OUT, len(rows)))
for r in rows:
    print('  %-24s BCT=%.3fms gp=%.4fG util=%s qmax=%s pfc=%d retx=%d'
          % (r['cell'], r['bct_ms'], r['batch_goodput_gbps'],
             ('%.6f' % r['utilisation']) if r['utilisation'] else 'NA',
             ('%.0f' % r['q_max_b']) if r['q_max_b'] else 'NA',
             r['pfc'], r['retx']))
