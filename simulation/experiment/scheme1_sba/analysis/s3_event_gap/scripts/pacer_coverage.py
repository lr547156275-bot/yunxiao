# -*- coding: utf-8 -*-
# Quantify the pacer-telemetry blind spot BEFORE classifying, so the gap
# classification states its own coverage instead of implying full coverage.
#
# Established by the span check:
#   rate_command fires 609 times, last at 2,059,450,000 ns (whole window)
#   causal_pacer.csv covers      [2,000,000,000 .. 2,000,185,000]  = 185 us
# Cause (source, not inference): CausalPacerTrace::Emit sits inside ChangeRate's
# CBAP branch, and ChangeRate is only reached when `currentRate != appliedRate`
# (rdma-hw.cc:3099).  Redundant / dominated commands re-issue the same rate, so
# ChangeRate is never entered and no pacer row is written -- even though a
# rate_command was logged.
#
# Consequence: class C (RATE_ACTUATION) is only decidable inside the covered
# 185 us.  Outside it, a gap that WAS caused by a pacer decision is
# indistinguishable from one that was not.  This script measures how many gaps
# and how much gap time fall outside pacer coverage, so the residual is reported
# rather than absorbed into another class.
import csv
import os

B = '/work/simulation/experiment/scheme1_sba'
CB = os.path.join(B, 'ct_cbap_on_out')
T0N, T1N = 2000000000, 2058372997


def load_tx(d):
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
    g, ce = [], pr[0][1]
    for (s, e, nb) in pr[1:]:
        if s > ce:
            g.append((ce, s, s - ce))
        ce = max(ce, e)
    return g


pp = os.path.join(CB, 'causal_pacer.csv')
pts = sorted(int(r['time_ns']) for r in csv.DictReader(open(pp)))
p_lo, p_hi = pts[0], pts[-1]

# independent witness of true actuation activity
rc = []
ap = os.path.join(CB, 'actuation.csv')
with open(ap) as fh:
    for r in csv.DictReader(fh):
        if r.get('stage') == 'rate_command':
            try:
                rc.append(int(r['time_ns']))
            except ValueError:
                pass
rc = sorted(t for t in rc if T0N <= t <= T1N)

pr = load_tx(CB)
gp = gaps_of(pr)

inside = [g for g in gp if g[0] >= p_lo and g[1] <= p_hi]
outside = [g for g in gp if not (g[0] >= p_lo and g[1] <= p_hi)]
tot = sum(g[2] for g in gp)

print('=== PACER TELEMETRY COVERAGE (CBAP, W2) ===')
print('  window                     : [%d, %d]  %.6f ms'
      % (T0N, T1N, (T1N - T0N) / 1e6))
print('  pacer trace covers         : [%d, %d]  %.3f us  (%.4f%% of window)'
      % (p_lo, p_hi, (p_hi - p_lo) / 1e3,
         100.0 * (p_hi - p_lo) / (T1N - T0N)))
print('  pacer rows                 : %d at %d distinct instants'
      % (len(pts), len(set(pts))))
print('  rate_command in window     : %d, last at %d'
      % (len(rc), rc[-1] if rc else -1))
print('  rate_command INSIDE cover  : %d'
      % len([t for t in rc if p_lo <= t <= p_hi]))
print('  rate_command OUTSIDE cover : %d   <-- no pacer row exists for these'
      % len([t for t in rc if not (p_lo <= t <= p_hi)]))
print('=== gaps vs coverage ===')
print('  total gaps                 : %d   total %d ns (%.6f ms)'
      % (len(gp), tot, tot / 1e6))
print('  gaps inside pacer coverage : %d   %d ns (%.2f%% of gap time)'
      % (len(inside), sum(g[2] for g in inside),
         100.0 * sum(g[2] for g in inside) / tot if tot else 0))
print('  gaps outside coverage      : %d   %d ns (%.2f%% of gap time)'
      % (len(outside), sum(g[2] for g in outside),
         100.0 * sum(g[2] for g in outside) / tot if tot else 0))
print('')
print('  => class C (RATE_ACTUATION) is DECIDABLE for %.2f%% of gap time and'
      % (100.0 * sum(g[2] for g in inside) / tot if tot else 0))
print('     UNDECIDABLE for %.2f%%.  The undecidable part must not be labelled'
      % (100.0 * sum(g[2] for g in outside) / tot if tot else 0))
print('     "not caused by actuation"; absence of a row is absence of telemetry.')
