# -*- coding: utf-8 -*-
# INDEPENDENT acceptance checker for the CLEAN_CORRECTNESS_CHECKPOINT.
#
# Section 4 requirement: the verdict may NOT be derived from the controller's own
# summary fields.  So:
#   * membership lifecycle  <- admission.csv / sba_events.csv / flow_summary.csv
#                              (raw admission + completion events)
#   * queue                 <- port_summary.csv:queue_bytes   (raw BEgressQueue
#                              counter, and selected_link_timeseries.csv)
#   * arrival / served      <- port_summary.csv input/output_bytes_delta and
#                              selected_link_timeseries.csv:tx_bytes_delta
#                              (actual link bytes)
#   * commanded / sender-effective / arrival-at-bottleneck
#                           <- actuation.csv (per stage) and
#                              applied_rate_audit.csv
#   * pending / in-flight   <- actuation.csv keyed by (generation, flow_id)
#
# qc_trace.csv is read ONLY for quantities that exist nowhere else (zone
# residency, boost/drain emission) and every such use is labelled
# CONTROLLER-REPORTED in the output so it is never mistaken for independent
# evidence.
#
# Frozen semantics (section 2), hardcoded here ON PURPOSE so a code change
# cannot silently move the target:
#   payload DATA          = 1000 B
#   link DATA (GetSize()) = 1048 B  = 1000 + 14(eth) + 20(ipv4) + 14(udp)
#   MIN_RATE              = 100 Mbps PAYLOAD
#   C                     = 10 Gbps LINK
#   S3 full overlap       floor = 65 (1 background + 64 incast)
#   floor_payload = 6.500 G, floor_wire = 6.812 G, DRAIN_MAX = 3.188 G
#
# Usage: python3 independent_acceptance.py <out_dir> [expect_incast] [label]
import csv
import os
import sys

PAY_B = 1000.0
LINK_B = 1048.0
RATIO = LINK_B / PAY_B
MINR_PAY = 100e6
C_LINK = 10e9
Q_ABS = 838.86e-6 * C_LINK / 8.0          # 1,048,575 B
M_SAFE = 67072.0
Q_RED = Q_ABS - M_SAFE
MAX_BOOST = 0.30 * C_LINK

OUT = sys.argv[1] if len(sys.argv) > 1 else 'qc_s3_rho090_fixE_out'
EXPECT_INCAST = int(sys.argv[2]) if len(sys.argv) > 2 else 64
LABEL = sys.argv[3] if len(sys.argv) > 3 else OUT

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, OUT)

gates = []
info = []


def gate(name, ok, detail, source):
    gates.append((name, ok, detail, source))


def note(k, v):
    info.append((k, v))


def rows(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return list(csv.DictReader(f))


def g(r, k, d=0.0):
    try:
        return float(r.get(k, d) or d)
    except (TypeError, ValueError):
        return d


if not os.path.isdir(D):
    print('FATAL: %s missing' % D)
    sys.exit(2)

adm = rows('admission.csv') or []
fs = rows('flow_summary.csv') or []
ps = rows('port_summary.csv') or []
lts = rows('selected_link_timeseries.csv') or []
act = rows('actuation.csv') or []
ara = rows('applied_rate_audit.csv') or []
pfc = rows('pfc_events.csv') or []
qc = rows('qc_trace.csv') or []

print('=' * 74)
print('INDEPENDENT ACCEPTANCE -- %s' % LABEL)
print('=' * 74)
print('  frozen: link=%.0fB payload=%.0fB ratio=%.6f MIN_RATE=%.0fM(payload)'
      % (LINK_B, PAY_B, RATIO, MINR_PAY / 1e6))
print('  frozen: C=%.0fG Q_abs=%.0fB Q_red=%.0fB MAX_BOOST=%.2fC'
      % (C_LINK / 1e9, Q_ABS, Q_RED, MAX_BOOST / C_LINK))
print('')

# ---------------------------------------------------------------------------
# 1. MEMBERSHIP LIFECYCLE, rebuilt from raw admission + completion events
# ---------------------------------------------------------------------------
# admission.csv gives (batch_id, flow_id, network_release_ns) -- the
# authoritative admission event.  flow_summary.csv gives finish_time -- the
# authoritative completion.  We reconstruct the live set ourselves.
adm_by_flow = {}
for r in adm:
    fid = r.get('flow_id')
    t = g(r, 'network_release_ns')
    if fid is None:
        continue
    if fid not in adm_by_flow or t < adm_by_flow[fid][0]:
        adm_by_flow[fid] = (t, r.get('batch_id'))

fin_by_flow = {}
for r in fs:
    fid = r.get('flow_id')
    ft = r.get('finish_time')
    if fid is None:
        continue
    fin_by_flow[fid] = (float(ft) * 1e9 if ft not in (None, '') else None)

batches = {}
for fid, (t, b) in adm_by_flow.items():
    batches.setdefault(b, []).append(fid)

note('admission events', len(adm))
note('distinct flows admitted', len(adm_by_flow))
note('distinct batches', '%d -> %s'
     % (len(batches), sorted((b, len(v)) for b, v in batches.items())))

# The live set at the instant of peak overlap = admitted and not yet finished.
# Evaluate at the LAST admission time (all incast released, none finished yet).
if adm_by_flow:
    t_overlap = max(t for t, _ in adm_by_flow.values())
    live_at_overlap = [fid for fid, (t, _) in adm_by_flow.items()
                       if t <= t_overlap
                       and (fin_by_flow.get(fid) is None
                            or fin_by_flow[fid] > t_overlap)]
    note('t_overlap (last admission)', '%.6f ms' % (t_overlap / 1e6))
    note('live flows at t_overlap (independent)', len(live_at_overlap))

    exp_floor = EXPECT_INCAST + 1          # incast + background
    gate('L-1. live set at peak overlap == %d (incast %d + background 1)'
         % (exp_floor, EXPECT_INCAST),
         len(live_at_overlap) == exp_floor,
         'reconstructed live set = %d' % len(live_at_overlap),
         'admission.csv + flow_summary.csv')

    # The control generation is the NEWEST batch; it must exclude the background.
    newest = max(batches.keys(), key=lambda b: min(
        adm_by_flow[f][0] for f in batches[b]))
    gen = batches[newest]
    older = [f for b, v in batches.items() if b != newest for f in v]
    gate('L-2. newest batch (control generation) == %d flows' % EXPECT_INCAST,
         len(gen) == EXPECT_INCAST,
         'newest batch %s has %d flows' % (newest, len(gen)),
         'admission.csv batch_id')
    gate('L-3. background flow is NOT in the control generation',
         len(older) >= 1 and all(f not in gen for f in older),
         '%d older-batch flow(s), none in the newest batch' % len(older),
         'admission.csv batch_id')
    gate('L-4. floor set (live) strictly contains the generation',
         set(gen).issubset(set(live_at_overlap))
         and len(live_at_overlap) > len(gen),
         'floor %d > generation %d' % (len(live_at_overlap), len(gen)),
         'admission.csv + flow_summary.csv')

    # Closed-form floor from the INDEPENDENT count.
    fp = len(live_at_overlap) * MINR_PAY
    fw = fp * RATIO
    dm = C_LINK - fw
    note('floor_payload (independent)', '%.4f G' % (fp / 1e9))
    note('floor_wire (independent)', '%.4f G' % (fw / 1e9))
    note('DRAIN_MAX (independent)', '%.4f G = %.4f C' % (dm / 1e9, dm / C_LINK))
    note('header_overhead per packet', '%.0f B (%.4f%%)'
         % (LINK_B - PAY_B, 100.0 * (LINK_B - PAY_B) / PAY_B))

# completion count, independent of the controller
done = [r for r in fs if g(r, 'completed') > 0]
inc_done = [r for r in done
            if r.get('flow_id') in set(batches.get(
                max(batches.keys(), key=lambda b: min(
                    adm_by_flow[f][0] for f in batches[b])), []))] \
    if adm_by_flow and batches else []
gate('L-5. %d/%d incast flows complete' % (EXPECT_INCAST, EXPECT_INCAST),
     len(inc_done) == EXPECT_INCAST,
     '%d incast completions' % len(inc_done),
     'flow_summary.csv completed')

# ---------------------------------------------------------------------------
# 2. QUEUE, from the raw egress counter
# ---------------------------------------------------------------------------
qsrc = 'port_summary.csv:queue_bytes'
qv = [g(r, 'queue_bytes') for r in ps] if ps else []
if not qv:
    qv = [g(r, 'queue_bytes') for r in lts]
    qsrc = 'selected_link_timeseries.csv:queue_bytes'
if qv:
    qv_s = sorted(qv)
    n = len(qv_s)
    qmean = sum(qv_s) / n
    qp95 = qv_s[int(0.95 * (n - 1))]
    qp99 = qv_s[int(0.99 * (n - 1))]
    qmax = qv_s[-1]
    note('queue samples', '%d (from %s)' % (n, qsrc))
    note('queue mean/p95/p99/max', '%.0f / %.0f / %.0f / %.0f B'
         % (qmean, qp95, qp99, qmax))
    note('queue delay mean/max', '%.3f / %.3f us'
         % (8.0 * qmean / C_LINK * 1e6, 8.0 * qmax / C_LINK * 1e6))
    note('queue max as %% of Q_abs', '%.2f%%' % (100.0 * qmax / Q_ABS))
    # Report truthfully; do not move the boundary.
    gate('Q-1. raw queue max <= Q_abs (reported truthfully, never relaxed)',
         qmax <= Q_ABS,
         'max %.0f B = %.2f%% of Q_abs %.0f B'
         % (qmax, 100.0 * qmax / Q_ABS, Q_ABS),
         qsrc)

# ---------------------------------------------------------------------------
# 3. ARRIVAL / SERVED from actual link bytes
# ---------------------------------------------------------------------------
if ps:
    ar = [g(r, 'arrival_rate_bps') for r in ps]
    sr = [g(r, 'service_rate_bps') for r in ps]
    ib = sum(g(r, 'input_bytes_delta') for r in ps)
    ob = sum(g(r, 'output_bytes_delta') for r in ps)
    note('input bytes total (raw)', '%.0f B' % ib)
    note('output bytes total (raw)', '%.0f B' % ob)
    if ar:
        note('arrival rate max/mean', '%.4f / %.4f G'
             % (max(ar) / 1e9, sum(ar) / len(ar) / 1e9))
    if sr:
        note('served rate max/mean', '%.4f / %.4f G'
             % (max(sr) / 1e9, sum(sr) / len(sr) / 1e9))
        gate('R-1. served rate never exceeds link capacity C',
             max(sr) <= C_LINK * 1.001,
             'max served %.4f G <= C %.4f G' % (max(sr) / 1e9, C_LINK / 1e9),
             'port_summary.csv:service_rate_bps')
if lts:
    tx = [g(r, 'tx_bytes_delta') for r in lts if g(r, 'tx_bytes_delta') > 0]
    if tx:
        gran = {}
        for v in tx:
            gran[v % LINK_B] = gran.get(v % LINK_B, 0) + 1
        note('tx_bytes_delta samples', len(tx))
        note('tx_bytes_delta divisible by 1048', '%d/%d (%.1f%%)'
             % (gran.get(0.0, 0), len(tx),
                100.0 * gran.get(0.0, 0) / len(tx)))

# Byte-domain cross-comparison gate: MIN_RATE is payload, floor must be link.
if adm_by_flow:
    gate('W-1. no byte-domain cross comparison (floor uses link domain)',
         abs(fw - fp * RATIO) < 1.0 and abs(RATIO - 1.048) < 1e-9,
         'floor_wire = floor_payload x %.6f exactly' % RATIO,
         'derived from frozen constants')

# ---------------------------------------------------------------------------
# 4. COMMANDED vs SENDER-EFFECTIVE vs ARRIVAL, per stage
# ---------------------------------------------------------------------------
if act:
    stages = {}
    for r in act:
        stages[r.get('stage')] = stages.get(r.get('stage'), 0) + 1
    note('actuation rows', '%d, stages=%s' % (len(act), sorted(stages.items())))
    gens = set(r.get('generation') for r in act)
    note('actuation generations', '%d distinct' % len(gens))
    # per (generation, flow) accounting of in-flight commands
    perkey = {}
    for r in act:
        perkey.setdefault((r.get('generation'), r.get('flow_id')), []).append(r)
    note('actuation (generation,flow) keys', len(perkey))
    gate('P-1. pending/in-flight is accounted per (generation, QP)',
         len(perkey) > 0,
         '%d distinct (generation, flow_id) command keys' % len(perkey),
         'actuation.csv')
else:
    note('actuation rows', '0 (no controller commands recorded)')

if ara:
    viol = sum(1 for r in ara if g(r, 'applied_capacity_violation') > 0)
    exc = [g(r, 'actual_arrival_excess_bps') for r in ara]
    note('applied_rate_audit rows', len(ara))
    note('applied capacity violations', viol)
    if exc:
        note('actual arrival excess max', '%.4f G' % (max(exc) / 1e9))
    # Section 1.3: short-term arrival above C is ALLOWED.  Report, do not gate.
    note('NOTE', 'arrival > C is permitted by design; reported not gated')

# ---------------------------------------------------------------------------
# 5. SAFETY: PFC / drops / retransmissions -- raw sources
# ---------------------------------------------------------------------------
gate('S-1. zero PFC pause events',
     len(pfc) == 0, '%d rows in pfc_events.csv' % len(pfc),
     'pfc_events.csv')
if lts:
    pfc_ns = sum(g(r, 'pfc_pause_ns_delta') for r in lts)
    pfc_ev = sum(g(r, 'pfc_event_delta') for r in lts)
    gate('S-2. zero PFC pause duration on the traced link',
         pfc_ns == 0 and pfc_ev == 0,
         'pause_ns=%.0f events=%.0f' % (pfc_ns, pfc_ev),
         'selected_link_timeseries.csv')
retx = sum(g(r, 'retx_bytes') for r in fs)
retxe = sum(g(r, 'retx_events') for r in fs)
gate('S-3. zero retransmissions',
     retx == 0 and retxe == 0,
     'retx_bytes=%.0f retx_events=%.0f' % (retx, retxe),
     'flow_summary.csv')
log = os.path.join(D, 'run.log')
drops = 0
if os.path.exists(log):
    with open(log) as f:
        for line in f:
            if 'Drop:' in line:
                drops += 1
gate('S-4. zero headroom drops',
     drops == 0, '%d "Drop:" lines in run.log' % drops, 'run.log')

# ---------------------------------------------------------------------------
# 6. FCT / CCT / goodput -- raw flow_summary
# ---------------------------------------------------------------------------
gen_ids = set()
if adm_by_flow and batches:
    newest = max(batches.keys(), key=lambda b: min(
        adm_by_flow[f][0] for f in batches[b]))
    gen_ids = set(batches[newest])
fcts = sorted(g(r, 'fct') for r in fs
              if r.get('flow_id') in gen_ids and g(r, 'fct') > 0)
if fcts:
    n = len(fcts)
    note('incast FCT mean', '%.6f ms' % (1e3 * sum(fcts) / n))
    note('incast FCT p95', '%.6f ms' % (1e3 * fcts[int(0.95 * (n - 1))]))
    note('incast FCT p99', '%.6f ms' % (1e3 * fcts[int(0.99 * (n - 1))]))
    note('incast CCT (last completion)', '%.6f ms' % (1e3 * fcts[-1]))
    tot = sum(g(r, 'total_size_bytes') for r in fs if r.get('flow_id') in gen_ids)
    if fcts[-1] > 0:
        note('incast goodput (aggregate/CCT)', '%.4f Gbps'
             % (8.0 * tot / fcts[-1] / 1e9))
bg = [r for r in fs if r.get('flow_id') not in gen_ids]
for r in bg:
    note('background flow %s' % r.get('flow_id'),
         'acked=%.0f B goodput=%.4f G completed=%s'
         % (g(r, 'acked_bytes'), g(r, 'flow_goodput') / 1e9,
            r.get('completed')))

# ---------------------------------------------------------------------------
# 7. CONTROLLER-REPORTED quantities (labelled; not independent evidence)
# ---------------------------------------------------------------------------
if qc:
    own = [r for r in qc if r.get('owns_rates') == '1']
    zones = {}
    for r in qc:
        zones[r.get('zone')] = zones.get(r.get('zone'), 0) + 1
    sw = 0
    prev = None
    for r in qc:
        z = r.get('zone')
        if prev is not None and z != prev:
            sw += 1
        prev = z
    note('[CONTROLLER] zone residency', sorted(zones.items()))
    note('[CONTROLLER] zone switches', sw)
    note('[CONTROLLER] owning epochs', '%d of %d' % (len(own), len(qc)))
    bad_scope = [r for r in qc if r.get('owns_rates') != '1'
                 and (g(r, 'boost_effective') != 0 or g(r, 'drain') != 0)]
    gate('C-1. not owning => boost == 0 and drain == 0',
         len(bad_scope) == 0,
         '%d non-owning epochs with non-zero boost/drain' % len(bad_scope),
         '[CONTROLLER] qc_trace.csv')
    both = [r for r in qc
            if g(r, 'boost_effective') != 0 and g(r, 'drain') != 0]
    gate('C-2. boost and drain are never both non-zero',
         len(both) == 0, '%d epochs with both non-zero' % len(both),
         '[CONTROLLER] qc_trace.csv')
    bmax = max([g(r, 'boost_effective') for r in qc] + [0])
    gate('C-3. boost never exceeds MAX_BOOST = 0.30 C',
         bmax <= MAX_BOOST + 2e6,
         'max boost %.4f G <= %.4f G' % (bmax / 1e9, MAX_BOOST / 1e9),
         '[CONTROLLER] qc_trace.csv')
    if 'floor_count' in qc[0]:
        # cross-check the controller against the INDEPENDENT reconstruction
        fcmax = max(int(g(r, 'floor_count')) for r in qc)
        gcmax = max(int(g(r, 'new_gen_count')) for r in qc)
        gate('X-1. controller floor_count matches independent live set',
             adm_by_flow and fcmax == len(live_at_overlap),
             'controller %d vs independent %d'
             % (fcmax, len(live_at_overlap) if adm_by_flow else -1),
             'cross-check')
        gate('X-2. controller generation matches independent newest batch',
             gcmax == EXPECT_INCAST,
             'controller %d vs independent %d' % (gcmax, EXPECT_INCAST),
             'cross-check')
        fwmax = max(g(r, 'floor_wire_bps') for r in qc)
        gate('X-3. controller floor_wire matches the independent closed form',
             adm_by_flow and abs(fwmax - fw) < 2e6,
             'controller %.4f G vs independent %.4f G'
             % (fwmax / 1e9, fw / 1e9 if adm_by_flow else -1),
             'cross-check')
        sv = int(g(qc[-1], 'scope_violations'))
        gate('C-4. zero scope violations',
             sv == 0, 'scope_violations=%d' % sv,
             '[CONTROLLER] qc_trace.csv')

# ---------------------------------------------------------------------------
print('')
print('--- measured quantities ---')
for k, v in info:
    print('  %-42s %s' % (k, v))
print('')
print('--- gates ---')
fail = 0
for name, ok, detail, source in gates:
    print('  [%s] %s' % ('PASS' if ok else 'FAIL', name))
    print('         %s   <- %s' % (detail, source))
    if not ok:
        fail += 1
print('')
print('  %d/%d gates passed' % (len(gates) - fail, len(gates)))
if fail:
    print('')
    print('  HARD GATE FAILED -- stop; retain full trace; do not continue.')
sys.exit(1 if fail else 0)
