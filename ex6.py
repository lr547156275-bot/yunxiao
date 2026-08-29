import csv, os
C=10e9
cells=[('rho=0.55','au_s3_rho055'),('rho=0.75','au_s3_rho075'),
       ('rho=0.90','au_s3_rho090'),('rho=0.9875','au_s3_rho09875'),
       ('HPCC','au_s3_hpcc')]
os.chdir('/work/simulation/experiment/scheme1_sba')
def rows(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []
print("%-12s %9s %9s %9s %9s %8s %10s %8s %7s %7s" % (
    "cell","BCT_ms","FCTmean","FCTp99","FCTmax","spread","qpeak_B","qdel_us","PFC","retx"))
res={}
for lbl,n in cells:
    fs=rows(n+'_out/flow_summary.csv')
    bg=[r for r in fs if r['src']=='65']
    bgid=set(id(r) for r in bg)
    inc=[r for r in fs if id(r) not in bgid and r['completed']=='1']
    if not inc: print("%-12s NO DATA"%lbl); continue
    st=min(float(r['start_time']) for r in inc)
    fi=max(float(r['finish_time']) for r in inc)
    f=sorted(float(r['fct']) for r in inc)
    lt=rows(n+'_out/selected_link_timeseries.csv')
    qp=max(float(r['queue_bytes']) for r in lt) if lt else 0
    pf=sum(float(r.get('pfc_pause_ns_delta',0)) for r in lt)
    rx=sum(float(r['retx_bytes']) for r in fs)
    res[lbl]=dict(bct=(fi-st)*1e3, fm=sum(f)/len(f)*1e3, qp=qp)
    print("%-12s %9.4f %9.4f %9.4f %9.4f %8.4f %10.0f %8.2f %7.0f %7.0f" % (
        lbl,(fi-st)*1e3,sum(f)/len(f)*1e3,f[int(0.99*(len(f)-1))]*1e3,f[-1]*1e3,
        f[-1]/f[0],qp,qp*8/C*1e6,pf,rx))
print()
print("=== CBAP vs corrected HPCC ===")
h=res.get('HPCC')
if h:
    for lbl,_ in cells[:-1]:
        r=res.get(lbl)
        if r: print("  %-11s BCT %8.4f ms vs HPCC %8.4f ms -> %+7.2f%%   qpeak %.0f vs %.0f B"
                    % (lbl,r['bct'],h['bct'],(r['bct']/h['bct']-1)*100,r['qp'],h['qp']))
print()
print("=== background before/during/after (fixed 150ms window) ===")
for lbl,n in cells:
    ts=rows(n+'_out/selected_flow_timeseries.csv')
    b=[r for r in ts if r.get('flow_id')=='0']
    if not b: print("  %-12s no bg series"%lbl); continue
    def rate(lo,hi):
        s=[r for r in b if lo<=float(r['time'])<=hi]
        if len(s)<2: return 0.0
        dt=float(s[-1]['time'])-float(s[0]['time'])
        return (float(s[-1]['snd_una'])-float(s[0]['snd_una']))*8/dt/1e9 if dt>0 else 0.0
    fs=rows(n+'_out/flow_summary.csv')
    inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
    t1=max(float(r['finish_time']) for r in inc) if inc else 2.1
    print("  %-12s before=%.4f during=%.4f after=%.4f G   debt=%.4f Gb"
          % (lbl, rate(1.85,2.0), rate(2.0,t1), rate(t1,t1+0.15),
             (rate(1.85,2.0)-rate(2.0,t1))*(t1-2.0)))
