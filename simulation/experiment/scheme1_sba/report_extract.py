# -*- coding: utf-8 -*-
# Report data extraction: three-set counts over time, floor/DRAIN_MAX during
# overlap, and the old-side / new-side migration trajectory.
#
# Usage: python3 report_extract.py <out_dir> [label]
import csv
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'qc_s3_rho090_fixE_out'
LABEL = sys.argv[2] if len(sys.argv) > 2 else OUT
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, OUT)
PAY, WIRE, C, MINR = 1000.0, 1048.0, 10e9, 100e6


def rows(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def g(r, k, d=0.0):
    try:
        return float(r.get(k, d) or d)
    except (TypeError, ValueError):
        return d


qc = rows('qc_trace.csv')
print('=== %s ===' % LABEL)
print('')

# --- 1. three-set counts over time (transitions only) --------------------
print('--- 1. three-set counts (transitions only) ---')
print('  %-14s %6s %7s %8s %10s %11s %11s'
      % ('t_ms', 'floor', 'newGen', 'oldSide', 'owns', 'floor_wire', 'DRAIN_MAX'))
prev = None
shown = 0
for r in qc:
    key = (int(g(r, 'floor_count')), int(g(r, 'new_gen_count')),
           int(g(r, 'old_side_count')), r.get('owns_rates'))
    if key == prev:
        continue
    prev = key
    shown += 1
    if shown > 22:
        continue
    print('  %-14.6f %6d %7d %8d %10s %11.4f %11.4f'
          % (g(r, 'time_ns') / 1e6, key[0], key[1], key[2], key[3],
             g(r, 'floor_wire_bps') / 1e9, g(r, 'drain_max_wire_bps') / 1e9))
print('  (%d distinct set-state transitions total)' % shown)
print('')

# --- 2. overlap window ---------------------------------------------------
own = [r for r in qc if r.get('owns_rates') == '1']
full = [r for r in own if int(g(r, 'floor_count')) == 65]
print('--- 2. full-overlap window (floor_count == 65) ---')
if full:
    print('  epochs                : %d' % len(full))
    print('  t range               : %.6f .. %.6f ms'
          % (g(full[0], 'time_ns') / 1e6, g(full[-1], 'time_ns') / 1e6))
    print('  floor_payload         : %.4f G (expect 6.5000)'
          % (g(full[0], 'floor_payload_bps') / 1e9))
    print('  floor_wire            : %.4f G (expect 6.8120)'
          % (g(full[0], 'floor_wire_bps') / 1e9))
    fw = set(round(g(r, 'floor_wire_bps'), 0) for r in full)
    dm = set(round(g(r, 'drain_max_wire_bps'), 0) for r in full)
    print('  distinct floor_wire   : %d value(s) -> %s'
          % (len(fw), [round(v / 1e9, 4) for v in sorted(fw)][:4]))
    print('  distinct DRAIN_MAX    : %d value(s) -> %s'
          % (len(dm), [round(v / 1e9, 4) for v in sorted(dm)][:4]))
    print('  new_gen_count         : %d (boost denominator)'
          % int(g(full[0], 'new_gen_count')))
    print('  old_side_count        : %d (background, floored not steered)'
          % int(g(full[0], 'old_side_count')))
print('')

# --- 3. migration trajectory: old side vs new side ----------------------
print('--- 3. migration trajectory (from rate_transition / applied_rate) ---')
rt = rows('rate_transition.csv')
if rt:
    bg = [r for r in rt if r.get('flow_id') == '0']
    inc = [r for r in rt if r.get('flow_id') not in (None, '', '0')]
    print('  rate_transition rows  : %d (bg=%d incast=%d)'
          % (len(rt), len(bg), len(inc)))
    cols = [c for c in (rt[0].keys() if rt else []) if 'rate' in c.lower()]
    print('  rate columns          : %s' % cols[:6])
    for tag, sub in (('background(old side)', bg), ('incast(new side)', inc)):
        if not sub:
            continue
        k = cols[0] if cols else None
        if k:
            vals = [g(r, k) for r in sub if g(r, k) > 0]
            if vals:
                print('    %-22s %s: first=%.4f G last=%.4f G min=%.4f max=%.4f'
                      % (tag, k, vals[0] / 1e9, vals[-1] / 1e9,
                         min(vals) / 1e9, max(vals) / 1e9))
else:
    print('  (rate_transition.csv absent)')
print('')

# --- 4. FCT / BCT summary ------------------------------------------------
print('--- 4. FCT / background ---')
fs = rows('flow_summary.csv')
inc = [r for r in fs if r.get('flow_id') not in (None, '', '0')]
bgr = [r for r in fs if r.get('flow_id') == '0']
fcts = sorted(g(r, 'fct') for r in inc if g(r, 'fct') > 0)
if fcts:
    n = len(fcts)
    print('  incast flows completed: %d' % n)
    print('  FCT mean              : %.6f ms' % (1e3 * sum(fcts) / n))
    print('  FCT p99               : %.6f ms' % (1e3 * fcts[int(0.99 * (n - 1))]))
    print('  FCT max               : %.6f ms' % (1e3 * fcts[-1]))
if bgr:
    b = bgr[0]
    print('  background acked      : %.0f B (completed=%s)'
          % (g(b, 'acked_bytes'), b.get('completed')))
    print('  background goodput    : %.4f Gbps' % (g(b, 'flow_goodput') / 1e9))
print('')

# --- 5. safety -----------------------------------------------------------
print('--- 5. safety ---')
q0 = [g(r, 'q0') for r in qc]
print('  queue peak            : %.0f B (%.2f%% of Q_abs)'
      % (max(q0) if q0 else 0, 100.0 * (max(q0) if q0 else 0) / 1048575.0))
print('  RED epochs            : %d'
      % sum(1 for r in qc if r.get('zone') == 'RED'))
print('  scope_violations      : %d'
      % int(g(qc[-1], 'scope_violations') if qc else 0))
print('  ownership_transitions : %d'
      % int(g(qc[-1], 'ownership_transitions') if qc else 0))
print('  path_metadata_missing : %d'
      % int(g(qc[-1], 'path_metadata_missing') if qc else 0))
pfc = rows('pfc_events.csv')
print('  PFC events            : %d' % len(pfc))
retx = sum(g(r, 'retx_bytes') for r in fs)
print('  retx bytes (all flows): %.0f' % retx)
