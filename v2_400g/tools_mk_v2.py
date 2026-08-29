# -*- coding: utf-8 -*-
# v2_400g unified config generator.  This round generates PREFLIGHT and HEFF
# cells only (screening/pilot generation is present but gated off until the
# preflight passes, per instruction).
#
# Derivations (v2 rules, from the campaign spec):
#   MIN_RATE  = MIN_RATE_FRAC * C                (payload bps, 0.01C)
#   Q_target  = C * D_target / 8
#   Q_abs     = min(C * D_abs / 8, 0.25 * BUFFER)
#   BMAX      = BMAX_RATIO * C
#   bg rate   = BG_LOAD_FRAC * C
# Q_abs is NOT bound to any message size.  All file paths absolute under
# /work/v2_400g/.
import io
import os
import re
import sys

SRC = '/work/simulation/experiment/scheme1_sba'
V2 = '/work/v2_400g'
CF = V2 + '/configs'
RS = V2 + '/results'
for d in (CF, RS, V2 + '/logs', V2 + '/reports'):
    os.path.isdir(d) or os.makedirs(d)

RATES = {10: '10Gbps', 200: '200Gbps', 400: '400Gbps'}
FANIN = 64
PKT_WIRE, PKT_PAY = 1048.0, 1000.0


def gbps(r):
    return r * 1e9


def load(p):
    return io.open(p, encoding='utf-8', errors='surrogateescape').read()


def put(rel, text):
    p = os.path.join(V2, rel)
    d = os.path.dirname(p)
    os.path.isdir(d) or os.makedirs(d)
    io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(text)
    return p


# ---- per-rate scenario files -----------------------------------------------
def topo(rate):
    t = load(os.path.join(SRC, 'topology.txt')).replace('10Gbps', RATES[rate])
    return put('configs/topo_%dg.txt' % rate, t)


def flow_files(rate, size_bytes, stop_s, tag):
    C = gbps(rate)
    bg_bytes = int(1.2 * 0.95 * C * stop_s / 8)      # never completes
    fl = ['%d' % (FANIN + 1), '65 64 3 100 %d 0.002' % bg_bytes]
    for s in range(FANIN):
        fl.append('%d 64 3 100 %d 0.05' % (s, size_bytes))
    put('configs/%s_flow.txt' % tag, '\n'.join(fl) + '\n')
    sch = ['%d' % (FANIN + 1),
           '0 0 0 1 %d 0 0 0 10000000' % bg_bytes]
    for i in range(FANIN):
        sch.append('%d 0 1 %d %d 0 0 0 100000000' % (1 + i, FANIN,
                                                     size_bytes))
    put('configs/%s_sched.txt' % tag, '\n'.join(sch) + '\n')
    put('configs/%s_link.txt' % tag,
        '1\n0 84 1 %d 400000 0 1\n' % int(C))
    pth = ['%d' % (FANIN + 1)]
    for i in range(FANIN + 1):
        pth.append('%d 1 0' % i)
    put('configs/%s_path.txt' % tag, '\n'.join(pth) + '\n')


def base_config(kind):
    # kind: 'cbap' from scr8_b040, 'dcqcn' from mx_s3_dcqcn
    return load(os.path.join(SRC,
                'scr8_b040.txt' if kind == 'cbap' else 'mx_s3_dcqcn.txt'))


def setkey(t, k, v):
    pat = re.compile(r'^%s\s+.*$' % re.escape(k), re.M)
    if pat.search(t):
        return pat.sub('%s %s' % (k, v), t)
    return t.rstrip('\n') + '\n%s %s\n' % (k, v)


def delkey(t, k):
    return re.sub(r'^%s\s+.*\n' % re.escape(k), '', t, flags=re.M)


def make_cell(tag, kind, rate, size_bytes, stop_s, over, heff_us,
              d_target_us=16, d_abs_us=80, bmax=0.04, buffer_mb=64,
              bg_frac=0.8, epoch_us=5, wire_domain=1):
    C = gbps(rate)
    flow_files(rate, size_bytes, stop_s, tag)
    t = base_config(kind)
    out = RS + '/' + tag
    os.path.isdir(out) or os.makedirs(out)
    old = re.search(r'^FLOW_SUMMARY_FILE\s+(\S+)/', t, re.M).group(1)
    t = t.replace(old + '/', out + '/').replace(old, out)
    q_abs_B = min(C * d_abs_us * 1e-6 / 8.0, 0.25 * buffer_mb * 1048576)
    d_abs_eff_us = q_abs_B * 8.0 / C * 1e6
    kv = {
        'TOPOLOGY_FILE': topo(rate),
        'FLOW_FILE': CF + '/%s_flow.txt' % tag,
        'ROUND_SCHEDULE_FILE': CF + '/%s_sched.txt' % tag,
        'CBAP_LINK_FILE': CF + '/%s_link.txt' % tag,
        'CBAP_PATH_FILE': CF + '/%s_path.txt' % tag,
        'SIMULATOR_STOP_TIME': '%.3f' % stop_s,
        'QLEN_MON_START': '0', 'QLEN_MON_END': '%d' % int(stop_s * 1e9),
        'QLEN_MON_FILE': '/dev/null',
        'SCENARIO': tag,
        'APP_RATE_CAP_BPS': '%d' % int(bg_frac * C),
        'BUFFER_SIZE': '%d' % buffer_mb,
        'MIN_RATE': '%dMb/s' % int(0.01 * rate * 1000),
        'KMIN_MAP': '1 %d 400' % int(C),
        'KMAX_MAP': '1 %d 1600' % int(C),
        'PMAX_MAP': '1 %d 0.2' % int(C),
        'FINAL_COLLECTIVE_FLOW_COUNT': '%d' % FANIN,
        'SBA_WIRE_DOMAIN_PLANNING': '%d' % wire_domain,
    }
    if kind == 'cbap':
        kv.update({
            'CBAP_QC_H_GUARD_US': '%.3f' % heff_us,
            'CBAP_QC_APP_HARD_DELAY_US': '%.4f' % d_abs_eff_us,
            'CBAP_QC_SAFETY_MARGIN_BYTES': '%d' % (FANIN * 1048),
            'CBAP_QB2_BMAX_RATIO': '%.3f' % bmax,
            'CBAP_QB2_QTARGET_RATIO': '%.6f' % (d_target_us / d_abs_eff_us),
            'CBAP_QB2_TRACE_FILE': out + '/controller_v2_trace.csv',
            'CBAP_CONTROL_EPOCH_US': '%d' % epoch_us,
            'CBAP_ACTUATION_FILE': out + '/actuation.csv',
        })
    for k, v in over.items():
        kv[k] = v
    for k, v in kv.items():
        t = setkey(t, k, str(v))
    for k in ('CBAP_QC_TRACE_FILE', 'TX_SERIALIZATION_TRACE_FILE'):
        if k not in over:
            t = delkey(t, k)
    put('configs/%s.txt' % tag, t)
    print('cell %-22s rate=%dG size=%s stop=%.3fs Qabs=%.0fB(%.1fus) '
          'kind=%s' % (tag, rate, size_bytes, stop_s, q_abs_B, d_abs_eff_us,
                       kind))


MODE = sys.argv[1] if len(sys.argv) > 1 else 'preflight'
MB = 1048576

if MODE == 'preflight':
    for rate in (10, 200, 400):
        C = gbps(rate)
        # single flow, no bg, no congestion; TX serialization ON to verify
        # the packet gap; theory time printed for the analyzer
        tag = 'pf_single_%dg' % rate
        stop = 0.05 + MB * 8.0 * (PKT_WIRE / PKT_PAY) / C * 3
        flow_files(rate, MB, stop, tag)
        # rewrite flow file: single flow only, no bg
        put('configs/%s_flow.txt' % tag, '1\n0 64 3 100 %d 0.01\n' % MB)
        put('configs/%s_sched.txt' % tag,
            '1\n0 0 0 1 %d 0 0 0 20000000\n' % MB)
        put('configs/%s_path.txt' % tag, '1\n0 1 0\n')
        t = base_config('dcqcn')
        out = RS + '/' + tag
        os.path.isdir(out) or os.makedirs(out)
        old = re.search(r'^FLOW_SUMMARY_FILE\s+(\S+)/', t, re.M).group(1)
        t = t.replace(old + '/', out + '/').replace(old, out)
        for k, v in {
                'TOPOLOGY_FILE': topo(rate),
                'FLOW_FILE': CF + '/%s_flow.txt' % tag,
                'ROUND_SCHEDULE_FILE': CF + '/%s_sched.txt' % tag,
                'CBAP_LINK_FILE': CF + '/%s_link.txt' % tag,
                'CBAP_PATH_FILE': CF + '/%s_path.txt' % tag,
                'SIMULATOR_STOP_TIME': '%.3f' % stop,
                'QLEN_MON_START': '0',
                'QLEN_MON_END': '%d' % int(stop * 1e9),
                'QLEN_MON_FILE': '/dev/null', 'SCENARIO': tag,
                'APP_RATE_CAP_FLOW': '255',
                'BUFFER_SIZE': '64',
                'KMIN_MAP': '1 %d 400' % int(C),
                'KMAX_MAP': '1 %d 1600' % int(C),
                'PMAX_MAP': '1 %d 0.2' % int(C),
                'FINAL_COLLECTIVE_FLOW_COUNT': '1',
                'TX_SERIALIZATION_TRACE_FILE':
                    out + '/tx_serialization.csv'}.items():
            t = setkey(t, k, str(v))
        t = delkey(t, 'CBAP_QC_TRACE_FILE')
        put('configs/%s.txt' % tag, t)
        print('cell %-22s single-flow line-rate check, stop=%.3fs'
              % (tag, stop))
        # 64-way sync burst, CC inert (KMIN >> buffer), bg 0.8C
        tag = 'pf_burst_%dg' % rate
        batch_s = FANIN * 262144 * 8.0 * (PKT_WIRE / PKT_PAY) / C
        stop = 0.1 + batch_s * 5 + 0.03
        make_cell(tag, 'dcqcn', rate, 262144, stop,
                  {'KMIN_MAP': '1 %d 999999999' % int(C),
                   'KMAX_MAP': '1 %d 1999999999' % int(C)}, heff_us=175)
elif MODE == 'heff':
    prov = {10: 175.0, 200: 40.0, 400: 40.0}   # PROVISIONAL guards, labelled
    for rate in (10, 200, 400):
        C = gbps(rate)
        batch_s = FANIN * 262144 * 8.0 * (PKT_WIRE / PKT_PAY) / C
        stop = 0.1 + batch_s * 5 + 0.03
        make_cell('heff_%dg' % rate, 'cbap', rate, 262144, stop, {},
                  heff_us=prov[rate])
    print('NOTE: H_GUARD values above are PROVISIONAL placeholders for the')
    print('measurement run only; the measured H_eff replaces them before')
    print('any screening cell is generated.')
else:
    print('mode %s not enabled this round (screening/pilot gated on '
          'preflight pass)' % MODE)
    sys.exit(2)
print('%s cells generated under /work/v2_400g/' % MODE)
