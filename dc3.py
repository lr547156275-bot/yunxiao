import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
print("=== the actuation chain, legacy vs credit, from admission.csv ===")
for D,lab in (('fx_s3_legacy_out','legacy'),('fx_s3_t025_out','t=0.25')):
    ad=list(csv.DictReader(open(D+'/admission.csv')))
    inc=[r for r in ad if r['flow_id']!='0']
    if not inc: continue
    r=inc[0]
    print('  --- %s ---' % lab)
    for k in ('plan_start_ns','plan_complete_ns','application_ready_ns',
              'network_release_ns','base_rate_bps','admit_rate_bps','initial_rate_bps'):
        if k in r: print('    %-24s %s' % (k, r[k]))
    # per-flow admitted rate
    rates=set(x['admit_rate_bps'] for x in inc)
    print('    distinct admit_rate over %d incast flows: %s' % (len(inc), sorted(rates)[:3]))
print()
print("=== so the chain is ===")
print("  credit computed at the switch  : t = 2.000000000 s (epoch tick)")
print("  boosted rate applied to flows  : t = 2.000000000 s (same tick; admission")
print("                                   and the epoch coincide at release)")
print("  first packet queued at 84:1    : see below")
ts=list(csv.DictReader(open('fx_s3_t025_out/selected_link_timeseries.csv')))
for r in ts:
    if float(r['time'])>=2.0 and float(r['queue_bytes'] or 0)>0:
        print('                                   t = %.9f s' % float(r['time'])); break
print()
print("=== command actuation delay vs network propagation ===")
print("  command actuation (switch decision -> sender rate) : 0 us  (same epoch tick)")
print("  network propagation (sender -> bottleneck queue)   : the gap above")
print("  boosted-rate active duration (UNBOUNDED today)     : until the next replan")
print("                                                        revokes it -- this is")
print("                                                        the defect being fixed")
