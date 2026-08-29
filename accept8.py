import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; RTT=15.2e-6
QHN=int(C*RTT/8); QSYNC=64*1048; QHS=QSYNC+QHN
def load(n):
    d=n+'_out'
    fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
    ts=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    fct=sorted(float(r['fct'])*1000 for r in inc)
    last=max(float(r['finish_time']) for r in inc)
    w=[r for r in ts if 1.9<=float(r['time'])<=last]
    q=[float(r['queue_bytes'] or 0) for r in w]
    return dict(n=len(inc), mean=sum(fct)/len(fct),
        p99=fct[int(len(fct)*0.99+0.999)-1], cct=(last-1.9)*1000,
        gp=sum(float(r['flow_goodput']) for r in inc)/1e9,
        qmean=sum(q)/len(q), qpeak=max(q),
        util=sum(float(r['utilization'] or 0) for r in w)/len(w),
        ecn=sum(float(r['ecn_marks_delta'] or 0) for r in ts),
        pfc=sum(float(r['pfc_event_delta'] or 0) for r in ts),
        retx=sum(float(r['retx_bytes']) for r in fs))
L=load('fx_s3_legacy'); T=load('fx_s3_t025')
REF=load('m_cbapsba_s3_seed2')
print('=== bounds: q_hard_normal=%d B (1.00 RTT)  q_sync_floor=%d  q_hard_startup=%d B (%.2f RTT) ==='
      % (QHN, QSYNC, QHS, QHS*8/C/RTT))
print()
print('  %-12s %-14s %-14s %s' % ('metric','legacy','t=0.25RTT','delta'))
for k,f in (('mean','%.3f'),('p99','%.3f'),('cct','%.3f'),('gp','%.4f'),
            ('qmean','%.0f'),('qpeak','%.0f'),('util','%.4f'),
            ('ecn','%.0f'),('pfc','%.0f'),('retx','%.0f')):
    d = '%+.2f%%' % ((T[k]-L[k])/L[k]*100) if L[k] else 'n/a'
    print('  %-12s %-14s %-14s %s' % (k, f%L[k], f%T[k], d))
print()
print('=== ACCEPTANCE ===')
ok=lambda b: 'PASS' if b else 'FAIL'
# 1 legacy reproduces
same=all(abs(L[k]-REF[k])<1e-6 for k in ('mean','p99','gp','qmean','qpeak','ecn','pfc','retx'))
print('  [%s] 1 legacy reproduces the frozen result' % ok(same))
# trace-based checks
cr='fx_s3_t025_out/delay_credit.csv'
rows=list(csv.DictReader(open(cr))) if os.path.exists(cr) else []
print('      credit trace rows: %d' % len(rows))
if rows:
    first=rows[0]
    print('  [%s] 2 first replan phase == SYNC_BURST (phase=%s, q=%s)'
          % (ok(first['phase']=='0'), first['phase'], first['queue_bytes']))
    bad=[r for r in rows if int(r['queue_bytes'])>int(r['q_target_bytes'])
         and not (int(r['credit_bps'])==0 and int(r['drain_bps'])>0
                  and int(r['total_budget_bps'])<int(r['capacity_bps']))]
    nover=[r for r in rows if int(r['queue_bytes'])>int(r['q_target_bytes'])]
    print('  [%s] 3 q>q_target => credit=0 & drain>0 & total<C  (%d/%d rows correct)'
          % (ok(not bad), len(nover)-len(bad), len(nover)))
    print('  [%s] 4 q_peak <= q_hard_startup  (%.0f <= %d)'
          % (ok(T['qpeak']<=QHS), T['qpeak'], QHS))
    lat=[r for r in rows if r['phase']=='1']
    tlat=int(lat[0]['timestamp_ns']) if lat else 0
    print('  [%s] 5 latched to NORMAL only after falling below 1 RTT (t=%.6f s)'
          % (ok(bool(lat)), tlat/1e9))
    nv=[r for r in rows if r['phase']=='1' and int(r['queue_bytes'])>QHN]
    print('  [%s] 6 NORMAL-phase q_hard violations = %d' % (ok(not nv), len(nv)))
print('  [%s] 7 PFC=%.0f drop=0 retx=%.0f' % (ok(T['pfc']==0 and T['retx']==0), T['pfc'], T['retx']))
if rows:
    credfire=[r for r in rows if int(r['credit_bps'])>0]
    over=[r for r in rows if r['oversubscribed']=='1']
    print('  [%s] 8 credit actually fired: %d rows credit>0, %d rows sum(target)>C'
          % (ok(bool(credfire)), len(credfire), len(over)))
    print('      max credit = %.3f G, max budget/C = %.4f'
          % (max(float(r['credit_bps']) for r in rows)/1e9,
             max(float(r['budget_over_capacity']) for r in rows)))
