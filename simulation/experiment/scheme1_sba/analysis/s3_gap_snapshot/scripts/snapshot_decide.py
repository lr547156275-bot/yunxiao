# -*- coding: utf-8 -*-
# Item F: decide between the four named hypotheses from the gap-boundary
# snapshots.  Every test reports its RAW DISTRIBUTION, not just a verdict.
#
#   F1 RATE_ALLOCATION_UNDERFEED
#      QPs have packets pending but applied_rate is low.  Measured as: at gap
#      start, among QPs with bytes_left > 0, the distribution of applied_rate,
#      and the sum of applied rates against link capacity.  If the active set's
#      applied rates sum well below C while work is queued, the controller is
#      handing out too little rate.
#
#   F2 PACER_REARM_OR_NEXTAVAIL_BUG
#      Rate is adequate but m_nextAvail jumps illegally forward, or never
#      updates.  Measured as: (a) next_avail - now at gap start for QPs with
#      work; (b) whether next_avail - last_tx exceeds the packet interval implied
#      by applied_rate (an illegal forward jump); (c) QPs whose next_avail is
#      identical across many consecutive snapshots while work is pending.
#
#   F3 ACTIVE_SET_TAIL_COLLAPSE
#      Only 1-2 QPs still have work.  Measured as: distribution of the count of
#      QPs with bytes_left > 0 per gap.
#
#   F4 QP_PHASE_CLUSTERING
#      Most active QPs' next_avail fall into a few time buckets.  Measured
#      directly on the simultaneous snapshot, so no historical inference is
#      involved: bucket the active QPs' next_avail at several resolutions and
#      report occupancy concentration.
#
# READ-ONLY.  Reads the snapshot CSV, writes CSVs and prints distributions.
import csv
import gzip
import hashlib
import os
import statistics as S
import sys

B = '/work/simulation/experiment/scheme1_sba'
OUT = os.path.join(B, 'analysis/s3_gap_snapshot')
SNAP = os.path.join(B, 'gs_s3_on_out', 'gap_snapshot.csv')
C = 10e9
WIRE = 1048


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
        return ''
    s = sorted(v)
    return s[min(len(s) - 1, int(q * (len(s) - 1)))]


def hist(v, edges):
    out = []
    for i in range(len(edges)):
        lo = edges[i]
        hi = edges[i + 1] if i + 1 < len(edges) else None
        n = sum(1 for x in v if x >= lo and (hi is None or x < hi))
        out.append((lo, hi, n))
    return out


if not os.path.exists(SNAP):
    print('SNAPSHOT ABSENT: %s' % SNAP)
    sys.exit(1)

rows = []
with open(SNAP) as fh:
    for r in csv.DictReader(fh):
        try:
            rows.append(dict(
                gap=int(r['gap_id']), t=int(r['time_ns']),
                bnd=int(r['boundary']), node=int(r['node_id']),
                qpi=int(r['qp_index']), flowref=int(r['flow_id_ref']),
                active=int(r['active']), fin=int(r['finished']),
                owns=int(r['owns_rate']), floor=int(r['in_floor']),
                left=int(r['bytes_left']), pend=int(r['packet_pending']),
                cmd=int(r['commanded_rate_bps']),
                app=int(r['applied_rate_bps']),
                na=int(r['next_avail_ns']), ltx=int(r['last_tx_time_ns']),
                lcmd=int(r['last_command_time_ns']),
                gen=int(r['generation'])))
        except (KeyError, ValueError):
            continue

print('=== snapshot inventory ===')
print('  rows                 : %d' % len(rows))
gaps = sorted(set(r['gap'] for r in rows))
print('  gaps                 : %d' % len(gaps))
print('  distinct node_id     : %d' % len(set(r['node'] for r in rows)))
print('  distinct qp_index    : %d' % len(set(r['qpi'] for r in rows)))
print('  distinct (node,qpi)  : %d'
      % len(set((r['node'], r['qpi']) for r in rows)))
starts = [r for r in rows if r['bnd'] == 0]
ends = [r for r in rows if r['bnd'] == 1]
print('  gap-start rows       : %d' % len(starts))
print('  gap-end rows         : %d' % len(ends))
bg = {}
for r in rows:
    bg.setdefault((r['gap'], r['bnd']), 0)
    bg[(r['gap'], r['bnd'])] += 1
if bg:
    v = sorted(bg.values())
    print('  QPs per snapshot     : min=%d p50=%d max=%d'
          % (v[0], pct(v, .5), v[-1]))
# Identity integrity: flow_id_ref must NOT be used as a key; confirm it would
# have been wrong here too.
nf = {}
for r in rows:
    nf.setdefault(r['node'], set()).add(r['flowref'])
multi = [n for n, s in nf.items() if len(s) > 1]
print('  nodes whose flow_id_ref is non-constant : %d  (identity uses '
      '(node_id,qp_index) instead)' % len(multi))

bystart = {}
for r in starts:
    bystart.setdefault(r['gap'], []).append(r)

# ------------------------------------------------------------------- F3 -----
print('')
print('=== F3 ACTIVE_SET_TAIL_COLLAPSE: how many QPs still have work? ===')
npend, nact, nowns = [], [], []
for g, v in sorted(bystart.items()):
    npend.append(sum(1 for r in v if r['left'] > 0))
    nact.append(sum(1 for r in v if r['active'] == 1))
    nowns.append(sum(1 for r in v if r['owns'] == 1))
if npend:
    print('  QPs with bytes_left>0 per gap : min=%d p05=%s p50=%s p95=%s max=%d'
          % (min(npend), pct(npend, .05), pct(npend, .5), pct(npend, .95),
             max(npend)))
    print('    distribution: %s'
          % [(lo, hi, n) for lo, hi, n in
             hist(npend, [0, 1, 2, 3, 5, 9, 17, 33, 65])])
    le2 = sum(1 for x in npend if x <= 2)
    print('    gaps with <=2 pending QPs : %d of %d (%.2f%%)'
          % (le2, len(npend), 100.0 * le2 / len(npend)))
    print('  QPs with active=1 per gap     : p50=%s max=%d'
          % (pct(nact, .5), max(nact)))
    print('  QPs with owns_rate=1 per gap  : p50=%s max=%d'
          % (pct(nowns, .5), max(nowns)))

# ------------------------------------------------------------------- F1 -----
print('')
print('=== F1 RATE_ALLOCATION_UNDERFEED: applied rate of QPs with work ===')
app_all, sum_app, sum_cmd = [], [], []
for g, v in sorted(bystart.items()):
    w = [r for r in v if r['left'] > 0]
    if not w:
        continue
    app_all.extend(r['app'] for r in w)
    sum_app.append(sum(r['app'] for r in w))
    sum_cmd.append(sum(r['cmd'] for r in w))
if app_all:
    print('  per-QP applied_rate (Gbps): p05=%.4f p50=%.4f p95=%.4f max=%.4f'
          % (pct(app_all, .05) / 1e9, pct(app_all, .5) / 1e9,
             pct(app_all, .95) / 1e9, max(app_all) / 1e9))
    print('  sum(applied) over QPs with work, per gap (Gbps):')
    print('    p05=%.4f p50=%.4f p95=%.4f max=%.4f'
          % (pct(sum_app, .05) / 1e9, pct(sum_app, .5) / 1e9,
             pct(sum_app, .95) / 1e9, max(sum_app) / 1e9))
    print('  sum(commanded) per gap (Gbps): p50=%.4f max=%.4f'
          % (pct(sum_cmd, .5) / 1e9, max(sum_cmd) / 1e9))
    below = sum(1 for x in sum_app if x < 0.9 * C)
    print('    gaps where sum(applied) < 0.9*C : %d of %d (%.2f%%)'
          % (below, len(sum_app), 100.0 * below / len(sum_app)))
    print('    (C = %.1f Gbps)' % (C / 1e9))

# ------------------------------------------------------------------- F2 -----
print('')
print('=== F2 PACER_REARM_OR_NEXTAVAIL_BUG ===')
lead, jump, stale = [], [], []
for g, v in sorted(bystart.items()):
    now = v[0]['t']
    for r in v:
        if r['left'] <= 0:
            continue
        lead.append(r['na'] - now)
        # legal interval implied by the applied rate for one wire packet
        if r['app'] > 0 and r['ltx'] > 0:
            legal = int(WIRE * 8 * 1e9 / r['app'])
            excess = (r['na'] - r['ltx']) - legal
            jump.append(excess)
if lead:
    print('  next_avail - now, QPs with work (ns):')
    print('    min=%d p05=%s p50=%s p95=%s max=%d'
          % (min(lead), pct(lead, .05), pct(lead, .5), pct(lead, .95),
             max(lead)))
    neg = sum(1 for x in lead if x <= 0)
    print('    <=0 (already eligible, so NOT pacing-blocked) : %d of %d '
          '(%.2f%%)' % (neg, len(lead), 100.0 * neg / len(lead)))
    print('    distribution: %s'
          % [(lo, hi, n) for lo, hi, n in
             hist(lead, [-10 ** 9, 0, 500, 1000, 2000, 3000, 5000, 10000,
                         50000])])
if jump:
    print('  (next_avail - last_tx) - legal_interval(applied_rate) (ns):')
    print('    min=%d p05=%s p50=%s p95=%s max=%d'
          % (min(jump), pct(jump, .05), pct(jump, .5), pct(jump, .95),
             max(jump)))
    ill = sum(1 for x in jump if x > 1000)
    print('    > 1000 ns beyond the legal interval (illegal forward jump) : '
          '%d of %d (%.2f%%)' % (ill, len(jump), 100.0 * ill / len(jump)))

# stale next_avail: same value across consecutive gap-start snapshots while work
# is pending
seq = {}
for g in sorted(bystart):
    for r in bystart[g]:
        k = (r['node'], r['qpi'])
        seq.setdefault(k, []).append((g, r['na'], r['left']))
stalemax = []
for k, v in seq.items():
    run = 1
    best = 1
    for i in range(1, len(v)):
        if v[i][1] == v[i - 1][1] and v[i][2] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 1
    stalemax.append(best)
if stalemax:
    print('  longest run of UNCHANGED next_avail while work pending, per QP:')
    print('    p50=%s p95=%s max=%d' % (pct(stalemax, .5), pct(stalemax, .95),
                                        max(stalemax)))

# ------------------------------------------------------------------- F4 -----
print('')
print('=== F4 QP_PHASE_CLUSTERING: simultaneous next_avail buckets ===')
print('  (measured on one instant per gap, so no historical inference)')
for bucket in (100, 500, 838, 2162, 3000):
    occ, top = [], []
    for g, v in sorted(bystart.items()):
        w = [r for r in v if r['left'] > 0 and r['na'] > v[0]['t']]
        if len(w) < 2:
            continue
        base = min(r['na'] for r in w)
        b = {}
        for r in w:
            b[(r['na'] - base) // bucket] = b.get((r['na'] - base) // bucket,
                                                  0) + 1
        occ.append(len(b))
        top.append(max(b.values()) / float(len(w)))
    if occ:
        print('  bucket=%-5d ns : gaps=%-5d occupied_buckets p50=%-4s '
              'max_bucket_share p50=%.3f p95=%.3f'
              % (bucket, len(occ), pct(occ, .5), pct(top, .5), pct(top, .95)))

# ---- write ---------------------------------------------------------------
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
PERGAP = []
for g, v in sorted(bystart.items()):
    w = [r for r in v if r['left'] > 0]
    now = v[0]['t']
    PERGAP.append(dict(
        gap_id=g, time_ns=now, qps_in_snapshot=len(v),
        qps_with_work=len(w),
        qps_active=sum(1 for r in v if r['active'] == 1),
        qps_owns_rate=sum(1 for r in v if r['owns'] == 1),
        sum_applied_bps=sum(r['app'] for r in w),
        sum_commanded_bps=sum(r['cmd'] for r in w),
        min_next_avail_minus_now=(min(r['na'] for r in w) - now) if w else '',
        n_already_eligible=sum(1 for r in w if r['na'] <= now),
        median_applied_bps=(int(S.median([r['app'] for r in w])) if w else '')))


def wcsv(name, rws, gz=False):
    p = os.path.join(OUT, name)
    if not rws:
        open(p, 'w').write('')
        return
    op = gzip.open(p, 'wt', newline='') if gz else open(p, 'w', newline='')
    with op as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rws[0].keys()))
        wr.writeheader()
        for r in rws:
            wr.writerow(r)


wcsv('S3_SNAPSHOT_PER_GAP.csv.gz', PERGAP, gz=True)
with open(os.path.join(OUT, 'SHA256SUMS_SNAPSHOT.txt'), 'w') as fh:
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.isfile(p) and f != 'SHA256SUMS_SNAPSHOT.txt':
            fh.write('%s  %s\n' % (sha(p), f))
print('')
print('=== written to %s ===' % OUT)
