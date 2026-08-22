# -*- coding: utf-8 -*-
# S3 ACTUATION PATH AUDIT -- read-only.
#
# Writes only into analysis/s3_actuation_v1/.  No source, config, parameter,
# threshold, control law or result is modified.  Nothing is re-run.
#
# INPUT SUBSTITUTION, justified before use:
#   The audited pair ckpt4_cbap_s3_out has NO actuation.csv (CBAP_ACTUATION_FILE
#   was absent from that config).  rec2_s3_on_out has 1256 actuation rows and is
#   the SAME physical outcome: all 64 per-flow FCT strings are bitwise identical
#   and the algorithm-relevant config is identical (CC_MODE 30, CBAP_ENABLE 1,
#   MIGRATION_ENABLE 1, CORE_INITIAL_RELEASE 1, RATIO 0.90, SIM_SEED 2,
#   MAX_BOOST 0.30, H_GUARD 175, Q_abs 838.86, M_safe 67072, MIN_RATE 100Mb/s).
#   Stage timestamps are therefore taken from rec2_s3_on_out; every metric
#   sourced there is labelled accordingly.
#
# FIELD SEMANTICS established from source (scratch/third.cc, rdma-hw.cc), not
# from column names -- see S3_ACTUATION_FIELD_DEFINITIONS.md.
import csv
import gzip
import hashlib
import os
import statistics as S

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_actuation_v1')
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)

ACT = os.path.join(B, 'rec2_s3_on_out/actuation.csv')
QC = os.path.join(B, 'ckpt4_cbap_s3_out/qc_trace.csv')
LTS_C = os.path.join(B, 'ckpt4_cbap_s3_out/selected_link_timeseries.csv')
LTS_D = os.path.join(B, 'ckpt4_dcqcn_s3_out/selected_link_timeseries.csv')
ARA = os.path.join(B, 'ckpt4_cbap_s3_out/applied_rate_audit.csv')

C_LINK = 10e9
T0, T1 = 2.000000000, 2.058372997      # W2 COMMON_OVERLAP
ROWS = []


def m(mid, cat, stat, val, unit, n='', sf='', sc='', formula='',
      ev='MEASURED', notes=''):
    ROWS.append(dict(metric_id=mid, category=cat, statistic=stat, value=val,
                     unit=unit, sample_count=n, source_file=sf,
                     source_columns=sc, formula=formula, evidence_type=ev,
                     notes=notes))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def st(v, name, cat, unit, sf, sc, formula, ev='MEASURED', notes=''):
    if not v:
        m(name + '.count', cat, 'count', 0, 'count', sf=sf, ev='UNAVAILABLE',
          notes='no samples')
        return
    s = sorted(v)
    n = len(s)
    for k, val in (('count', n), ('mean', S.mean(s)), ('p50', s[n // 2]),
                   ('p95', s[min(n - 1, int(.95 * (n - 1)))]),
                   ('p99', s[min(n - 1, int(.99 * (n - 1)))]),
                   ('max', s[-1]), ('min', s[0])):
        m('%s.%s' % (name, k), cat, k, val, 'count' if k == 'count' else unit,
          n=n, sf=sf, sc=sc, formula=formula, ev=ev, notes=notes)


# ---------------------------------------------------------------- B/C ------
# Per (generation, flow) collect the three stage timestamps.
ev = {}
counters = []
with open(ACT) as fh:
    for r in csv.DictReader(fh):
        stage = r['stage']
        if stage.startswith('counters_'):
            counters.append((r['time_ns'], stage))
            continue
        key = (r['generation'], r['flow_id'])
        e = ev.setdefault(key, {})
        e[stage] = dict(t=int(r['time_ns']), old=float(r['old_rate_bps']),
                        new=float(r['rate_bps']),
                        dprev=int(r['delta_prev_stage_ns']),
                        dcmd=int(r['delta_from_command_ns']),
                        seq=r['seq'])

D1, D2, D3 = [], [], []
klass = {}
PER = []
for (gen, fid), e in sorted(ev.items(), key=lambda kv: int(kv[0][0])):
    has_cmd = 'rate_command' in e
    has_snd = 'sender_rate_effect' in e
    has_arr = ('first_affected_at_bottleneck' in e) or ('arrival_at_bottleneck' in e)
    arr = e.get('first_affected_at_bottleneck') or e.get('arrival_at_bottleneck')
    d1 = d2 = d3 = ''
    if has_cmd and has_snd:
        d1 = e['sender_rate_effect']['t'] - e['rate_command']['t']
        D1.append(d1)
    if has_snd and has_arr:
        d2 = arr['t'] - e['sender_rate_effect']['t']
        D2.append(d2)
    if has_cmd and has_arr:
        d3 = arr['t'] - e['rate_command']['t']
        D3.append(d3)
    if has_cmd and has_snd and has_arr:
        k = 'APPLIED'
    elif has_cmd and has_snd and not has_arr:
        k = 'SUPERSEDED_AFTER_EFFECT'
    elif has_cmd and not has_snd:
        k = 'SUPERSEDED_BEFORE_EFFECT'
    else:
        k = 'NEVER_OBSERVED'
    klass[k] = klass.get(k, 0) + 1
    PER.append(dict(generation=gen, flow_id=fid, classification=k,
                    t_command=e.get('rate_command', {}).get('t', ''),
                    t_sender_effect=e.get('sender_rate_effect', {}).get('t', ''),
                    t_arrival=arr['t'] if arr else '',
                    D1_ns=d1, D2_ns=d2, D3_ns=d3,
                    old_rate_bps=e.get('rate_command', {}).get('old', ''),
                    new_rate_bps=e.get('rate_command', {}).get('new', '')))

st(D1, 'C.D1_command_to_sender', 'actuation', 'ns', 'actuation.csv',
   'time_ns@sender_rate_effect - time_ns@rate_command',
   'D1 = t_sender_effect - t_command')
st(D2, 'C.D2_sender_to_bottleneck', 'actuation', 'ns', 'actuation.csv',
   'time_ns@first_affected_at_bottleneck - time_ns@sender_rate_effect',
   'D2 = t_first_affected_at_bottleneck - t_sender_effect')
st(D3, 'C.D3_command_to_bottleneck', 'actuation', 'ns', 'actuation.csv',
   'time_ns@first_affected_at_bottleneck - time_ns@rate_command',
   'D3 = t_first_affected_at_bottleneck - t_command')
tot_gen = sum(klass.values())
for k, v in sorted(klass.items()):
    m('C.class.' + k, 'actuation', 'count', v, 'generations', n=tot_gen,
      sf='actuation.csv', sc='stage presence',
      formula='classified by which stages are present')
    m('C.class.' + k + '.frac', 'actuation', 'fraction',
      v / float(tot_gen) if tot_gen else 0, 'ratio', n=tot_gen, ev='DERIVED')
for t, c in counters:
    m('C.counters.' + c.split('_')[1], 'actuation', 'raw', c, 'text',
      sf='actuation.csv', sc='stage', notes='writer end-of-run counter line')

# ------------------------------------------------------------------ E ------
# B_deficit over W2, from real link bytes (both arms).
def deficit(path):
    prev = None
    dfb = 0.0
    served = 0.0
    span = 0.0
    n = 0
    with open(path) as fh:
        for r in csv.DictReader(fh):
            t = float(r['time'])
            if not (T0 <= t <= T1):
                prev = t
                continue
            tx = float(r['tx_bytes_delta'])
            dt = t - prev if prev is not None else 0.0
            prev = t
            if dt <= 0:
                continue
            n += 1
            span += dt
            served += tx
            ideal = C_LINK * dt / 8.0
            if tx < ideal:
                dfb += ideal - tx
    return dfb, served, span, n


for tag, p in (('CBAP', LTS_C), ('DCQCN', LTS_D)):
    dfb, served, span, n = deficit(p)
    m('E.B_deficit.' + tag, 'deficit', 'sum', dfb, 'B', n=n,
      sf=os.path.basename(p), sc='tx_bytes_delta,time',
      formula='integral(max(0, C - served_wire_rate) dt) over W2', ev='DERIVED')
    m('E.served_bytes.' + tag, 'deficit', 'sum', served, 'B', n=n,
      sf=os.path.basename(p), sc='tx_bytes_delta')
    m('E.span.' + tag, 'deficit', 'duration', span, 's', n=n, ev='DERIVED')
    if span > 0:
        m('E.mean_served.' + tag, 'deficit', 'mean', 8 * served / span / 1e9,
          'Gbps', ev='DERIVED', formula='8*served_bytes/span')
        m('E.deficit_rate.' + tag, 'deficit', 'mean',
          8 * dfb / span / 1e9, 'Gbps', ev='DERIVED',
          formula='8*B_deficit/span')

# counterfactual upper bounds ------------------------------------------------
dfb_c = [r['value'] for r in ROWS if r['metric_id'] == 'E.B_deficit.CBAP'][0]
dfb_d = [r['value'] for r in ROWS if r['metric_id'] == 'E.B_deficit.DCQCN'][0]
m('E.B_deficit.gap_vs_dcqcn', 'deficit', 'difference', dfb_c - dfb_d, 'B',
  ev='DERIVED', formula='B_deficit(CBAP) - B_deficit(DCQCN)')

nA = klass.get('APPLIED', 0)
if D1 and nA:
    # Upper bound: if D1 were zero, each APPLIED generation would take effect
    # D1 earlier.  Bytes NOT sent during that interval, at the full boost the
    # command was asking for, bound the recoverable bytes.
    mean_d1 = S.mean(D1)
    ub_d1 = nA * mean_d1 / 1e9 * C_LINK / 8.0
    m('E.cf.D1_zero.upper_bound_bytes', 'counterfactual', 'upper_bound',
      ub_d1, 'B', n=nA, ev='COUNTERFACTUAL',
      formula='n_APPLIED * mean(D1) * C / 8  (all links idle-equivalent)',
      notes='ceiling, not a predicted gain; assumes every ns of D1 is a full-'
            'line-rate hole, which it is not (idle fraction is 0)')
    m('E.cf.D1_zero.frac_of_deficit', 'counterfactual', 'fraction',
      ub_d1 / dfb_c if dfb_c else '', 'ratio', ev='COUNTERFACTUAL')
if D2 and nA:
    mean_d2 = S.mean(D2)
    ub_d2 = nA * mean_d2 / 1e9 * C_LINK / 8.0
    m('E.cf.D2_zero.upper_bound_bytes', 'counterfactual', 'upper_bound',
      ub_d2, 'B', n=nA, ev='COUNTERFACTUAL',
      formula='n_APPLIED * mean(D2) * C / 8',
      notes='D2 is propagation+queueing of in-flight data; it cannot be zero '
            'physically. Bound only.')
    m('E.cf.D2_zero.frac_of_deficit', 'counterfactual', 'fraction',
      ub_d2 / dfb_c if dfb_c else '', 'ratio', ev='COUNTERFACTUAL')
nsb = klass.get('SUPERSEDED_BEFORE_EFFECT', 0)
m('E.cf.superseded_before_effect.count', 'counterfactual', 'count', nsb,
  'generations', ev='MEASURED', sf='actuation.csv')

# FCT translation of the deficit, as an upper bound only
inc_bytes = 64 * 1048576.0
if dfb_c:
    m('E.cf.deficit_as_fct_ms', 'counterfactual', 'upper_bound',
      1e3 * 8 * (dfb_c - dfb_d) / C_LINK, 'ms', ev='COUNTERFACTUAL',
      formula='8*(B_deficit_CBAP - B_deficit_DCQCN)/C',
      notes='time to serve the EXCESS deficit bytes at line rate; an upper '
            'bound on the CCT component attributable to service shortfall')

# ------------------------------------------------------------------ D ------
TS = []
qc_by_t = {}
with open(QC) as fh:
    for r in csv.DictReader(fh):
        t = float(r['time_ns']) / 1e9
        if not (T0 <= t <= T1):
            continue
        qc_by_t[int(r['time_ns'])] = r
ara_by_ep = {}
if os.path.exists(ARA):
    with open(ARA) as fh:
        for r in csv.DictReader(fh):
            ara_by_ep[r['epoch']] = r
# pending age per epoch, from generation continuity
prev_gen = None
gen_start = None
for tns in sorted(qc_by_t):
    r = qc_by_t[tns]
    g = r['pending_generation']
    if g != prev_gen:
        gen_start = tns
        prev_gen = g
    age = tns - (gen_start or tns)
    ep = r['epoch_id']
    a = ara_by_ep.get(ep, {})
    TS.append(dict(time_ns=tns, generation_id=g,
                   commanded_rate=r['boost_commanded'],
                   sender_effective_rate=r['sender_effective_wire_bps'],
                   bottleneck_arrival_rate=r['arrival_safe_wire_bps'],
                   served_wire_rate='',
                   queue_bytes=r['q0'], q_stop_bytes=r['q_stop'],
                   zone=r['zone'], boost=r['boost_effective'],
                   drain=r['drain'], pending_age_ns=age,
                   superseded='', app_cap=a.get('C_effective_l', ''),
                   pacing_cap=a.get('applied_rate_sum_bps', ''),
                   min_rate_binding=a.get('flows_below_legacy_floor', '')))
# attach real served rate from the link timeseries (nearest earlier sample)
lts = []
with open(LTS_C) as fh:
    prev = None
    for r in csv.DictReader(fh):
        t = float(r['time'])
        if prev is not None and T0 <= t <= T1:
            dt = t - prev
            if dt > 0:
                lts.append((int(t * 1e9), 8 * float(r['tx_bytes_delta']) / dt))
        prev = t
li = 0
for row in TS:
    while li + 1 < len(lts) and lts[li + 1][0] <= row['time_ns']:
        li += 1
    if lts:
        row['served_wire_rate'] = '%.0f' % lts[li][1]

# pending-age stats, now that it is defined as generation continuity
st([r['pending_age_ns'] for r in TS], 'D.pending_age', 'epoch', 'ns',
   'qc_trace.csv', 'pending_generation continuity',
   'epoch_time - first epoch carrying the same pending_generation',
   ev='DERIVED',
   notes='This is NOT an actuation delay; it is how long a generation id '
         'persists in the ledger. Reported separately from D1/D2/D3.')

# ---------------------------------------------------------------- write ----
FIELDS = ['metric_id', 'category', 'statistic', 'value', 'unit',
          'sample_count', 'source_file', 'source_columns', 'formula',
          'evidence_type', 'notes']
with open(os.path.join(OUT, 'S3_ACTUATION_DECOMPOSITION.csv'), 'w',
          newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in ROWS:
        w.writerow(r)
with gzip.open(os.path.join(OUT, 'S3_ACTUATION_PER_GENERATION.csv.gz'), 'wt',
               newline='') as fh:
    if PER:
        w = csv.DictWriter(fh, fieldnames=list(PER[0].keys()))
        w.writeheader()
        for r in PER:
            w.writerow(r)
with gzip.open(os.path.join(OUT, 'S3_ACTUATION_EPOCH.csv.gz'), 'wt',
               newline='') as fh:
    if TS:
        w = csv.DictWriter(fh, fieldnames=list(TS[0].keys()))
        w.writeheader()
        for r in TS:
            w.writerow(r)

def get(mid):
    for r in ROWS:
        if r['metric_id'] == mid:
            return r['value']
    return None

print('generations=%d classes=%s' % (tot_gen, klass))
for nm in ('C.D1_command_to_sender', 'C.D2_sender_to_bottleneck',
           'C.D3_command_to_bottleneck'):
    print('%s: n=%s mean=%.0f p50=%.0f p95=%.0f max=%.0f ns'
          % (nm.split('.')[1], get(nm + '.count'), get(nm + '.mean'),
             get(nm + '.p50'), get(nm + '.p95'), get(nm + '.max')))
print('B_deficit CBAP=%.0f B  DCQCN=%.0f B  gap=%.0f B'
      % (get('E.B_deficit.CBAP'), get('E.B_deficit.DCQCN'),
         get('E.B_deficit.gap_vs_dcqcn')))
print('mean served CBAP=%.4f DCQCN=%.4f Gbps'
      % (get('E.mean_served.CBAP'), get('E.mean_served.DCQCN')))
print('deficit as CCT upper bound = %.6f ms' % get('E.cf.deficit_as_fct_ms'))
print('cf D1_zero frac_of_deficit=%s  D2_zero frac=%s'
      % (get('E.cf.D1_zero.frac_of_deficit'),
         get('E.cf.D2_zero.frac_of_deficit')))
print('pending_age mean=%.0f ns p95=%.0f ns'
      % (get('D.pending_age.mean'), get('D.pending_age.p95')))
print('rows=%d per_gen=%d epoch=%d' % (len(ROWS), len(PER), len(TS)))
