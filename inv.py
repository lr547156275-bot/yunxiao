import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
print("=== INVARIANT CHECK: is granted credit == aggregate_boosted - aggregate_base? ===")
def agg(D):
    ad=list(csv.DictReader(open(D+'/admission.csv')))
    inc=[r for r in ad if r['flow_id']!='0']
    bg=[r for r in ad if r['flow_id']=='0']
    return inc,bg
li,lb=agg('fx_s3_legacy_out')
ti,tb=agg('fx_s3_t025_out')
a_base=sum(float(r['admit_rate_bps']) for r in li)
a_boost=sum(float(r['admit_rate_bps']) for r in ti)
print('  incast flows: legacy n=%d, credit n=%d' % (len(li),len(ti)))
print('  aggregate_base    (legacy admit sum) = %.6f G' % (a_base/1e9))
print('  aggregate_boosted (credit admit sum) = %.6f G' % (a_boost/1e9))
print('  incremental_credit                   = %.6f G' % ((a_boost-a_base)/1e9))
print()
print('  per-flow: legacy %.6f Mbps -> credit %.6f Mbps'
      % (a_base/len(li)/1e6, a_boost/len(ti)/1e6))
print('  64 x (31.25 - 15.625) Mbps           = %.6f G' % (64*(31.25-15.625)/1e3))
print()
cred=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
inb=[r for r in cred if 2.0 <= int(r['timestamp_ns'])/1e9 <= 2.071028 and int(r['credit_bps'])>0]
print('  trace-reported granted credit_bps    = %.6f G' % (float(inb[0]['credit_bps'])/1e9))
print()
delta=(a_boost-a_base)
rep=float(inb[0]['credit_bps'])
print('=== VERDICT ===')
if abs(delta-rep) < 1e6:
    print('  INVARIANT HOLDS: incremental == reported')
else:
    print('  INVARIANT FAILS: incremental %.3f G vs reported %.3f G (ratio %.3f)'
          % (delta/1e9, rep/1e9, rep/delta if delta else 0))
    print()
    print('  So the reported 2.0 G is NOT the increment over base. Candidates:')
    print('   (a) it is the TOTAL new-batch share, not a delta;')
    print('   (b) the background/old-flow share also moved.')
    print()
    print('  background admit_rate: legacy=%s  credit=%s'
          % (lb[0]['admit_rate_bps'] if lb else 'n/a', tb[0]['admit_rate_bps'] if tb else 'n/a'))
    for D,lab in (('fx_s3_legacy_out','legacy'),('fx_s3_t025_out','credit')):
        ef=list(csv.DictReader(open(D+'/eta_feasibility.csv')))
        if ef:
            r=ef[0]
            print('  %-7s eta_feas: old_share=%.3f G new_share=%.3f G total=%.3f G'
                  % (lab, float(r['old_target_sum_bps'])/1e9,
                     float(r['new_target_sum_bps'])/1e9,
                     float(r['final_sum_target_bps'])/1e9))
