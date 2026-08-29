import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
D='fx_s3_t025_out'
print("=== which traces carry per-flow rate application times? ===")
for f in sorted(os.listdir(D)):
    p=os.path.join(D,f)
    if f.endswith('.csv'):
        n=sum(1 for _ in open(p))-1
        print('  %-32s %d rows' % (f, n))
print()
print("=== selected_flow_timeseries: when does an incast flow's current_rate rise? ===")
ff=list(csv.DictReader(open(D+'/selected_flow_timeseries.csv')))
f1=[r for r in ff if r['flow_id']=='1' and 1.999 <= float(r['time']) <= 2.001]
print('  flow 1 samples in [1.999, 2.001]: %d' % len(f1))
prev=None
for r in f1[:400]:
    cr=float(r['current_rate'] or 0)
    if prev is not None and cr != prev:
        print('    t=%.9f current_rate %.0f -> %.0f bps' % (float(r['time']), prev, cr))
        if cr > 0: break
    prev=cr
