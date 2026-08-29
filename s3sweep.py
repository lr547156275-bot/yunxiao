import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; RTT=15.2e-6
def load(n):
    d=n+'_out'
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    last=max(float(r['finish_time']) for r in inc)
    w=[r for r in ts if 1.9<=float(r['time'])<=last]
    q=[float(r['queue_bytes'] or 0) for r in w]
    u=[float(r['utilization'] or 0) for r in w]
    cr=d+'/delay_credit.csv'
    over=credmax=0; rows=0
    if os.path.exists(cr):
        cc=list(csv.DictReader(open(cr))); rows=len(cc)
        over=sum(1 for r in cc if r['oversubscribed']=='1')
        credmax=max([float(r['credit_bps']) for r in cc] or [0])
    return dict(mean=sum(fct)/len(fct), p99=fct[int(len(fct)*0.99+0.999)-1],
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q), util=sum(u)/len(u),
        ecn=sum(float(r['ecn_marks_delta'] or 0) for r in ts),
        pfc=sum(float(r['pfc_event_delta'] or 0) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fs),
        rows=rows, over=over, credmax=credmax)
print('=== S3: target sweep (does queue rise with target? does credit fire?) ===')
print('  %-9s %-9s %-9s %-8s %-10s %-10s %-7s %-6s %-5s %-6s %s'
      % ('mode','mean','p99','gp_G','q_mean','q_peak','q_pk/RTT','util','ECN','PFC','oversub_rows'))
for n,lab in (('qc_s3_legacy','legacy'),('qc_s3_t025','t=0.25'),
              ('qc_s3_t050','t=0.50'),('qc_s3_t080','t=0.80')):
    if not os.path.exists(n+'_out/flow_summary.csv'): continue
    r=load(n)
    print('  %-9s %-9.3f %-9.3f %-8.3f %-10.0f %-10.0f %-7.2f %-6.4f %-5.0f %-6.0f %d/%d'
          % (lab, r['mean'], r['p99'], r['gp'], r['qmean'], r['qpeak'],
             r['qpeak']*8/C/RTT, r['util'], r['ecn'], r['pfc'], r['over'], r['rows']))
print()
print('  q_hard_normal = 19000 B = 1.00 RTT')
