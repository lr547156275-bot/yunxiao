# -*- coding: utf-8 -*-
# Diagnose: winner cell commands bg at ~317G post-batch but bg acked bytes
# stop at ~30ms.  Where does the command chain break?
import csv
import os
import sys

D = sys.argv[1] if len(sys.argv) > 1 else \
    '/work/v2_400g/results/scrv2_d08_b020'


def rd(p):
    if not os.path.isfile(p):
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


print('== bg (flow 0) rate transitions ==')
rt = rd(D + '/rate_transition.csv')
bg = [r for r in rt if r.get('flow_id') == '0']
print('total transitions for flow 0: %d' % len(bg))
for r in bg[-8:]:
    print(' t=%.3fms %s->%s old=%.1fG new=%.1fG applied_after=%sG reason=%s '
          'owner=%s->%s kind=%s'
          % (int(r['time_ns']) / 1e6, r['phase_before'], r['phase_after'],
             int(r['old_rate_bps']) / 1e9, int(r['new_rate_bps']) / 1e9,
             '%.1f' % (int(r['applied_rate_after_bps']) / 1e9)
             if r.get('applied_rate_after_bps') else '?',
             r['reason'], r['owner_before'], r['owner_after'],
             r.get('actuation_kind', '?')))

print('')
print('== bg actual tx from selected_flow_timeseries ==')
ts = rd(D + '/selected_flow_timeseries.csv')
if ts:
    cols = list(ts[0].keys())
    print('columns: %s' % ','.join(cols))
    bgt = [r for r in ts if r.get('flow_id') == '0']
    step = max(1, len(bgt) // 12)
    for r in bgt[::step]:
        print('  ' + ','.join('%s=%s' % (k, r[k]) for k in cols[:8]))
else:
    print('(missing/empty)')

print('')
print('== applied_rate_audit (flow 0, last 8) ==')
ar = rd(D + '/applied_rate_audit.csv')
if ar:
    cols = list(ar[0].keys())
    print('columns: %s' % ','.join(cols))
    fa = [r for r in ar if r.get('flow_id') == '0']
    for r in fa[-8:]:
        print('  ' + ','.join('%s=%s' % (k, r[k]) for k in cols))
else:
    print('(missing/empty)')

print('')
print('== sba_events tail ==')
se = rd(D + '/sba_events.csv')
if se:
    cols = list(se[0].keys())
    print('columns: %s' % ','.join(cols))
    for r in se[-6:]:
        print('  ' + ','.join('%s=%s' % (k, r[k]) for k in cols))
else:
    print('(missing/empty)')

print('')
print('== flow_timing bg row ==')
for r in rd(D + '/flow_timing.csv'):
    try:
        if float(r['total_size_bytes']) > 2**30:
            print('  ' + ','.join('%s=%s' % (k, v) for k, v in r.items()))
    except (ValueError, KeyError):
        pass
