# -*- coding: utf-8 -*-
# S3 full-metrics + gap attribution.  READ-ONLY: opens existing CSVs streaming,
# writes only into analysis/s3_full_metrics_v1/.  No source, config, parameter,
# threshold, checker or result is modified.  Nothing is re-run.
#
# Data-source asymmetry that constrains this analysis (established, not assumed):
#   BOTH arms : selected_link_timeseries.csv, flow_summary.csv,
#               selected_flow_timeseries.csv, round_summary.csv, pfc_events.csv
#   CBAP only : port_summary.csv (arrival/service rate), qc_trace.csv (zones,
#               boost/drain/pending), applied_rate_audit.csv, admission.csv,
#               rate_transition.csv, run.log migration events
#   DCQCN     : qc_trace.csv is a 447-byte header-only stub; port_summary.csv
#               absent -> every controller/arrival/service-rate metric that
#               depends on them is UNAVAILABLE for DCQCN and is recorded as such.
import csv
import gzip
import hashlib
import io
import os
import subprocess
import sys

BASE = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(BASE, 'analysis/s3_full_metrics_v1')
SCRIPTS = os.path.join(OUT, 'scripts')
CB = os.path.join(BASE, 'ckpt4_cbap_s3_out')
DQ = os.path.join(BASE, 'ckpt4_dcqcn_s3_out')
CBC = os.path.join(BASE, 'ckpt4_cbap_s3.txt')
DQC = os.path.join(BASE, 'ckpt4_dcqcn_s3.txt')

C_LINK = 10e9
PAY_B, WIRE_B = 1000.0, 1048.0
Q_ABS = 838.86e-6 * C_LINK / 8.0          # 1,048,575 B
M_SAFE = 67072.0
Q_RED = Q_ABS - M_SAFE
MAX_BOOST = 0.30 * C_LINK
Q_LOW = 0.5 * Q_ABS
MIN_RATE_PAY = 100e6
BASE_RTT_US = 15.2                        # maxRtt=15200 ns from run.log

os.makedirs(SCRIPTS, exist_ok=True)
ROWS = []


def m(mid, cat, algo, win, scope, stat, val, unit, num='', den='', n='',
      sf='', sc='', formula='', ev='MEASURED', avail='AVAILABLE', notes=''):
    ROWS.append(dict(metric_id=mid, category=cat, algorithm=algo, scenario='S3',
                     window=win, scope=scope, statistic=stat, value=val,
                     unit=unit, numerator=num, denominator=den,
                     sample_count=n, source_file=sf, source_columns=sc,
                     formula=formula, evidence_type=ev, availability=avail,
                     notes=notes))


def miss(mid, cat, algo, win, scope, stat, unit, why):
    m(mid, cat, algo, win, scope, stat, '', unit, ev='UNAVAILABLE',
      avail='MISSING', notes=why)


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def pct(v, q):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(q * (len(s) - 1))))]


def stats(v):
    if not v:
        return {}
    s = sorted(v)
    n = len(s)
    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / n if n > 1 else 0.0
    return dict(min=s[0], mean=mean, p50=pct(s, .50), p90=pct(s, .90),
                p95=pct(s, .95), p99=pct(s, .99), max=s[-1],
                std=var ** 0.5, n=n)


def cfgval(path, key):
    if not os.path.exists(path):
        return ''
    for ln in open(path):
        p = ln.split()
        if len(p) >= 2 and p[0] == key:
            return p[1]
    return ''


def flows(d):
    p = os.path.join(d, 'flow_summary.csv')
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p)))


def f(r, k, dv=0.0):
    try:
        return float(r.get(k, dv) or dv)
    except Exception:
        return dv


# ---------------------------------------------------------------- windows ---
def windows():
    w = {}
    for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
        fs = flows(d)
        inc = [r for r in fs if 0 < f(r, 'total_size_bytes') < 1e9 and f(r, 'fct') > 0]
        st = min(f(r, 'start_time') for r in inc)
        fi = max(f(r, 'finish_time') for r in inc)
        w[tag] = dict(first_start=st, last_finish=fi)
    T0 = max(w['CBAP']['first_start'], w['DCQCN']['first_start'])
    T1 = min(w['CBAP']['last_finish'], w['DCQCN']['last_finish'])
    w['W2'] = (T0, T1)
    later = 'CBAP' if w['CBAP']['last_finish'] > w['DCQCN']['last_finish'] else 'DCQCN'
    w['W3'] = (min(w['CBAP']['last_finish'], w['DCQCN']['last_finish']),
               max(w['CBAP']['last_finish'], w['DCQCN']['last_finish']))
    w['W3_arm'] = later
    return w


W = windows()
T0, T1 = W['W2']
W3a, W3b = W['W3']

# --------------------------------------------------- A. identity / config ---
BIN = '/work/simulation/build/scratch/third'
LIB = '/work/simulation/build/libns3.18-point-to-point-debug.so'
for k, p in (('binary', BIN), ('libns3', LIB),
             ('third_cc', '/work/simulation/scratch/third.cc'),
             ('recorder_ml', '/work/simulation/scratch/tx-serialization-recorder-ml.h')):
    m('A.sha.' + k, 'identity', 'BOTH', 'W0', 'toolchain', 'sha256', sha(p),
      'hex', sf=p, ev='MEASURED')
for nm, p in (('config_cbap', CBC), ('config_dcqcn', DQC)):
    m('A.sha.' + nm, 'identity', 'CBAP' if 'cbap' in nm else 'DCQCN', 'W0',
      'config', 'sha256', sha(p), 'hex', sf=p)
for nm in ('topology.txt', 's3_flow.txt', 's3_round_schedule.txt',
           's3_cbap_link.txt', 's3_cbap_path.txt'):
    m('A.sha.input.' + nm, 'identity', 'BOTH', 'W0', 'input', 'sha256',
      sha(os.path.join(BASE, nm)), 'hex', sf=nm,
      notes='identical for both arms (verified)')
for key in ('CBAP_MIGRATION_ENABLE', 'CBAP_CORE_INITIAL_RELEASE',
            'CBAP_INITIAL_RELEASE_RATIO', 'CBAP_MIGRATION_TRACE',
            'CC_MODE', 'CBAP_ENABLE', 'SIM_SEED', 'SIMULATOR_STOP_TIME',
            'MIN_RATE', 'CBAP_QC_MAX_BOOST_RATIO', 'CBAP_QC_H_GUARD_US',
            'CBAP_QC_APP_HARD_DELAY_US', 'CBAP_QC_SAFETY_MARGIN_BYTES',
            'PACKET_PAYLOAD_SIZE', 'CBAP_MAX_WIRE_PACKET_BYTES'):
    for tag, cp in (('CBAP', CBC), ('DCQCN', DQC)):
        v = cfgval(cp, key)
        m('A.cfg.' + key, 'identity', tag, 'W0', 'config', 'value',
          v if v else 'ABSENT', 'text', sf=os.path.basename(cp),
          sc=key, ev='MEASURED')
# parsed echo, straight from run.log
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    ln = ''
    p = os.path.join(d, 'run.log')
    if os.path.exists(p):
        for x in open(p, errors='replace'):
            if 'CBAP_REALLOC_PARSED' in x:
                ln = x.strip()
                break
    m('A.parsed.realloc', 'identity', tag, 'W0', 'runtime', 'echo',
      ln if ln else 'ABSENT', 'text', sf='run.log',
      sc='CBAP_REALLOC_PARSED', ev='MEASURED',
      notes='parsed values echoed by the simulator, not config text')
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'run.log')
    wall = ''
    if os.path.exists(p):
        tl = [x.strip() for x in open(p, errors='replace') if x.strip()]
        if tl:
            wall = tl[-1]
    m('A.wall', 'identity', tag, 'W0', 'run', 'wall_seconds', wall, 's',
      sf='run.log', sc='last line', ev='MEASURED')
# pg distribution
pg = {}
for ln in open(os.path.join(BASE, 's3_flow.txt')):
    p = ln.split()
    if len(p) >= 6:
        pg[p[2]] = pg.get(p[2], 0) + 1
m('A.pg.dist', 'identity', 'BOTH', 'W0', 'traffic', 'distribution',
  ';'.join('pg%s=%d' % kv for kv in sorted(pg.items())), 'count',
  sf='s3_flow.txt', sc='col3', ev='MEASURED')
for k, v in (('C_link', C_LINK), ('payload_packet_bytes', PAY_B),
             ('wire_packet_bytes', WIRE_B), ('Q_abs', Q_ABS), ('Q_red', Q_RED),
             ('Q_low', Q_LOW), ('M_safe', M_SAFE), ('MAX_BOOST', MAX_BOOST),
             ('MIN_RATE_payload', MIN_RATE_PAY), ('base_rtt_us', BASE_RTT_US)):
    m('A.const.' + k, 'identity', 'BOTH', 'W0', 'constant', 'value', v,
      'bps/B/us', ev='DERIVED', notes='frozen configuration constant')
for nm, (a, b) in (('W1_CBAP', (W['CBAP']['first_start'], W['CBAP']['last_finish'])),
                   ('W1_DCQCN', (W['DCQCN']['first_start'], W['DCQCN']['last_finish'])),
                   ('W2_COMMON_OVERLAP', (T0, T1)), ('W3_CBAP_TAIL', (W3a, W3b))):
    m('A.window.' + nm, 'identity', 'BOTH', nm, 'window', 'start_s', a, 's',
      ev='DERIVED')
    m('A.window.' + nm + '.end', 'identity', 'BOTH', nm, 'window', 'end_s', b,
      's', ev='DERIVED')
    m('A.window.' + nm + '.dur', 'identity', 'BOTH', nm, 'window',
      'duration_ms', 1e3 * (b - a), 'ms', ev='DERIVED')

# ------------------------------------------------- B. flow completion -------
PF = []
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    fs = flows(d)
    inc = [r for r in fs if 0 < f(r, 'total_size_bytes') < 1e9]
    bg = [r for r in fs if f(r, 'total_size_bytes') >= 1e9]
    done = [r for r in inc if f(r, 'completed') > 0]
    fct = [f(r, 'fct') for r in done if f(r, 'fct') > 0]
    st = stats(fct)
    m('B.incast.count', 'completion', tag, 'W1', 'incast', 'count', len(inc),
      'flows', sf='flow_summary.csv', sc='total_size_bytes<1e9')
    m('B.incast.completed', 'completion', tag, 'W1', 'incast', 'count',
      len(done), 'flows', sf='flow_summary.csv', sc='completed')
    for k in ('min', 'mean', 'p50', 'p90', 'p95', 'p99', 'max', 'std'):
        m('B.fct.' + k, 'completion', tag, 'W1', 'incast', k, 1e3 * st[k],
          'ms', n=st['n'], sf='flow_summary.csv', sc='fct',
          formula='percentile/mean over completed incast fct')
    m('B.fct.cv', 'completion', tag, 'W1', 'incast', 'cv',
      st['std'] / st['mean'] if st['mean'] else '', 'ratio',
      formula='std/mean', ev='DERIVED')
    m('B.fct.max_minus_mean', 'completion', tag, 'W1', 'incast', 'spread',
      1e3 * (st['max'] - st['mean']), 'ms', formula='max-mean', ev='DERIVED')
    m('B.fct.max_minus_min', 'completion', tag, 'W1', 'incast', 'spread',
      1e3 * (st['max'] - st['min']), 'ms', formula='max-min', ev='DERIVED')
    fin = sorted(f(r, 'finish_time') for r in done)
    m('B.cct', 'completion', tag, 'W1', 'incast', 'batch_completion_time',
      1e3 * st['max'], 'ms', formula='max fct', ev='DERIVED')
    m('B.first_finish', 'completion', tag, 'W1', 'incast', 'time_s', fin[0],
      's', sf='flow_summary.csv', sc='finish_time')
    m('B.last_finish', 'completion', tag, 'W1', 'incast', 'time_s', fin[-1],
      's', sf='flow_summary.csv', sc='finish_time')
    m('B.completion_skew', 'completion', tag, 'W1', 'incast', 'skew_ms',
      1e3 * (fin[-1] - fin[0]), 'ms', formula='last_finish-first_finish',
      ev='DERIVED')
    tot_pay = sum(f(r, 'total_size_bytes') for r in inc)
    m('B.goodput.payload', 'completion', tag, 'W1', 'incast', 'aggregate',
      8 * tot_pay / st['max'] / 1e9, 'Gbps', num=8 * tot_pay, den=st['max'],
      formula='8*sum(total_size_bytes)/CCT', ev='DERIVED')
    m('B.goodput.wire', 'completion', tag, 'W1', 'incast', 'aggregate',
      8 * tot_pay * WIRE_B / PAY_B / st['max'] / 1e9, 'Gbps',
      formula='payload goodput * 1048/1000', ev='DERIVED',
      notes='wire domain, header overhead included')
    m('B.acked_bytes', 'completion', tag, 'W1', 'incast', 'sum',
      sum(f(r, 'acked_bytes') for r in inc), 'B', sf='flow_summary.csv',
      sc='acked_bytes')
    # Jain fairness on per-flow goodput
    g = [f(r, 'flow_goodput') for r in done if f(r, 'flow_goodput') > 0]
    if g:
        jg = (sum(g) ** 2) / (len(g) * sum(x * x for x in g))
        m('B.jain.goodput', 'completion', tag, 'W1', 'incast', 'index', jg,
          'ratio', n=len(g), formula='(sum x)^2/(n*sum x^2)', ev='DERIVED')
        jf = (sum(fct) ** 2) / (len(fct) * sum(x * x for x in fct))
        m('B.jain.fct', 'completion', tag, 'W1', 'incast', 'index', jf,
          'ratio', n=len(fct), formula='(sum x)^2/(n*sum x^2)', ev='DERIVED',
          notes='FCT-Jain is reported for symmetry; equal-size flows make it '
                'a dispersion proxy, not a fairness claim')
    for r in inc + bg:
        PF.append(dict(algorithm=tag, flow_id=r.get('flow_id'),
                       src=r.get('src'), dst=r.get('dst'),
                       size_bytes=f(r, 'total_size_bytes'),
                       start_time=f(r, 'start_time'),
                       finish_time=f(r, 'finish_time'), fct=f(r, 'fct'),
                       acked_bytes=f(r, 'acked_bytes'),
                       completed=r.get('completed'),
                       goodput_bps=f(r, 'flow_goodput'),
                       retx_bytes=f(r, 'retx_bytes'),
                       retx_events=f(r, 'retx_events'),
                       klass='incast' if f(r, 'total_size_bytes') < 1e9 else 'background'))
    for r in bg:
        m('F.bg.fullrun.goodput', 'background', tag, 'W0', 'flow ' + str(r.get('flow_id')),
          'mean', f(r, 'flow_goodput') / 1e9, 'Gbps', sf='flow_summary.csv',
          sc='flow_goodput', notes='FULL RUN lifetime, not overlap-window')
        m('F.bg.fullrun.acked', 'background', tag, 'W0', 'flow ' + str(r.get('flow_id')),
          'sum', f(r, 'acked_bytes'), 'B', sf='flow_summary.csv', sc='acked_bytes')
        m('F.bg.completed', 'background', tag, 'W0', 'flow ' + str(r.get('flow_id')),
          'flag', r.get('completed'), 'bool', sf='flow_summary.csv',
          notes='4 GB flow cannot finish inside a 3 s run; 0 is expected')

# --------------------------- C/D. link timeseries: BOTH arms ---------------
TS = []
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'selected_link_timeseries.csv')
    if not os.path.exists(p):
        continue
    per = {}
    with open(p) as fh:
        rd = csv.DictReader(fh)
        prev_t = {}
        for r in rd:
            t = f(r, 'time')
            lk = r.get('link_id', '0')
            q = f(r, 'queue_bytes')
            tx = f(r, 'tx_bytes_delta')
            util = f(r, 'utilization')
            ecn = f(r, 'ecn_marks_delta')
            dt = t - prev_t.get(lk, t)
            prev_t[lk] = t
            served = 8 * tx / dt if dt > 0 else 0.0
            for wn, (a, b) in (('W1', (W[tag]['first_start'], W[tag]['last_finish'])),
                               ('W2', (T0, T1)), ('W3', (W3a, W3b)),
                               ('W0', (-1, 1e9))):
                if a <= t <= b:
                    k = (wn, lk)
                    per.setdefault(k, dict(q=[], served=[], util=[], ecn=0.0,
                                           tx=0.0, idle=0, n=0, dt=[]))
                    e = per[k]
                    e['q'].append(q)
                    e['served'].append(served)
                    e['util'].append(served / C_LINK)
                    e['ecn'] += ecn
                    e['tx'] += tx
                    e['n'] += 1
                    if dt > 0:
                        e['dt'].append(dt)
                    if tx == 0:
                        e['idle'] += 1
            if T0 <= t <= T1 and len(TS) < 400000:
                TS.append(dict(time_ns=int(t * 1e9), algorithm=tag, window='W2',
                               link_id=lk, node_id='', if_index='',
                               queue_bytes=q,
                               queue_delay_us=8 * q / C_LINK * 1e6,
                               served_payload_bps=served * PAY_B / WIRE_B,
                               served_wire_bps=served, arrival_wire_bps='',
                               utilization=served / C_LINK,
                               idle=1 if tx == 0 else 0, zone='',
                               boost_bps='', drain_bps='', pending_bps='',
                               sumR_bps='', background_rate_bps='',
                               incast_rate_bps=''))
    for (wn, lk), e in sorted(per.items()):
        sc = 'link' + lk
        qs = stats(e['q'])
        for k in ('min', 'mean', 'p50', 'p90', 'p95', 'p99', 'max', 'std'):
            m('D.queue.bytes.' + k, 'queue', tag, wn, sc, k, qs[k], 'B',
              n=qs['n'], sf='selected_link_timeseries.csv', sc='queue_bytes')
            m('D.queue.delay.' + k, 'queue', tag, wn, sc, k,
              8 * qs[k] / C_LINK * 1e6, 'us', ev='DERIVED',
              formula='8*queue_bytes/C*1e6')
        m('D.queue.pct_Qabs.max', 'queue', tag, wn, sc, 'max',
          100.0 * qs['max'] / Q_ABS, '%', ev='DERIVED',
          formula='100*max_queue/Q_abs')
        m('D.queue.rtt_mult.max', 'queue', tag, wn, sc, 'max',
          (8 * qs['max'] / C_LINK * 1e6) / BASE_RTT_US, 'xRTT', ev='DERIVED',
          formula='queue_delay_us/base_rtt_us')
        for nm, th in (('Q_low', Q_LOW), ('Q_high', Q_RED - MAX_BOOST * 175e-6 / 8),
                       ('Q_red', Q_RED), ('Q_abs', Q_ABS)):
            over = sum(1 for x in e['q'] if x > th)
            m('D.queue.frac_above_' + nm, 'queue', tag, wn, sc, 'fraction',
              over / float(e['n']) if e['n'] else 0, 'ratio', num=over,
              den=e['n'], ev='DERIVED')
        ss = stats(e['served'])
        for k in ('mean', 'p50', 'p95', 'p99', 'max'):
            m('C.served.wire.' + k, 'service', tag, wn, sc, k, ss[k] / 1e9,
              'Gbps', n=ss['n'], sf='selected_link_timeseries.csv',
              sc='tx_bytes_delta,time', formula='8*tx_bytes_delta/dt',
              ev='DERIVED')
            m('C.served.payload.' + k, 'service', tag, wn, sc, k,
              ss[k] * PAY_B / WIRE_B / 1e9, 'Gbps', ev='DERIVED',
              formula='served_wire*1000/1048')
        us = stats(e['util'])
        for k in ('mean', 'p50', 'p95', 'max'):
            m('C.utilization.' + k, 'service', tag, wn, sc, k, us[k], 'ratio',
              ev='DERIVED', formula='served_wire/C')
        for thr in (0.90, 0.95, 0.99):
            below = sum(1 for x in e['util'] if x < thr)
            m('C.util.frac_below_%d' % int(thr * 100), 'service', tag, wn, sc,
              'fraction', below / float(e['n']) if e['n'] else 0, 'ratio',
              num=below, den=e['n'], ev='DERIVED')
        for thr, nm in ((1.0, 'C'), (1.05, '1.05C'), (1.10, '1.10C')):
            above = sum(1 for x in e['util'] if x > thr)
            m('C.util.frac_above_' + nm, 'service', tag, wn, sc, 'fraction',
              above / float(e['n']) if e['n'] else 0, 'ratio', num=above,
              den=e['n'], ev='DERIVED')
        m('C.idle.fraction', 'service', tag, wn, sc, 'fraction',
          e['idle'] / float(e['n']) if e['n'] else 0, 'ratio', num=e['idle'],
          den=e['n'], sf='selected_link_timeseries.csv', sc='tx_bytes_delta==0',
          ev='DERIVED')
        m('C.busy.fraction', 'service', tag, wn, sc, 'fraction',
          1 - (e['idle'] / float(e['n']) if e['n'] else 0), 'ratio',
          ev='DERIVED')
        m('C.served.total_bytes', 'service', tag, wn, sc, 'sum', e['tx'], 'B',
          sf='selected_link_timeseries.csv', sc='tx_bytes_delta')
        span = (T1 - T0) if wn == 'W2' else None
        if wn == 'W2' and span and span > 0:
            ideal = C_LINK * span / 8.0
            m('C.service_deficit.bytes', 'service', tag, wn, sc, 'deficit',
              ideal - e['tx'], 'B', num=ideal, den=e['tx'], ev='DERIVED',
              formula='C*window/8 - served_bytes',
              notes='bytes not served vs an ideal fully-loaded link')
            m('C.service_deficit.frac', 'service', tag, wn, sc, 'fraction',
              (ideal - e['tx']) / ideal, 'ratio', ev='DERIVED')
        m('G.ecn.marks', 'safety', tag, wn, sc, 'sum', e['ecn'], 'packets',
          sf='selected_link_timeseries.csv', sc='ecn_marks_delta')

# ----------------------- C/E. CBAP-only: port_summary + qc_trace ----------
p = os.path.join(CB, 'port_summary.csv')
if os.path.exists(p):
    per = {}
    with open(p) as fh:
        for r in csv.DictReader(fh):
            t = f(r, 'delivery_time_ns') / 1e9
            lk = r.get('link_id', '0')
            for wn, (a, b) in (('W1', (W['CBAP']['first_start'], W['CBAP']['last_finish'])),
                               ('W2', (T0, T1)), ('W3', (W3a, W3b))):
                if a <= t <= b:
                    e = per.setdefault((wn, lk), dict(ar=[], sr=[]))
                    e['ar'].append(f(r, 'arrival_rate_bps'))
                    e['sr'].append(f(r, 'service_rate_bps'))
    for (wn, lk), e in sorted(per.items()):
        a1 = stats(e['ar'])
        s1 = stats(e['sr'])
        for k in ('mean', 'p50', 'p95', 'p99', 'max'):
            m('C.arrival.wire.' + k, 'service', 'CBAP', wn, 'link' + lk, k,
              a1[k] / 1e9, 'Gbps', n=a1['n'], sf='port_summary.csv',
              sc='arrival_rate_bps')
            m('C.service_rate.' + k, 'service', 'CBAP', wn, 'link' + lk, k,
              s1[k] / 1e9, 'Gbps', n=s1['n'], sf='port_summary.csv',
              sc='service_rate_bps')
        for thr, nm in ((1.0, 'C'), (1.05, '1.05C'), (1.10, '1.10C')):
            ab = sum(1 for x in e['ar'] if x > thr * C_LINK)
            m('C.arrival.frac_above_' + nm, 'service', 'CBAP', wn, 'link' + lk,
              'fraction', ab / float(a1['n']) if a1['n'] else 0, 'ratio',
              num=ab, den=a1['n'], ev='DERIVED',
              notes='arrival>C is permitted while the queue stays in band')
for wn in ('W1', 'W2', 'W3'):
    for k in ('mean', 'p50', 'p95', 'p99', 'max'):
        miss('C.arrival.wire.' + k, 'service', 'DCQCN', wn, 'link0', k, 'Gbps',
             'port_summary.csv is CBAP-only (CBAP telemetry path); DCQCN never '
             'writes arrival_rate_bps. Needs a CC-agnostic port sampler.')
        miss('C.service_rate.' + k, 'service', 'DCQCN', wn, 'link0', k, 'Gbps',
             'port_summary.csv absent for DCQCN; served rate for DCQCN is '
             'DERIVED from tx_bytes_delta instead (see C.served.wire.*)')

q = os.path.join(CB, 'qc_trace.csv')
if os.path.exists(q):
    zc = {}
    trans = {}
    prevz = None
    bo, dr, pe, sm = [], [], [], []
    nrow = 0
    with open(q) as fh:
        for r in csv.DictReader(fh):
            t = f(r, 'time_ns') / 1e9
            if not (T0 <= t <= T1):
                continue
            nrow += 1
            z = r.get('zone', '')
            zc[z] = zc.get(z, 0) + 1
            if prevz is not None and z != prevz:
                trans[prevz + '->' + z] = trans.get(prevz + '->' + z, 0) + 1
            prevz = z
            bo.append(f(r, 'boost_effective'))
            dr.append(f(r, 'drain'))
            pe.append(f(r, 'pending_generation'))
            sm.append(f(r, 'sumR_effective'))
    tot = float(nrow) if nrow else 1.0
    for z, c in sorted(zc.items()):
        m('E.zone.fraction', 'controller', 'CBAP', 'W2', 'zone ' + z,
          'fraction', c / tot, 'ratio', num=c, den=nrow, sf='qc_trace.csv',
          sc='zone')
    for k, v in sorted(trans.items()):
        m('E.zone.transitions', 'controller', 'CBAP', 'W2', k, 'count', v,
          'count', sf='qc_trace.csv', sc='zone')
    for nm, arr in (('boost', bo), ('drain', dr), ('sumR', sm)):
        s1 = stats(arr)
        if s1:
            for k in ('min', 'mean', 'p95', 'max'):
                m('E.%s.%s' % (nm, k), 'controller', 'CBAP', 'W2', 'link0', k,
                  s1[k] / 1e9, 'Gbps', n=s1['n'], sf='qc_trace.csv', sc=nm)
            nz = sum(1 for x in arr if x > 0)
            m('E.%s.frac_nonzero' % nm, 'controller', 'CBAP', 'W2', 'link0',
              'fraction', nz / tot, 'ratio', num=nz, den=nrow, ev='DERIVED')
    nzp = sum(1 for x in pe if x > 0)
    m('E.pending.frac_nonzero', 'controller', 'CBAP', 'W2', 'link0',
      'fraction', nzp / tot, 'ratio', num=nzp, den=nrow, sf='qc_trace.csv',
      sc='pending_generation')
    if sm:
        over = sum(1 for x in sm if x > C_LINK)
        m('E.sumR.frac_above_C', 'controller', 'CBAP', 'W2', 'link0',
          'fraction', over / tot, 'ratio', num=over, den=nrow, ev='DERIVED',
          notes='sumR>C is allowed by design while the queue is in band')
for nm in ('zone.fraction', 'boost.mean', 'drain.mean', 'pending.frac_nonzero',
           'sumR.mean'):
    miss('E.' + nm, 'controller', 'DCQCN', 'W2', 'link0', 'value', 'various',
         'DCQCN has no CBAP queue controller; qc_trace.csv is a header-only '
         '447-byte stub. Zones/boost/drain/pending do not exist for DCQCN and '
         'must not be reported as 0.')

# ------------------------------ E. migration events ----------------------
rl = os.path.join(CB, 'run.log')
if os.path.exists(rl):
    mig = 0
    replan = 0
    first_t = None
    conv_t = None
    old_first = None
    old_last = None
    bg_min = None
    for ln in open(rl, errors='replace'):
        if 'CBAP_MIG_REPLAN' in ln:
            replan += 1
        elif 'CBAP_MIG ' in ln:
            mig += 1
            tk = dict(x.split('=', 1) for x in ln.split() if '=' in x)
            t = float(tk.get('t', 0)) / 1e9
            if first_t is None:
                first_t = t
            if tk.get('side') == 'old':
                cur = float(tk.get('cur', 0))
                if old_first is None:
                    old_first = cur
                old_last = float(tk.get('next', cur))
                bg_min = cur if bg_min is None else min(bg_min, cur)
            if tk.get('end') == 'converged':
                conv_t = t
    m('E.migration.events', 'controller', 'CBAP', 'W0', 'link0', 'count', mig,
      'count', sf='run.log', sc='CBAP_MIG')
    m('E.migration.replans', 'controller', 'CBAP', 'W0', 'link0', 'count',
      replan, 'count', sf='run.log', sc='CBAP_MIG_REPLAN')
    if first_t and conv_t:
        m('E.migration.convergence_time', 'controller', 'CBAP',
          'W4_MIGRATION_CONVERGENCE', 'link0', 'duration_ms',
          1e3 * (conv_t - first_t), 'ms', ev='DERIVED',
          formula='last end=converged - first CBAP_MIG', sf='run.log')
    if old_first is not None:
        m('F.bg.old_side.start_rate', 'background', 'CBAP', 'W2', 'flow0',
          'value', old_first / 1e9, 'Gbps', sf='run.log', sc='side=old cur')
        m('F.bg.old_side.end_rate', 'background', 'CBAP', 'W2', 'flow0',
          'value', old_last / 1e9, 'Gbps', sf='run.log', sc='side=old next')
        m('F.bg.suppression_depth', 'background', 'CBAP', 'W2', 'flow0',
          'ratio', old_first / old_last if old_last else '', 'x',
          ev='DERIVED', formula='start_rate/end_rate')
    miss('E.migration.events', 'controller', 'DCQCN', 'W0', 'link0', 'count',
         'count', 'DCQCN has no capacity migration mechanism by construction')

# ---------------- F. background rate inside the overlap window ------------
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'selected_flow_timeseries.csv')
    if not os.path.exists(p):
        continue
    bgr = []
    incr = []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            t = f(r, 'time')
            if not (T0 <= t <= T1):
                continue
            fid = r.get('flow_id', '')
            rate = f(r, 'current_rate')
            if fid == '0':
                bgr.append(rate)
            else:
                incr.append(rate)
    if bgr:
        s1 = stats(bgr)
        for k in ('min', 'mean', 'p50', 'p95', 'max'):
            m('F.bg.overlap.rate.' + k, 'background', tag, 'W2', 'flow0', k,
              s1[k] / 1e9, 'Gbps', n=s1['n'],
              sf='selected_flow_timeseries.csv', sc='current_rate',
              notes='OVERLAP WINDOW instantaneous sender rate, flow_id=0')
        m('F.bg.overlap.rate.p5', 'background', tag, 'W2', 'flow0', 'p5',
          pct(bgr, .05) / 1e9, 'Gbps', ev='DERIVED')
        at_min = sum(1 for x in bgr if x <= MIN_RATE_PAY * 1.02)
        m('F.bg.overlap.frac_at_min_rate', 'background', tag, 'W2', 'flow0',
          'fraction', at_min / float(len(bgr)), 'ratio', num=at_min,
          den=len(bgr), ev='DERIVED',
          formula='fraction of overlap samples with rate <= 1.02*MIN_RATE')
        m('F.bg.overlap.suppression_ratio', 'background', tag, 'W2', 'flow0',
          'ratio', s1['max'] / s1['min'] if s1['min'] else '', 'x',
          ev='DERIVED', formula='max/min sender rate in overlap')
    if incr:
        s2 = stats(incr)
        for k in ('min', 'mean', 'p50', 'p95', 'max'):
            m('F.incast.overlap.rate.' + k, 'background', tag, 'W2',
              'incast_flows', k, s2[k] / 1e9, 'Gbps', n=s2['n'],
              sf='selected_flow_timeseries.csv', sc='current_rate')

# ----------------------------- G. safety ---------------------------------
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'pfc_events.csv')
    n = 0
    if os.path.exists(p):
        n = max(0, sum(1 for _ in open(p)) - 1)
    m('G.pfc.events', 'safety', tag, 'W0', 'all', 'count', n, 'count',
      sf='pfc_events.csv')
    rl2 = os.path.join(d, 'run.log')
    dr = 0
    if os.path.exists(rl2):
        dr = sum(1 for ln in open(rl2, errors='replace') if 'Drop:' in ln)
    m('G.drops', 'safety', tag, 'W0', 'all', 'count', dr, 'count',
      sf='run.log', sc='Drop:')
    fs = flows(d)
    m('G.retx.bytes', 'safety', tag, 'W0', 'all', 'sum',
      sum(f(r, 'retx_bytes') for r in fs), 'B', sf='flow_summary.csv')
    m('G.retx.events', 'safety', tag, 'W0', 'all', 'sum',
      sum(f(r, 'retx_events') for r in fs), 'count', sf='flow_summary.csv')
    miss('G.cnp.count', 'safety', tag, 'W0', 'all', 'count', 'count',
         'No per-flow CNP counter is emitted in these outputs; '
         'feedback_summary.csv aggregates without a CNP column.')

# ------------------------------- write out -------------------------------
FIELDS = ['metric_id', 'category', 'algorithm', 'scenario', 'window', 'scope',
          'statistic', 'value', 'unit', 'numerator', 'denominator',
          'sample_count', 'source_file', 'source_columns', 'formula',
          'evidence_type', 'availability', 'notes']
with open(os.path.join(OUT, 'S3_FULL_METRICS.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in ROWS:
        w.writerow(r)
with gzip.open(os.path.join(OUT, 'S3_PER_FLOW.csv.gz'), 'wt', newline='') as fh:
    if PF:
        w = csv.DictWriter(fh, fieldnames=list(PF[0].keys()))
        w.writeheader()
        for r in PF:
            w.writerow(r)
with gzip.open(os.path.join(OUT, 'S3_TIMESERIES.csv.gz'), 'wt', newline='') as fh:
    if TS:
        w = csv.DictWriter(fh, fieldnames=list(TS[0].keys()))
        w.writeheader()
        for r in TS:
            w.writerow(r)
avail = sum(1 for r in ROWS if r['availability'] == 'AVAILABLE')
missn = sum(1 for r in ROWS if r['availability'] == 'MISSING')
print('metrics_total=%d available=%d missing=%d' % (len(ROWS), avail, missn))
print('per_flow_rows=%d timeseries_rows=%d' % (len(PF), len(TS)))
print('W1_CBAP=[%.9f, %.9f]' % (W['CBAP']['first_start'], W['CBAP']['last_finish']))
print('W1_DCQCN=[%.9f, %.9f]' % (W['DCQCN']['first_start'], W['DCQCN']['last_finish']))
print('W2_COMMON=[%.9f, %.9f] dur=%.6f ms' % (T0, T1, 1e3 * (T1 - T0)))
print('W3_TAIL=[%.9f, %.9f] arm=%s dur=%.6f ms' % (W3a, W3b, W['W3_arm'], 1e3 * (W3b - W3a)))
