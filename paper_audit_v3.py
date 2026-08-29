# -*- coding: utf-8 -*-
# Data-dependency audit numbers for PAPER_*_v3 deliverables.  Read-only.
import csv
import os

V2 = '/work/v2_400g'
RS = V2 + '/results'
MAIN_ARMS = ['cbap', 'hpcc', 'dcqn', 'dctcp', 'timely']

rows = list(csv.DictReader(open(V2 + '/reports/final_results_v2.csv')))
main = [r for r in rows if r['arm'] in MAIN_ARMS and r['buffer_mb'] == '64']
print('main matrix rows (5 arms x 6 scen x 3 rates, buf=64): %d' % len(main))
inc = [r['tag'] for r in main if r['n_complete'] != r['fanin']]
print('  incomplete: %s' % (inc or 'none'))

cb = [r for r in rows if r['arm'] in ('cbap', 'cbap0')]
print('CBAP-configured cells in the 120: %d; PFC nonzero among them: %d'
      % (len(cb), sum(1 for r in cb if int(r['pfc']) > 0)))
bl = [r for r in rows if r['arm'] not in ('cbap', 'cbap0')]
nz = [r for r in bl if int(r['pfc']) > 0]
print('baseline cells: %d; with PFC>0: %d; max PFC: %d'
      % (len(bl), len(nz), max(int(r['pfc']) for r in bl)))

# CCT-BCT gap check on two representative cells
for tag in ('fm400g_s2_cbap', 'fm400g_s2_dcqn'):
    ft = list(csv.DictReader(open(RS + '/' + tag + '/flow_timing.csv')))
    gaps = set()
    for r in ft:
        if r['flow_id'] == '0':
            continue
        try:
            gaps.add(int(r['network_release_ns']) -
                     int(r['application_ready_ns']))
        except ValueError:
            continue
    print('%s: release-ready gaps (ns): %s' % (tag, sorted(gaps)))

# handoff timing distribution (first_feedback - release) for two cells
for tag in ('fm200g_s2_cbap', 'fm400g_s2_cbap'):
    p = RS + '/' + tag + '/sba_events.csv'
    if not os.path.isfile(p):
        print('%s: sba_events missing' % tag)
        continue
    deltas = []
    for r in csv.DictReader(open(p)):
        if r.get('state_transition') == 'STARTUP_SENDING->DCQCN_OWNED':
            try:
                deltas.append((int(r['first_feedback_time']) -
                               int(r['release_time'])) / 1e3)
            except ValueError:
                continue
    deltas.sort()
    if deltas:
        print('%s: handoffs=%d  first_feedback-release us: min=%.1f '
              'p50=%.1f max=%.1f; >=1000us: %d'
              % (tag, len(deltas), deltas[0],
                 deltas[len(deltas) // 2], deltas[-1],
                 sum(1 for d in deltas if d >= 1000)))
    else:
        print('%s: no handoff transitions found' % tag)

# holds / readmissions census across formal cbap cells
holds = readmits = 0
cells = 0
for tag in sorted(os.listdir(RS)):
    if not tag.startswith('fm') or '_cbap' not in tag:
        continue
    p = RS + '/' + tag + '/sba_events.csv'
    if not os.path.isfile(p):
        continue
    cells += 1
    for r in csv.DictReader(open(p)):
        t = r.get('state_transition', '')
        if t.endswith('->ADMISSION_HOLD'):
            holds += 1
        if t == 'ADMISSION_HOLD->STARTUP_SENDING':
            readmits += 1
print('formal cbap cells scanned: %d; ->ADMISSION_HOLD events: %d; '
      'readmissions: %d' % (cells, holds, readmits))
