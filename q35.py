# Q3 + Q5: per-flow diagnostics on ONE overlap window, and reconcile the
# per-flow sum against the link's own goodput over the SAME window.
import csv, os
D='/work/simulation/experiment/scheme1_sba/motivation/m2_dcqcn_out'
OUT='/work/simulation/experiment/scheme1_sba/motivation'

link=list(csv.DictReader(open(os.path.join(D,'selected_link_timeseries.csv'))))
flow=list(csv.DictReader(open(os.path.join(D,'selected_flow_timeseries.csv'))))
fsum=list(csv.DictReader(open(os.path.join(D,'flow_summary.csv'))))
rnd ={r['flow_id']: r for r in csv.DictReader(open(os.path.join(D,'round_summary.csv')))}

# ONE overlap window for everything: incast release -> last incast finish.
REL=1.9
last=max(float(r['finish_time']) for r in fsum if r['src']!='65' and r['completed']=='1')
W0,W1=REL,last
print('=== single overlap window: [%.4f, %.4f] s  (%.1f ms) ===' % (W0,W1,(W1-W0)*1000))

# link goodput over that window, from tx_bytes_delta
lw=[r for r in link if W0<=float(r['time'])<=W1]
link_bytes=sum(float(r['tx_bytes_delta']) for r in lw)
link_gbps=link_bytes*8/(W1-W0)/1e9
ecn_delta=sum(float(r['ecn_marks_delta']) for r in lw)
print('  link 84:1 tx over window = %.3f Gbps   ecn_marks_delta = %.0f' % (link_gbps, ecn_delta))

# per-traced-flow progress over the SAME window
prog={}
for r in flow:
    t=float(r['time']); fid=r['flow_id']
    if W0<=t<=W1:
        v=float(r['snd_una'])
        d=prog.setdefault(fid,[None,None])
        if d[0] is None: d[0]=v
        d[1]=v
print('  traced flows in window: %s' % sorted(prog.keys()))

rows=[]
tot_traced=0.0
for r in fsum:
    fid=r['flow_id']; src=r['src']
    isbg = (src=='65')
    # rate before the collective (background only; incast does not exist yet)
    before=''
    if isbg:
        s=[(float(x['time']),float(x['snd_una'])) for x in flow if x['flow_id']==fid and 1.5<=float(x['time'])<=REL]
        if len(s)>=2:
            s.sort(); before='%.6f'%((s[-1][1]-s[0][1])*8/(s[-1][0]-s[0][0])/1e9)
    during=''
    if fid in prog and prog[fid][0] is not None:
        g=(prog[fid][1]-prog[fid][0])*8/(W1-W0)/1e9
        during='%.6f'%g
        tot_traced+=g
    rr=rnd.get(fid,{})
    rows.append(dict(
        flow_id=fid, src=src, dst=r['dst'],
        pg=('0' if isbg else '3'),
        queue_index=('0' if isbg else '3'),
        role=('background' if isbg else 'incast'),
        total_size_bytes=r['total_size_bytes'],
        acked_bytes=r['acked_bytes'],
        completed=r['completed'],
        fct_s=r['fct'],
        goodput_whole_flow_bps=r['flow_goodput'],
        rate_before_overlap_gbps=before,
        rate_during_overlap_gbps=during,
        dcqcn_start_rate_bps=rr.get('start_rate',''),
        dcqcn_min_rate_bps=rr.get('minimum_rate',''),
        dcqcn_end_rate_bps=rr.get('end_rate',''),
        cnp_received=rr.get('cnp_count',''),
        retx_bytes=r['retx_bytes'],
    ))

p=os.path.join(OUT,'m2_dcqcn_perflow_overlap_diag.csv')
with open(p,'w') as f:
    w=csv.writer(f)
    w.writerow(['# per-flow diagnostics over ONE overlap window [%.4f, %.4f] s' % (W0,W1)])
    w.writerow(['# queue_index = pg (switch-node.cc:181 maps udp.pg -> qIndex)'])
    w.writerow(['# NOTE switch-mmu.cc:106: ShouldSendCN returns false when qIndex==0,'])
    w.writerow(['#      so pg=0 traffic is EXEMPT from ECN marking by construction.'])
    w.writerow(['# cnp_received is per-flow from round_summary.csv, not a filtered aggregate.'])
    w.writerow(list(rows[0].keys()))
    for r in rows: w.writerow(list(r.values()))
print('  wrote %s (%d flows)' % (os.path.basename(p), len(rows)))
print()
print('=== Q5 reconciliation, SAME window for both sides ===')
print('  sum of traced per-flow goodput = %.3f Gbps  (only flows 0,1,2,3 are traced)' % tot_traced)
# full accounting: background traced + all incast from flow_summary over the window
inc=[r for r in fsum if r['src']!='65' and r['completed']=='1']
inc_bytes=sum(float(r['acked_bytes']) for r in inc)
inc_gbps=inc_bytes*8/(W1-W0)/1e9
bg_during=float([r['rate_during_overlap_gbps'] for r in rows if r['role']=='background'][0])
print('  all 64 incast acked over window = %.3f Gbps' % inc_gbps)
print('  background over window          = %.3f Gbps' % bg_during)
print('  per-flow total                  = %.3f Gbps' % (inc_gbps+bg_during))
print('  link-reported total             = %.3f Gbps' % link_gbps)
print('  difference                      = %.3f Gbps (%.2f%%)' % (inc_gbps+bg_during-link_gbps, (inc_gbps+bg_during-link_gbps)/link_gbps*100))
