import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
D='fx_s3_t025_out'
print("=== STEP 1: the actuation delay chain, from existing traces ===")
cred=list(csv.DictReader(open(D+'/delay_credit.csv')))
# the 4 in-batch credit epochs
inb=[r for r in cred if 2.0 <= int(r['timestamp_ns'])/1e9 <= 2.071028 and int(r['credit_bps'])>0]
print('  credit_issue_time (first)      = %.9f s' % (int(inb[0]['timestamp_ns'])/1e9))
print('  credit_issue_time (last of 4)  = %.9f s' % (int(inb[-1]['timestamp_ns'])/1e9))
print('  issue epochs = %d, spaced %.1f us apart' % (len(inb),
      (int(inb[1]['timestamp_ns'])-int(inb[0]['timestamp_ns']))/1e3))
print()
# when did the boosted rate reach the flows? rate_transition.csv records applies
p=D+'/rate_transition.csv'
if os.path.exists(p):
    rt=list(csv.DictReader(open(p)))
    print('  rate_transition.csv columns: %s' % ', '.join(list(rt[0].keys())[:9]))
    inw=[r for r in rt if 2.0 <= float(r.get('time_ns', r.get('timestamp_ns','0')))/1e9 <= 2.08]
    print('  transitions in [2.00, 2.08] s: %d' % len(inw))
    for r in inw[:4]:
        t=float(r.get('time_ns', r.get('timestamp_ns','0')))/1e9
        print('    t=%.9f flow=%s old=%s target=%s' % (t, r.get('flow_id'),
              r.get('old_rate_bps'), r.get('target_rate_bps')))
print()
# when did the first boosted packet show at the bottleneck? queue leaves 0
ts=list(csv.DictReader(open(D+'/selected_link_timeseries.csv')))
for r in ts:
    t=float(r['time'])
    if t >= 2.0 and float(r['queue_bytes'] or 0) > 0:
        print('  first_boosted_packet_at_bottleneck = %.9f s (queue leaves 0)' % t)
        break
# drain decision
dr=[r for r in cred if int(r['drain_bps'])>0 and 2.0 <= int(r['timestamp_ns'])/1e9 <= 2.08]
if dr:
    print('  drain_decision_time (first)        = %.9f s' % (int(dr[0]['timestamp_ns'])/1e9))
print()
print('=== derived intervals ===')
t_iss=int(inb[0]['timestamp_ns'])/1e9
q0=None
for r in ts:
    t=float(r['time'])
    if t>=2.0 and float(r['queue_bytes'] or 0)>0:
        q0=t; break
if q0: print('  issue -> first packet queued : %.3f us' % ((q0-t_iss)*1e6))
if dr: print('  issue -> drain decision      : %.3f us' % ((int(dr[0]['timestamp_ns'])/1e9-t_iss)*1e6))
print('  configured epoch/plan/ctrl   : 5 / 5 / 5 us  (H_eff = 15 us)')
print('  base RTT                     : 15.2 us  <- the lease duration to use')
