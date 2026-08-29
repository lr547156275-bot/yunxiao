import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
print("=== read the ACTUAL available capacity at the admission epoch ===")
for D,lab in (('fx_s3_legacy_out','legacy'),('fx_s3_t025_out','credit')):
    ad=list(csv.DictReader(open(D+'/admission.csv')))
    inc=[r for r in ad if r['flow_id']!='0']
    r=inc[0]
    print('  --- %s ---' % lab)
    for k in ('effective_capacity_bps','base_rate_bps','admit_rate_bps','floor_scale','capacity_valid'):
        if k in r: print('    %-24s %s' % (k, r[k]))
    print('    incast admit sum = %.6f G over %d flows' % (sum(float(x['admit_rate_bps']) for x in inc)/1e9, len(inc)))
print()
print("=== and what the credit path itself recorded at that epoch ===")
cr=list(csv.DictReader(open('fx_s3_t025_out/delay_credit.csv')))
first=[r for r in cr if int(r['timestamp_ns'])==2000000000]
if first:
    r=first[0]
    for k in ('queue_bytes','q_target_bytes','credit_bps','total_budget_bps',
              'old_share_bps','new_share_bps','sum_target_bps','capacity_bps'):
        print('    %-22s %s' % (k, r[k]))
