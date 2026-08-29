import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; RTT=15.2e-6; QHN=19000; QHS=67072+19000
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
    over=rows=0; credmax=0.0
    cr=d+'/delay_credit.csv'
    if os.path.exists(cr):
        cc=list(csv.DictReader(open(cr))); rows=len(cc)
        over=sum(1 for r in cc if r['oversubscribed']=='1')
        credmax=max([float(r['credit_bps']) for r in cc] or [0])
    return dict(mean=sum(fct)/len(fct), p99=fct[int(len(fct)*0.99+0.999)-1],
        cct=(last-1.9)*1000,
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q), util=sum(u)/len(u),
        ecn=sum(float(r['ecn_marks_delta'] or 0) for r in ts),
        pfc=sum(float(r['pfc_event_delta'] or 0) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fs),
        over=over, rows=rows, credmax=credmax,
        above_qhn=sum(1 for x in q if x>QHN)/len(q)*100,
        above_qhs=sum(1 for x in q if x>QHS)/len(q)*100)
print('=== 8-cell queue-delay-credit preflight ===')
print('  q_hard_normal=19000 B (1.00 RTT)   q_hard_startup=86072 B (4.53 RTT)')
print()
hdr=('cell','mean','p99','CCT','gp_G','q_mean','q_peak','pk/RTT','util','ECN','PFC','retx','over')
print('  %-14s %-8s %-8s %-9s %-6s %-9s %-9s %-7s %-7s %-5s %-4s %-5s %s' % hdr)
res={}
for tag in ('s3','s4'):
    for m,lab in (('legacy','legacy'),('t025','t=0.25'),('t050','t=0.50'),('t080','t=0.80')):
        n='qc_%s_%s'%(tag,m)
        if not os.path.exists(n+'_out/flow_summary.csv'): continue
        r=load(n); res[(tag,m)]=r
        print('  %-14s %-8.3f %-8.3f %-9.3f %-6.3f %-9.0f %-9.0f %-7.2f %-7.4f %-5.0f %-4.0f %-5.0f %d/%d'
              % (tag.upper()+' '+lab, r['mean'], r['p99'], r['cct'], r['gp'],
                 r['qmean'], r['qpeak'], r['qpeak']*8/C/RTT, r['util'],
                 r['ecn'], r['pfc'], r['retx'], r['over'], r['rows']))
    print()
print('=== does queue rise with target (diagnostic of a working credit)? ===')
for tag in ('s3','s4'):
    line='  %s: ' % tag.upper()
    for m in ('legacy','t025','t050','t080'):
        if (tag,m) in res: line += '%s=%.0f  ' % (m, res[(tag,m)]['qpeak'])
    print(line)
print()
print('=== time above the hard bounds (%) ===')
print('  %-14s %-14s %s' % ('cell','above 1.00RTT','above 4.53RTT'))
for tag in ('s3','s4'):
    for m in ('legacy','t025','t050','t080'):
        if (tag,m) not in res: continue
        r=res[(tag,m)]
        print('  %-14s %-14.2f %.2f' % (tag.upper()+' '+m, r['above_qhn'], r['above_qhs']))
