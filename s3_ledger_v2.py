# -*- coding: utf-8 -*-
# Items 1,4,5,6: canonical ledger, count reconciliation, D2 split,
# supersession semantics, effect-aligned tracking.  READ-ONLY.
import csv
import gzip
import hashlib
import os
import statistics as S

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_actuation_v2')
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
ACT = os.path.join(B, 'rec2_s3_on_out/actuation.csv')
QC = os.path.join(B, 'ckpt4_cbap_s3_out/qc_trace.csv')
LTS = os.path.join(B, 'ckpt4_cbap_s3_out/selected_link_timeseries.csv')

C = 10e9
DT = 10e-6                     # CRFM_TRACE_SAMPLE_US = 10, verified uniform
T0, T1 = 2.000000000, 2.058372997
Q_ABS = 838.86e-6 * C / 8.0
Q_LOW = 0.5 * Q_ABS
RUN_ID = 'rec2_s3_on_out'
LINK_ID = '0:84:1'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


# ---------------- item 1: canonical ledger ---------------------------------
raw = []
counters = {}
with open(ACT) as fh:
    for r in csv.DictReader(fh):
        if r['stage'].startswith('counters_'):
            p = r['stage'].split('_')
            for i in range(1, len(p) - 1, 2):
                counters[p[i]] = int(p[i + 1])
            continue
        raw.append(r)

ev = {}
order = []
for r in raw:
    key = (RUN_ID, LINK_ID, r['flow_id'], r['generation'])
    if key not in ev:
        ev[key] = {}
        order.append(key)
    ev[key][r['stage']] = dict(t=int(r['time_ns']),
                               old=float(r['old_rate_bps']),
                               new=float(r['rate_bps']),
                               seq=r['seq'])

# per-flow chronological chain, so a generation's replacement is well defined
by_flow = {}
for key in order:
    cmd = ev[key].get('rate_command')
    if cmd:
        by_flow.setdefault(key[2], []).append((cmd['t'], key))
for fid in by_flow:
    by_flow[fid].sort()
repl = {}
for fid, lst in by_flow.items():
    for i, (t, key) in enumerate(lst):
        repl[key] = lst[i + 1][1] if i + 1 < len(lst) else None

LED = []
klass = {}
for key in order:
    e = ev[key]
    cmd = e.get('rate_command')
    snd = e.get('sender_rate_effect')
    arr = e.get('first_affected_at_bottleneck') or e.get('arrival_at_bottleneck')
    if cmd and snd and arr:
        k = 'APPLIED'
    elif cmd and snd and not arr:
        k = 'SUPERSEDED_AFTER_EFFECT'
    elif cmd and not snd:
        k = 'SUPERSEDED_BEFORE_EFFECT'
    else:
        k = 'UNMATCHED_NO_COMMAND'
    klass[k] = klass.get(k, 0) + 1
    d1 = (snd['t'] - cmd['t']) if (cmd and snd) else ''
    d2 = (arr['t'] - snd['t']) if (snd and arr) else ''
    d3 = (arr['t'] - cmd['t']) if (cmd and arr) else ''
    rk = repl.get(key)
    LED.append(dict(run_id=key[0], link_id=key[1], flow_id=key[2],
                    generation_id=key[3], classification=k,
                    t_command=cmd['t'] if cmd else '',
                    t_sender_effect=snd['t'] if snd else '',
                    t_arrival=arr['t'] if arr else '',
                    D1_ns=d1, D2_ns=d2, D3_ns=d3,
                    old_rate_bps=cmd['old'] if cmd else '',
                    new_rate_bps=cmd['new'] if cmd else '',
                    replacement_generation=rk[3] if rk else '',
                    replacement_t_command=(ev[rk]['rate_command']['t']
                                           if rk and 'rate_command' in ev[rk] else ''),
                    replacement_rate_bps=(ev[rk]['rate_command']['new']
                                          if rk and 'rate_command' in ev[rk] else '')))

# writer-equivalent recount: a command displacing a still-pending entry
disp = 0
pending_keys = set()
for fid, lst in sorted(by_flow.items()):
    for t, key in lst:
        e = ev[key]
        if key in pending_keys:
            pass
        # emulate: displaced if the PREVIOUS command for this flow had not yet
        # been seen at the sender when this one was issued
        pass
prev_by_flow = {}
for fid, lst in sorted(by_flow.items()):
    for t, key in lst:
        p = prev_by_flow.get(fid)
        if p is not None:
            pe = ev[p]
            psnd = pe.get('sender_rate_effect')
            if (psnd is None) or (psnd['t'] > t):
                disp += 1
        prev_by_flow[fid] = key

# ---------------- item 5: supersession semantics --------------------------
qrows = []
with open(QC) as fh:
    for r in csv.DictReader(fh):
        t = int(r['time_ns'])
        qrows.append((t, float(r['q0']), float(r['q_stop']), r['zone'],
                      float(r['boost_effective']), float(r['drain'])))
qrows.sort()
qt = [x[0] for x in qrows]


def qstate(tns):
    lo, hi = 0, len(qt) - 1
    if not qt or tns < qt[0]:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if qt[mid] <= tns:
            lo = mid
        else:
            hi = mid - 1
    return qrows[lo]


sup_class = {}
SUPC = []
for row in LED:
    if not row['classification'].startswith('SUPERSEDED'):
        continue
    tc = row['t_command']
    old = row['old_rate_bps']
    new = row['new_rate_bps']
    rnew = row['replacement_rate_bps']
    st = qstate(tc) if tc else None
    zone = st[3] if st else ''
    q0 = st[1] if st else ''
    direction = ''
    if new != '' and old != '':
        direction = 'increase' if new > old else ('decrease' if new < old else 'flat')
    rdir = ''
    if rnew != '' and new != '':
        rdir = 'higher' if rnew > new else ('lower' if rnew < new else 'same')
    if zone in ('YELLOW-DRAIN', 'RED'):
        k = 'safety_correction'
    elif direction == 'increase' and rdir == 'lower':
        k = 'harmful_lost_increase' if (q0 != '' and q0 < Q_LOW) else 'indeterminate'
    elif direction == 'increase' and rdir in ('higher', 'same'):
        k = 'redundant_same_direction'
    elif direction == 'decrease' and rdir == 'higher':
        k = 'harmful_lost_decrease'
    elif direction == 'decrease':
        k = 'redundant_same_direction'
    else:
        k = 'indeterminate'
    sup_class[k] = sup_class.get(k, 0) + 1
    dur = (row['replacement_t_command'] - tc) if (row['replacement_t_command']
                                                 != '' and tc != '') else ''
    lost = ''
    if k == 'harmful_lost_increase' and dur != '' and new != '' and rnew != '':
        lost = (new - rnew) * dur / 1e9 / 8.0
    SUPC.append(dict(run_id=row['run_id'], flow_id=row['flow_id'],
                     generation_id=row['generation_id'],
                     sup_class=k, zone_at_command=zone, q0_at_command=q0,
                     direction=direction, replacement_direction=rdir,
                     old_rate_bps=old, new_rate_bps=new,
                     replacement_rate_bps=rnew,
                     duration_ns=dur, lost_bytes_upper=lost))

# ---------------- item 4: D2 sub-split ------------------------------------
# Available sub-stages: sender_rate_effect -> arrival_at_bottleneck ->
# first_affected_at_bottleneck.  arrival = QbbEnqueue (reaches bottleneck queue),
# first_affected = EgressDequeue (leaves it).  So:
#   D2a = arrival - sender_effect      : propagation + upstream queueing
#   D2b = first_affected - arrival     : bottleneck egress queueing (serialization)
D2A, D2B = [], []
for key in order:
    e = ev[key]
    snd = e.get('sender_rate_effect')
    a1 = e.get('arrival_at_bottleneck')
    a2 = e.get('first_affected_at_bottleneck')
    if snd and a1:
        D2A.append(a1['t'] - snd['t'])
    if a1 and a2:
        D2B.append(a2['t'] - a1['t'])

D2ROWS = []


def wr(name, v, note):
    if not v:
        D2ROWS.append(dict(stage=name, count=0, mean_ns='', p50_ns='',
                           p95_ns='', max_ns='', evidence='UNAVAILABLE',
                           note=note))
        return
    s = sorted(v)
    n = len(s)
    D2ROWS.append(dict(stage=name, count=n, mean_ns='%.0f' % S.mean(s),
                       p50_ns=s[n // 2], p95_ns=s[min(n - 1, int(.95 * (n - 1)))],
                       max_ns=s[-1], evidence='MEASURED', note=note))


wr('D2a_sender_to_bottleneck_arrival', D2A,
   'propagation + upstream queueing; physical, not controller-optimisable')
wr('D2b_bottleneck_queue_to_egress', D2B,
   'bottleneck egress queueing + serialization; physical lower bound')
wr('D2_total_sender_to_first_affected',
   [a + b for a, b in zip(D2A, D2B)] if len(D2A) == len(D2B) else [],
   'sum of the two measured sub-stages')

# ---------------- item 6: effect-aligned tracking -------------------------
served = []
prev = None
with open(LTS) as fh:
    for r in csv.DictReader(fh):
        t = float(r['time'])
        if prev is not None and T0 <= t <= T1:
            served.append((int(t * 1e9), 8 * float(r['tx_bytes_delta']) / DT,
                           float(r['queue_bytes'])))
        prev = t
sv_t = [x[0] for x in served]


def svlook(tns):
    lo, hi = 0, len(sv_t) - 1
    if not sv_t or tns < sv_t[0]:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sv_t[mid] <= tns:
            lo = mid
        else:
            hi = mid - 1
    return served[lo]


TRK = []
lag_bytes = 0.0
lag_epochs = 0
for (t, q0, qstop, zone, boost, drain) in qrows:
    if not (T0 * 1e9 <= t <= T1 * 1e9):
        continue
    sv = svlook(t)
    sr = sv[1] if sv else ''
    latest_target = C + boost - drain
    err = (latest_target - sr) if sr != '' else ''
    safe_green = (zone == 'GREEN' and q0 < Q_LOW)
    behind = bool(safe_green and sr != '' and sr < C * 0.99)
    if behind:
        lag_epochs += 1
        lag_bytes += (C - sr) * DT / 8.0
    TRK.append(dict(time_ns=t, latest_desired_target_bps='%.0f' % latest_target,
                    served_wire_bps=('%.0f' % sr) if sr != '' else '',
                    signed_tracking_error_bps=('%.0f' % err) if err != '' else '',
                    queue_bytes=q0, q_stop_bytes=qstop, zone=zone,
                    boost_bps=boost, drain_bps=drain,
                    safe_green=1 if safe_green else 0,
                    behind_target=1 if behind else 0))

# ---------------- write ---------------------------------------------------
with gzip.open(os.path.join(OUT, 'ACTUATION_LEDGER_CANONICAL.csv.gz'), 'wt',
               newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(LED[0].keys()))
    w.writeheader()
    for r in LED:
        w.writerow(r)
with gzip.open(os.path.join(OUT, 'SUPERSESSION_CLASSIFICATION.csv.gz'), 'wt',
               newline='') as fh:
    if SUPC:
        w = csv.DictWriter(fh, fieldnames=list(SUPC[0].keys()))
        w.writeheader()
        for r in SUPC:
            w.writerow(r)
with open(os.path.join(OUT, 'D2_STAGE_DECOMPOSITION.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(D2ROWS[0].keys()))
    w.writeheader()
    for r in D2ROWS:
        w.writerow(r)
with gzip.open(os.path.join(OUT, 'EFFECT_ALIGNED_TRACKING.csv.gz'), 'wt',
               newline='') as fh:
    if TRK:
        w = csv.DictWriter(fh, fieldnames=list(TRK[0].keys()))
        w.writeheader()
        for r in TRK:
            w.writerow(r)

tot = len(LED)
print('LEDGER total=%d' % tot)
print('classes=%s' % klass)
print('sum(classes)=%d  closes=%s' % (sum(klass.values()),
                                      sum(klass.values()) == tot))
print('writer counters=%s' % counters)
print('recount displaced(prev cmd unseen at sender when next issued)=%d' % disp)
print('supersession classes=%s' % sup_class)
hli = [r for r in SUPC if r['sup_class'] == 'harmful_lost_increase']
lb = sum(r['lost_bytes_upper'] for r in hli if r['lost_bytes_upper'] != '')
print('harmful_lost_increase n=%d lost_bytes_upper=%.0f' % (len(hli), lb))
print('D2 split:')
for r in D2ROWS:
    print('  %-38s n=%-5s mean=%-9s p95=%-9s max=%s'
          % (r['stage'], r['count'], r['mean_ns'], r['p95_ns'], r['max_ns']))
print('tracking rows=%d  safe_green_behind_epochs=%d  lag_bytes=%.0f'
      % (len(TRK), lag_epochs, lag_bytes))
sg = sum(1 for r in TRK if r['safe_green'] == 1)
print('safe_green epochs=%d of %d' % (sg, len(TRK)))
