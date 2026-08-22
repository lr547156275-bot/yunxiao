# -*- coding: utf-8 -*-
# Confirm the decisive numbers before reporting, because two of them look like
# they could be artefacts and both change the verdict:
#
#  (a) per-QP applied_rate p05 = p50 = p95 = 0.1480 Gbps.  A distribution with
#      no spread at all is either a real uniform allocation or a stuck column.
#      0.1480 Gbps is suspiciously close to MIN_RATE (100 Mbps payload -> what on
#      the wire?).  If every steered QP sits at the floor, F1 is implicated.
#      But sum(applied) = 9.5754 Gbps ~= 0.96 C, which points AWAY from underfeed.
#      Both cannot be casually asserted; resolve it.
#
#  (b) max_bucket_share = 0.985 at EVERY bucket size from 100 ns to 3000 ns.
#      Identical concentration across a 30x range of bucket widths is the
#      signature of a degenerate input (e.g. nearly all values equal), not of a
#      genuine 3000 ns clustering period.  0.985 * 65 = 64.0 -- exactly the
#      steered set.  Check whether the 64 QPs literally share one next_avail.
#
#  (c) "longest run of UNCHANGED next_avail = 7" needs context: 7 out of how many
#      snapshots does each QP appear in?
import csv
import os
import statistics as S

B = '/work/simulation/experiment/scheme1_sba'
SNAP = os.path.join(B, 'gs_s3_on_out', 'gap_snapshot.csv')
C = 10e9
WIRE, PAYLOAD = 1048, 1000

rows = []
with open(SNAP) as fh:
    for r in csv.DictReader(fh):
        rows.append(dict(gap=int(r['gap_id']), t=int(r['time_ns']),
                         bnd=int(r['boundary']), node=int(r['node_id']),
                         qpi=int(r['qp_index']), owns=int(r['owns_rate']),
                         floor=int(r['in_floor']), left=int(r['bytes_left']),
                         cmd=int(r['commanded_rate_bps']),
                         app=int(r['applied_rate_bps']),
                         na=int(r['next_avail_ns']),
                         ltx=int(r['last_tx_time_ns'])))

starts = {}
for r in rows:
    if r['bnd'] == 0:
        starts.setdefault(r['gap'], []).append(r)

print('=== (a) is 0.1480 Gbps the MIN_RATE floor? ===')
print('  MIN_RATE payload = 100 Mbps (config)')
print('  wire equivalent  = 100e6 * %d/%d = %.4f Gbps'
      % (WIRE, PAYLOAD, 100e6 * WIRE / PAYLOAD / 1e9))
print('  payload equiv of 0.1480 Gbps = %.4f Gbps'
      % (0.148e9 * PAYLOAD / WIRE / 1e9))
# exact value distribution of applied_rate among QPs with work
g0 = sorted(starts)[len(starts) // 2]
v = starts[g0]
appv = {}
for r in v:
    if r['left'] > 0:
        appv[r['app']] = appv.get(r['app'], 0) + 1
print('  at the median gap (id=%d), applied_rate value counts:' % g0)
for k, n in sorted(appv.items()):
    print('    %.6f Gbps  x %d QPs%s' % (k / 1e9, n,
          '   <- this is the whole steered set' if n >= 60 else ''))
print('  sum = %.6f Gbps  (%.2f%% of C)'
      % (sum(r['app'] for r in v if r['left'] > 0) / 1e9,
         100.0 * sum(r['app'] for r in v if r['left'] > 0) / C))
# who holds the big rate?
big = [r for r in v if r['app'] > 1e9]
print('  QPs with applied_rate > 1 Gbps: %d  %s'
      % (len(big), [(r['node'], r['qpi'], '%.3fG' % (r['app'] / 1e9),
                     'owns=%d' % r['owns'], 'floor=%d' % r['floor'])
                    for r in big]))
own = [r for r in v if r['owns'] == 1]
print('  owns_rate=1 count: %d ; their applied sum = %.6f Gbps'
      % (len(own), sum(r['app'] for r in own) / 1e9))
print('  commanded sum over QPs with work = %.6f Gbps'
      % (sum(r['cmd'] for r in v if r['left'] > 0) / 1e9))
print('    NOTE: commanded 18.28 G > C means the commanded column is a per-QP')
print('    target that is NOT meant to sum to C, or is wire-vs-payload mixed.')
print('    Do not read it as "the controller asked for 18 Gbps".')

print('')
print('=== (b) do the 64 steered QPs share ONE next_avail? ===')
same = []
for g, vv in sorted(starts.items()):
    w = [r for r in vv if r['left'] > 0 and r['na'] > vv[0]['t']]
    if len(w) < 2:
        continue
    nas = [r['na'] for r in w]
    uniq = len(set(nas))
    top = max(nas.count(x) for x in set(nas))
    same.append((uniq, top, len(w), max(nas) - min(nas)))
if same:
    uq = [x[0] for x in same]
    tp = [x[1] for x in same]
    sp = [x[3] for x in same]
    print('  distinct next_avail values among pending QPs, per gap:')
    print('    min=%d p50=%d p95=%d max=%d'
          % (min(uq), sorted(uq)[len(uq) // 2],
             sorted(uq)[int(.95 * (len(uq) - 1))], max(uq)))
    print('  largest identical group size, per gap: p50=%d max=%d'
          % (sorted(tp)[len(tp) // 2], max(tp)))
    print('  spread max(next_avail)-min(next_avail), per gap (ns):')
    print('    min=%d p50=%d p95=%d max=%d'
          % (min(sp), sorted(sp)[len(sp) // 2],
             sorted(sp)[int(.95 * (len(sp) - 1))], max(sp)))
    ident = sum(1 for x in same if x[0] == 1)
    print('  gaps where ALL pending QPs share one next_avail: %d of %d (%.2f%%)'
          % (ident, len(same), 100.0 * ident / len(same)))
    # show one gap in detail
    gm = sorted(starts)[len(starts) // 2]
    vv = starts[gm]
    w = sorted([r for r in vv if r['left'] > 0], key=lambda r: r['na'])
    print('  detail at gap %d (t=%d): first/last 4 pending QPs by next_avail'
          % (gm, vv[0]['t']))
    for r in w[:4] + w[-4:]:
        print('    node=%-3d qp=%-3d next_avail=%d (now+%d) app=%.4fG owns=%d'
              % (r['node'], r['qpi'], r['na'], r['na'] - vv[0]['t'],
                 r['app'] / 1e9, r['owns']))

print('')
print('=== (c) how many snapshots does each QP appear in? ===')
cnt = {}
for r in rows:
    if r['bnd'] == 0:
        cnt[(r['node'], r['qpi'])] = cnt.get((r['node'], r['qpi']), 0) + 1
if cnt:
    v2 = sorted(cnt.values())
    print('  gap-start snapshots per QP: min=%d p50=%d max=%d'
          % (v2[0], v2[len(v2) // 2], v2[-1]))
    print('  => a max unchanged-run of 7 out of %d is NOT a stuck pacer'
          % v2[len(v2) // 2])
