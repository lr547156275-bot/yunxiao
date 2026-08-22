# -*- coding: utf-8 -*-
# Items 1,3,4,5 on the SAME-RUN pair.  READ-ONLY.
#
# Item 1  canonical ledger with corrected semantics:
#         APPLIED / SUPERSEDED / RIGHT_CENSORED_PENDING, and the 340
#         supersessions classified by MAGNITUDE, not merely direction.
# Item 3  bottleneck busy/gap from per-packet TX_BEGIN/TX_END (nanosecond
#         union of transmit intervals), both arms, identical windows.
# Item 4  same-window deficit closure.
# Item 5  causal decision under the stated branch rules.
import csv
import gzip
import hashlib
import os
import statistics as S

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_causal_final')
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)

CB = os.path.join(B, 'sr_cbap_s3_out')
DQ = os.path.join(B, 'sr_dcqcn_s3_out')
REF_CB = os.path.join(B, 'ckpt4_cbap_s3_out')
REF_DQ = os.path.join(B, 'ckpt4_dcqcn_s3_out')

C = 10e9
DT = 10e-6
Q_ABS = 838.86e-6 * C / 8.0
Q_LOW = 0.5 * Q_ABS
RUN = 'sr_cbap_s3_out'
LINK = '0:84:1'


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def fl(d):
    p = os.path.join(d, 'flow_summary.csv')
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def f(r, k, dv=0.0):
    try:
        return float(r.get(k, dv) or dv)
    except Exception:
        return dv


# ---------------- item 2: byte-identity vs the ckpt4 reference -------------
IDENT = []
for tag, new, ref in (('CBAP', CB, REF_CB), ('DCQCN', DQ, REF_DQ)):
    for fn in ('flow_summary.csv', 'round_summary.csv', 'pfc_events.csv',
               'selected_link_timeseries.csv', 'qc_trace.csv',
               'controller_summary.csv', 'flow_plan.csv',
               'selected_flow_timeseries.csv', 'qlen.txt',
               'port_summary.csv', 'admission.csv', 'sba_events.csv',
               'applied_rate_audit.csv', 'increase_audit.csv',
               'feedback_summary.csv', 'group_round_summary.csv'):
        a, b = os.path.join(ref, fn), os.path.join(new, fn)
        if not os.path.exists(a) and not os.path.exists(b):
            continue
        sa, sb = sha(a), sha(b)
        IDENT.append(dict(arm=tag, file=fn, ref_sha=sa, new_sha=sb,
                          identical='YES' if sa == sb else 'NO'))

# windows from the SAME-RUN pair
W = {}
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    inc = [r for r in fl(d) if 0 < f(r, 'total_size_bytes') < 1e9 and f(r, 'fct') > 0]
    if inc:
        W[tag] = (min(f(r, 'start_time') for r in inc),
                  max(f(r, 'finish_time') for r in inc))
T0 = max(W['CBAP'][0], W['DCQCN'][0])
T1 = min(W['CBAP'][1], W['DCQCN'][1])
W3a = min(W['CBAP'][1], W['DCQCN'][1])
W3b = max(W['CBAP'][1], W['DCQCN'][1])
WINS = dict(W1_CBAP=W['CBAP'], W1_DCQCN=W['DCQCN'], W2=(T0, T1), W3=(W3a, W3b))

# ---------------- item 1: canonical ledger --------------------------------
ACT = os.path.join(CB, 'actuation.csv')
ev, order, counters = {}, [], {}
if os.path.exists(ACT):
    for r in csv.DictReader(open(ACT)):
        if r['stage'].startswith('counters_'):
            p = r['stage'].split('_')
            for i in range(1, len(p) - 1, 2):
                counters[p[i]] = int(p[i + 1])
            continue
        k = (RUN, LINK, r['flow_id'], r['generation'])
        if k not in ev:
            ev[k] = {}
            order.append(k)
        ev[k][r['stage']] = dict(t=int(r['time_ns']),
                                 old=float(r['old_rate_bps']),
                                 new=float(r['rate_bps']))

by_flow = {}
for k in order:
    c = ev[k].get('rate_command')
    if c:
        by_flow.setdefault(k[2], []).append((c['t'], k))
for v in by_flow.values():
    v.sort()
succ = {}
for lst in by_flow.values():
    for i, (t, k) in enumerate(lst):
        succ[k] = lst[i + 1][1] if i + 1 < len(lst) else None

LED, klass = [], {}
for k in order:
    e = ev[k]
    cmd, snd = e.get('rate_command'), e.get('sender_rate_effect')
    arr = e.get('first_affected_at_bottleneck') or e.get('arrival_at_bottleneck')
    s = succ.get(k)
    # CORRECTED SEMANTICS: a generation with no sender effect is SUPERSEDED only
    # if a successor command actually exists for that flow; otherwise the run
    # simply ended first -> RIGHT_CENSORED_PENDING.
    if cmd and snd and arr:
        cl = 'APPLIED'
    elif cmd and snd and not arr:
        cl = 'APPLIED_NO_BOTTLENECK_SIGHTING'
    elif cmd and not snd and s is not None:
        cl = 'SUPERSEDED'
    elif cmd and not snd and s is None:
        cl = 'RIGHT_CENSORED_PENDING'
    else:
        cl = 'UNMATCHED_NO_COMMAND'
    klass[cl] = klass.get(cl, 0) + 1
    LED.append(dict(run_id=k[0], link_id=k[1], flow_id=k[2], generation_id=k[3],
                    classification=cl,
                    t_command=cmd['t'] if cmd else '',
                    t_sender_effect=snd['t'] if snd else '',
                    t_arrival=arr['t'] if arr else '',
                    D1_ns=(snd['t'] - cmd['t']) if (cmd and snd) else '',
                    D2_ns=(arr['t'] - snd['t']) if (snd and arr) else '',
                    D3_ns=(arr['t'] - cmd['t']) if (cmd and arr) else '',
                    old_target_bps=cmd['old'] if cmd else '',
                    new_target_bps=cmd['new'] if cmd else '',
                    successor_generation=s[3] if s else '',
                    successor_target_bps=(ev[s]['rate_command']['new']
                                          if s and 'rate_command' in ev[s] else ''),
                    successor_t_command=(ev[s]['rate_command']['t']
                                         if s and 'rate_command' in ev[s] else '')))

# ---------------- item 1b: magnitude classification of SUPERSEDED ---------
MAG = []
mag_count = {}
for row in LED:
    if row['classification'] != 'SUPERSEDED':
        continue
    old = row['old_target_bps']
    new = row['new_target_bps']
    sc = row['successor_target_bps']
    tc = row['t_command']
    ts = row['successor_t_command']
    if '' in (old, new, sc, tc, ts):
        cl = 'indeterminate_missing_field'
    else:
        rising = new > old
        if rising:
            # successor at least as aggressive -> nothing lost
            cl = 'lost_increase' if sc < new else 'redundant_dominated'
        elif new < old:
            cl = 'lost_decrease' if sc > new else 'redundant_dominated'
        else:
            cl = 'flat_no_change'
    mag_count[cl] = mag_count.get(cl, 0) + 1
    dur = (ts - tc) if ('' not in (ts, tc)) else ''
    lost = ''
    if cl in ('lost_increase', 'lost_decrease') and dur != '':
        lost = abs(new - sc) * dur / 1e9 / 8.0
    MAG.append(dict(run_id=row['run_id'], flow_id=row['flow_id'],
                    generation_id=row['generation_id'],
                    magnitude_class=cl, old_target_bps=old,
                    new_target_bps=new, successor_target_bps=sc,
                    override_duration_ns=dur,
                    attributable_bytes_upper=lost))

# ---------------- item 3: serializer busy / gap ---------------------------
BG = []
BUSY = {}
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'tx_serialization.csv')
    if not os.path.exists(p):
        BUSY[tag] = None
        continue
    beg, pairs = {}, []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            key = (r['link_id'], r['node_id'], r['if_index'], r['packet_uid'])
            t = int(r['time_ns'])
            if r['event'] == 'TX_BEGIN':
                beg[key] = (t, int(r['packet_bytes']))
            elif r['event'] == 'TX_END' and key in beg:
                b, nb = beg.pop(key)
                pairs.append((b, t, nb))
    pairs.sort()
    for wn, (a, b) in WINS.items():
        an, bn = int(a * 1e9), int(b * 1e9)
        sel = [(s, e, nb) for (s, e, nb) in pairs if s >= an and e <= bn]
        if not sel:
            continue
        # union of transmit intervals -> true busy time
        busy = 0
        gaps = []
        cs, ce = sel[0][0], sel[0][1]
        wire = sel[0][2]
        for (s, e, nb) in sel[1:]:
            wire += nb
            if s > ce:
                busy += ce - cs
                gaps.append(s - ce)
                cs, ce = s, e
            else:
                ce = max(ce, e)
        busy += ce - cs
        span = bn - an
        gs = sorted(gaps)
        BG.append(dict(algorithm=tag, window=wn, packets=len(sel),
                       span_ns=span, busy_ns=busy,
                       busy_fraction='%.9f' % (busy / float(span)) if span else '',
                       gap_count=len(gaps), gap_total_ns=sum(gaps),
                       gap_fraction='%.9f' % (sum(gaps) / float(span)) if span else '',
                       gap_mean_ns='%.1f' % S.mean(gs) if gs else '',
                       gap_p50_ns=gs[len(gs) // 2] if gs else '',
                       gap_p95_ns=gs[min(len(gs) - 1, int(.95 * (len(gs) - 1)))] if gs else '',
                       gap_max_ns=gs[-1] if gs else '',
                       wire_bytes=wire,
                       served_wire_bps='%.0f' % (8.0 * wire / (span / 1e9)) if span else ''))
        if wn == 'W2':
            BUSY[tag] = busy / float(span)

# ---------------- item 4: same-window deficit ----------------------------
DEF = []
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'selected_link_timeseries.csv')
    if not os.path.exists(p):
        continue
    for wn, (a, b) in WINS.items():
        dfb = served = 0.0
        n = 0
        for r in csv.DictReader(open(p)):
            t = float(r['time'])
            if not (a <= t <= b):
                continue
            n += 1
            tx = float(r['tx_bytes_delta'])
            served += tx
            ideal = C * DT / 8.0
            if tx < ideal:
                dfb += ideal - tx
        span = b - a
        DEF.append(dict(algorithm=tag, window=wn, samples=n,
                        span_s='%.9f' % span, served_bytes='%.0f' % served,
                        ideal_bytes='%.0f' % (C * span / 8.0),
                        deficit_bytes='%.0f' % dfb,
                        deficit_frac='%.9f' % (dfb / (C * span / 8.0)) if span else '',
                        mean_served_gbps='%.6f' % (8 * served / span / 1e9) if span else ''))
dc = {r['window']: float(r['deficit_bytes']) for r in DEF if r['algorithm'] == 'CBAP'}
dd = {r['window']: float(r['deficit_bytes']) for r in DEF if r['algorithm'] == 'DCQCN'}
EX = []
for wn in ('W2',):
    if wn in dc and wn in dd:
        ex = dc[wn] - dd[wn]
        EX.append(dict(window=wn, cbap_deficit_bytes='%.0f' % dc[wn],
                       dcqcn_deficit_bytes='%.0f' % dd[wn],
                       excess_deficit_bytes='%.0f' % ex,
                       excess_as_ms='%.6f' % (8 * ex / C * 1e3),
                       tail_gap_ms='1.033590',
                       ratio='%.4f' % ((8 * ex / C * 1e3) / 1.033590)))

# ---------------- write ---------------------------------------------------
def wcsv(name, rows, gz=False):
    p = os.path.join(OUT, name)
    if not rows:
        open(p if not gz else p, 'w').write('')
        return
    op = gzip.open(p, 'wt', newline='') if gz else open(p, 'w', newline='')
    with op as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


wcsv('ACTUATION_LEDGER_CANONICAL.csv.gz', LED, gz=True)
wcsv('SUPERSESSION_MAGNITUDE_AUDIT.csv', MAG)
wcsv('SERIALIZER_BUSY_GAP_AUDIT.csv.gz', BG, gz=True)
wcsv('S3_SAME_WINDOW_DEFICIT.csv', DEF)
wcsv('S3_SAME_WINDOW_EXCESS.csv', EX)
wcsv('_identity.csv', IDENT)

print('=== item 2 identity ===')
nid = sum(1 for r in IDENT if r['identical'] == 'YES')
print('files compared=%d identical=%d differ=%d'
      % (len(IDENT), nid, len(IDENT) - nid))
for r in IDENT:
    if r['identical'] == 'NO':
        print('  DIFFER %s %s' % (r['arm'], r['file']))
print('=== windows ===')
for k, (a, b) in WINS.items():
    print('  %-10s [%.9f, %.9f] dur=%.6f ms' % (k, a, b, 1e3 * (b - a)))
print('=== item 1 ledger ===')
print('  total=%d  %s' % (len(LED), klass))
print('  writer counters=%s' % counters)
print('=== item 1b magnitude ===')
print('  %s' % mag_count)
li = [r for r in MAG if r['magnitude_class'] == 'lost_increase']
lb = sum(r['attributable_bytes_upper'] for r in li
         if r['attributable_bytes_upper'] != '')
print('  lost_increase n=%d attributable_bytes_upper=%.0f' % (len(li), lb))
print('=== item 3 busy/gap (W2) ===')
for r in BG:
    if r['window'] == 'W2':
        print('  %-6s pkts=%-7s busy=%s gap_frac=%s gaps=%s gap_mean=%s served=%s'
              % (r['algorithm'], r['packets'], r['busy_fraction'],
                 r['gap_fraction'], r['gap_count'], r['gap_mean_ns'],
                 r['served_wire_bps']))
print('=== item 4 deficit ===')
for r in DEF:
    if r['window'] == 'W2':
        print('  %-6s deficit=%s B frac=%s mean=%s Gbps'
              % (r['algorithm'], r['deficit_bytes'], r['deficit_frac'],
                 r['mean_served_gbps']))
for r in EX:
    print('  excess=%s B -> %s ms  vs tail 1.033590 ms  ratio=%s'
          % (r['excess_deficit_bytes'], r['excess_as_ms'], r['ratio']))
