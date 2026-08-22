# -*- coding: utf-8 -*-
# Items 1-5: gap event classification, pacer rearm audit, QP phase audit,
# offline phase counterfactual, completion components.  READ-ONLY.
import csv
import gzip
import hashlib
import os
import random
import statistics as S

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_gap_causal')
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
CB = os.path.join(B, 'sr_cbap_s3_out')
DQ = os.path.join(B, 'sr_dcqcn_s3_out')

C = 10e9
DT = 10e-6
T0, T1 = 2.000000000, 2.058372997
T0N, T1N = int(T0 * 1e9), int(T1 * 1e9)


def sha(p):
    if not os.path.exists(p):
        return 'ABSENT'
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def pairs_of(d):
    """Per-packet (begin, end, bytes) on the bottleneck, W2 only."""
    p = os.path.join(d, 'tx_serialization.csv')
    if not os.path.exists(p):
        return []
    beg, out = {}, []
    with open(p) as fh:
        for r in csv.DictReader(fh):
            k = (r['link_id'], r['node_id'], r['if_index'], r['packet_uid'])
            t = int(r['time_ns'])
            if r['event'] == 'TX_BEGIN':
                beg[k] = (t, int(r['packet_bytes']))
            elif r['event'] == 'TX_END' and k in beg:
                b, nb = beg.pop(k)
                out.append((b, t, nb))
    out.sort()
    return [x for x in out if x[0] >= T0N and x[1] <= T1N]


def gaps_of(pr):
    """Gaps between the union of transmit intervals."""
    if not pr:
        return []
    g = []
    ce = pr[0][1]
    for (s, e, nb) in pr[1:]:
        if s > ce:
            g.append((ce, s, s - ce))
        ce = max(ce, e)
    return g


# time-indexed queue from the link timeseries (both arms have it)
def queue_series(d):
    p = os.path.join(d, 'selected_link_timeseries.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p)):
        t = float(r['time'])
        if T0 <= t <= T1:
            out.append((int(t * 1e9), float(r['queue_bytes'])))
    out.sort()
    return out


def lookup(series, tns):
    if not series:
        return None
    lo, hi = 0, len(series) - 1
    if tns < series[0][0]:
        return series[0][1]
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if series[mid][0] <= tns:
            lo = mid
        else:
            hi = mid - 1
    return series[lo][1]


# CBAP-only auxiliary series
def act_events(d):
    p = os.path.join(d, 'actuation.csv')
    cmd, snd, arr = [], [], []
    if not os.path.exists(p):
        return cmd, snd, arr
    for r in csv.DictReader(open(p)):
        if r['stage'].startswith('counters_'):
            continue
        t = int(r['time_ns'])
        if r['stage'] == 'rate_command':
            cmd.append(t)
        elif r['stage'] == 'sender_rate_effect':
            snd.append(t)
        elif r['stage'] in ('first_affected_at_bottleneck',
                            'arrival_at_bottleneck'):
            arr.append(t)
    return sorted(cmd), sorted(snd), sorted(arr)


def nearest_before(arr, t):
    if not arr:
        return ''
    lo, hi = 0, len(arr) - 1
    if t < arr[0]:
        return ''
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if arr[mid] <= t:
            lo = mid
        else:
            hi = mid - 1
    return t - arr[lo]


def ara_series(d):
    p = os.path.join(d, 'applied_rate_audit.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p)):
        try:
            out.append((int(r['epoch']), float(r['rate_clamp_delta_sum_bps']),
                        float(r['actual_arrival_excess_bps']),
                        float(r['applied_rate_sum_bps']),
                        float(r['actual_tx_rate_sum_bps'])))
        except Exception:
            continue
    return out


# ---------------- item 2: exclusive gap classification --------------------
GAPROWS = []
CLS = {}
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    pr = pairs_of(d)
    gp = gaps_of(pr)
    qs = queue_series(d)
    cmd, snd, arr = act_events(d)
    ara = ara_series(d)
    ara_clamp = S.mean([x[1] for x in ara]) if ara else ''
    ara_exc = S.mean([x[2] for x in ara]) if ara else ''
    for (gs, ge, dur) in gp:
        q = lookup(qs, gs)
        # EXCLUSIVE classification
        if q is not None and q > 0:
            k = 'A_bottleneck_queue_nonempty_port_idle'
        elif gs <= T0N + 1000 or ge >= T1N - 1000:
            k = 'E_simulation_boundary'
        else:
            # queue empty at the bottleneck.  Distinguish pacing-limited from
            # source-limited using the sender-side evidence available:
            # if the gap is shorter than one packet serialization time it is
            # in-flight/propagation; otherwise the senders were not allowed to
            # send (pacing) -- CBAP has actuation events to corroborate.
            one_pkt_ns = 1048 * 8 * 1e9 / C          # 838 ns
            if dur < one_pkt_ns:
                k = 'D_propagation_inflight'
            else:
                k = 'B_pacing_gap_queue_empty'
        CLS.setdefault(tag, {}).setdefault(k, [0, 0])
        CLS[tag][k][0] += 1
        CLS[tag][k][1] += dur
        GAPROWS.append(dict(algorithm=tag, gap_start_ns=gs, gap_end_ns=ge,
                            duration_ns=dur, link_id='0:84:1',
                            bottleneck_queue_bytes=q if q is not None else '',
                            classification=k,
                            ns_since_last_rate_command=nearest_before(cmd, gs),
                            ns_since_last_sender_effect=nearest_before(snd, gs),
                            ns_since_last_bottleneck_arrival=nearest_before(arr, gs),
                            mean_rate_clamp_delta_bps=ara_clamp,
                            mean_actual_arrival_excess_bps=ara_exc))

# ---------------- item 1: pacer rearm audit (CBAP) ------------------------
# Source-established: ChangeRate's CBAP branch sets
#   m_nextAvail = max(now, lastTxTimeNs + gap(lastPktSize, new_rate))
# i.e. anchored to THIS QP's own last transmit, not to `now`.
REARM = []
p = os.path.join(CB, 'rate_transition.csv')
have_rt = os.path.exists(p) and sum(1 for _ in open(p)) > 1
p2 = os.path.join(CB, 'actuation.csv')
if os.path.exists(p2):
    per = {}
    for r in csv.DictReader(open(p2)):
        if r['stage'].startswith('counters_'):
            continue
        k = (r['flow_id'], r['generation'])
        per.setdefault(k, {})[r['stage']] = int(r['time_ns'])
    # group commands by epoch (5 us control epoch) to test clustering
    byepoch = {}
    for (fid, gen), st in per.items():
        tc = st.get('rate_command')
        if tc is None:
            continue
        byepoch.setdefault(tc // 5000, []).append((fid, gen, tc,
                                                   st.get('sender_rate_effect')))
    for ep, lst in sorted(byepoch.items()):
        sends = [x[3] for x in lst if x[3] is not None]
        REARM.append(dict(epoch_5us=ep, commands_in_epoch=len(lst),
                          qps_with_sender_effect=len(sends),
                          sender_effect_spread_ns=(max(sends) - min(sends))
                          if len(sends) > 1 else '',
                          sender_effect_min_ns=min(sends) if sends else '',
                          sender_effect_max_ns=max(sends) if sends else '',
                          anchor='lastTxTimeNs+gap(new_rate)',
                          resets_to_now='NO',
                          evidence='source: ChangeRate CBAP branch'))

# ---------------- item 3: per-QP phase audit -----------------------------
PHASE = []
CONC = []
for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    p = os.path.join(d, 'tx_serialization.csv')
    if not os.path.exists(p):
        continue
    # per-packet begins on the bottleneck are aggregate, not per-QP.
    # Per-QP send times come from selected_flow_timeseries (rate) only, so
    # per-QP inter-packet intervals at the bottleneck are UNAVAILABLE.
    pr = pairs_of(d)
    begins = [x[0] for x in pr]
    iv = [begins[i] - begins[i - 1] for i in range(1, len(begins))]
    s = sorted(iv)
    if s:
        PHASE.append(dict(algorithm=tag, scope='aggregate_bottleneck',
                          packets=len(pr), interval_count=len(s),
                          interval_mean_ns='%.1f' % S.mean(s),
                          interval_p50_ns=s[len(s) // 2],
                          interval_p95_ns=s[min(len(s) - 1, int(.95 * (len(s) - 1)))],
                          interval_max_ns=s[-1],
                          expected_interval_ns='%.1f' % (1048 * 8 * 1e9 / C),
                          note='aggregate arrival interval at the bottleneck; '
                               'per-QP intervals are UNAVAILABLE (recorder is '
                               'per-link, packet_uid is not a QP id)'))
    for bin_ns in (1, 10, 100, 1000):
        cnt = {}
        for b in begins:
            cnt[b // bin_ns] = cnt.get(b // bin_ns, 0) + 1
        v = sorted(cnt.values())
        CONC.append(dict(algorithm=tag, bin_ns=bin_ns,
                         occupied_bins=len(v),
                         max_packets_in_bin=v[-1],
                         p95_packets_in_bin=v[min(len(v) - 1, int(.95 * (len(v) - 1)))],
                         mean_packets_in_bin='%.4f' % S.mean(v)))

# ---------------- item 4: offline serializer replay ----------------------
CF = []
pr_cb = pairs_of(CB)
if pr_cb:
    sizes = [x[2] for x in pr_cb]
    n = len(pr_cb)
    span = T1N - T0N
    total_ser = sum(nb * 8 * 1e9 / C for nb in sizes)
    real_busy = 0
    ce = pr_cb[0][1]
    cs = pr_cb[0][0]
    for (s2, e2, nb) in pr_cb[1:]:
        if s2 > ce:
            real_busy += ce - cs
            cs = s2
        ce = max(ce, e2)
    real_busy += ce - cs
    random.seed(12345)
    for trial in range(50):
        # keep per-packet sizes and count; only re-phase the arrival instants
        # uniformly across the window (preserves total bytes and rate)
        starts = sorted(random.uniform(T0N, T1N - 900) for _ in range(n))
        busy = 0
        gaps = []
        cur_e = None
        cur_s = None
        for i, st_ in enumerate(starts):
            dur = sizes[i] * 8 * 1e9 / C
            s2, e2 = st_, st_ + dur
            if cur_e is None:
                cur_s, cur_e = s2, e2
                continue
            if s2 > cur_e:
                busy += cur_e - cur_s
                gaps.append(s2 - cur_e)
                cur_s, cur_e = s2, e2
            else:
                cur_e = max(cur_e, e2)
        busy += cur_e - cur_s
        gs2 = sorted(gaps)
        CF.append(dict(trial=trial, mode='uniform_rephase',
                       packets=n, span_ns=span,
                       busy_ns='%.0f' % busy,
                       busy_fraction='%.9f' % (busy / float(span)),
                       gap_count=len(gaps),
                       gap_total_ns='%.0f' % sum(gaps),
                       gap_fraction='%.9f' % (sum(gaps) / float(span)),
                       gap_p95_ns='%.0f' % gs2[min(len(gs2) - 1, int(.95 * (len(gs2) - 1)))] if gs2 else '',
                       gap_max_ns='%.0f' % gs2[-1] if gs2 else '',
                       real_busy_fraction='%.9f' % (real_busy / float(span)),
                       improvement_vs_real='%.9f' % ((busy - real_busy) / float(span)),
                       evidence='OFFLINE_COUNTERFACTUAL'))

# ---------------- write --------------------------------------------------
def wcsv(name, rows, gz=False):
    p = os.path.join(OUT, name)
    if not rows:
        open(p, 'w').write('')
        return
    op = gzip.open(p, 'wt', newline='') if gz else open(p, 'w', newline='')
    with op as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


wcsv('S3_GAP_EVENT_CLASSIFICATION.csv.gz', GAPROWS, gz=True)
wcsv('S3_PACER_REARM_AUDIT.csv.gz', REARM, gz=True)
wcsv('S3_QP_PHASE_AUDIT.csv.gz', PHASE, gz=True)
wcsv('S3_PHASE_CONCENTRATION.csv', CONC)
wcsv('S3_PHASE_COUNTERFACTUAL.csv', CF)

print('=== item 2: exclusive gap classification (W2) ===')
for tag in ('CBAP', 'DCQCN'):
    tot_n = sum(v[0] for v in CLS.get(tag, {}).values())
    tot_t = sum(v[1] for v in CLS.get(tag, {}).values())
    print('  %s total gaps=%d total_gap_ns=%d' % (tag, tot_n, tot_t))
    for k, (cn, ct) in sorted(CLS.get(tag, {}).items()):
        print('    %-42s n=%-5d time=%-9d %.2f%% of gap time'
              % (k, cn, ct, 100.0 * ct / tot_t if tot_t else 0))
print('=== item 1: pacer rearm ===')
print('  rate_transition.csv usable: %s' % have_rt)
print('  epochs with commands=%d' % len(REARM))
sp = [r['sender_effect_spread_ns'] for r in REARM
      if r['sender_effect_spread_ns'] != '']
if sp:
    print('  sender_effect spread within an epoch: mean=%.0f p95=%.0f max=%d ns'
          % (S.mean(sp), sorted(sp)[int(.95 * (len(sp) - 1))], max(sp)))
print('  ChangeRate anchor = lastTxTimeNs + gap(new_rate); resets_to_now = NO')
print('=== item 3: concentration ===')
for r in CONC:
    print('  %-6s bin=%-5s occupied=%-7s max_in_bin=%-4s mean=%s'
          % (r['algorithm'], r['bin_ns'], r['occupied_bins'],
             r['max_packets_in_bin'], r['mean_packets_in_bin']))
print('=== item 4: offline counterfactual (50 trials) ===')
if CF:
    bf = [float(r['busy_fraction']) for r in CF]
    gf = [float(r['gap_fraction']) for r in CF]
    print('  real busy_fraction   = %s' % CF[0]['real_busy_fraction'])
    print('  replay busy_fraction : mean=%.9f min=%.9f max=%.9f'
          % (S.mean(bf), min(bf), max(bf)))
    print('  replay gap_fraction  : mean=%.9f' % S.mean(gf))
    print('  improvement vs real  : mean=%.9f' % S.mean(
        [float(r['improvement_vs_real']) for r in CF]))
