import csv, os
C=10e9; Q=262144
ARMS=[('E DCQCN','sr_dcqcn_s3_out'),('A base','mb_off_out'),
      ('phase','mb_phase_out'),('both','mb_both_out')]
def pc(v,q):
    s=sorted(v); return s[min(len(s)-1,int(q*(len(s)-1)))] if v else None
def fl(d):
    inc=[];bg=[]
    for r in csv.DictReader(open(os.path.join(d,'flow_summary.csv'))):
        try: sz=int(float(r['total_size_bytes']))
        except: continue
        f=None
        if r.get('fct'):
            try: f=float(r['fct'])
            except: pass
        st=fi=None
        try: st=float(r['start_time'])
        except: pass
        try: fi=float(r['finish_time'])
        except: pass
        rec=dict(sz=sz,f=f,st=st,fi=fi,ak=float(r['acked_bytes'] or 0),
                 dn=str(r['completed']).strip() not in ('0','false',''),
                 rx=int(float(r.get('retx_events') or 0)))
        (bg if sz>=(1<<30) else inc).append(rec)
    dn=[x for x in inc if x['dn'] and x['f'] is not None]
    if not dn: return None
    t0=min(x['st'] for x in dn); t1=max(x['fi'] for x in dn)
    bct=t1-t0; tb=sum(x['sz'] for x in dn)
    fv=sorted(x['f'] for x in dn)
    return dict(n=len(inc),done=len(dn),bct=bct,
        gp=8.0*tb/bct if bct>0 else 0,
        mean=sum(fv)/len(fv),p99=pc(fv,.99),mx=fv[-1],spr=fv[-1]-fv[0],
        rx=sum(x['rx'] for x in inc)+sum(x['rx'] for x in bg),
        bgak=bg[0]['ak'] if bg else None,
        bggp=8.0*bg[0]['ak']/(t1-1.0) if bg and t1>1.0 else None,
        t0=t0,t1=t1)
def busy(d,lo,hi):
    p=os.path.join(d,'tx_serialization.csv')
    if not os.path.exists(p): return None
    b={};pr=[]
    for r in csv.DictReader(open(p)):
        k=(r['node_id'],r['if_index'],r['packet_uid']); t=int(r['time_ns'])
        if r['event']=='TX_BEGIN': b[k]=(t,int(r['packet_bytes']))
        elif r['event']=='TX_END' and k in b:
            s,nb=b.pop(k); pr.append((s,t,nb))
    pr=sorted(x for x in pr if x[0]>=lo and x[1]<=hi)
    if not pr: return None
    bs=0;g=[];cs,ce=pr[0][0],pr[0][1]
    for s,e,nb in pr[1:]:
        if s>ce: bs+=ce-cs; g.append(s-ce); cs=s
        ce=max(ce,e)
    bs+=ce-cs; sp=pr[-1][1]-pr[0][0]
    return dict(f=bs/float(sp),n=len(pr),ng=len(g),gt=sum(g),
                gm=max(g) if g else 0,g50=pc(g,.5))
def qs(d):
    p=os.path.join(d,'selected_link_timeseries.csv')
    if not os.path.exists(p): return None
    v=[]
    for r in csv.DictReader(open(p)):
        try: v.append(float(r['queue_bytes']))
        except: pass
    return dict(m=sum(v)/len(v),p99=pc(v,.99),mx=max(v)) if v else None
def pfc(d):
    p=os.path.join(d,'pfc_events.csv')
    return max(0,sum(1 for _ in open(p))-1) if os.path.exists(p) else 0
R={}
for nm,d in ARMS:
    f=fl(d)
    R[nm]=dict(f=f,q=qs(d),p=pfc(d),
        b=busy(d,int(f['t0']*1e9),int(f['t1']*1e9)) if f else None)
H='%-26s'+'%14s'*len(ARMS)
print(H%tuple(['metric']+[n for n,_ in ARMS]))
print('-'*(26+14*len(ARMS)))
def L(l,fn,fm='%.4f'):
    o=[]
    for n,_ in ARMS:
        try: x=fn(R[n]); o.append('NA' if x is None else fm%x)
        except: o.append('NA')
    print(H%tuple([l]+o))
L('BCT (ms)',lambda r:r['f']['bct']*1e3,'%.6f')
L('batch goodput (Gbps)',lambda r:r['f']['gp']/1e9,'%.6f')
L('completed',lambda r:r['f']['done'],'%.0f')
L('FCT mean (us)',lambda r:r['f']['mean']*1e6,'%.1f')
L('FCT p99 (us)',lambda r:r['f']['p99']*1e6,'%.1f')
L('FCT spread (us)',lambda r:r['f']['spr']*1e6,'%.1f')
L('backlogged busy',lambda r:r['b']['f'],'%.6f')
L('gap count',lambda r:r['b']['ng'],'%.0f')
L('gap total (us)',lambda r:r['b']['gt']/1e3,'%.1f')
L('gap p50 (ns)',lambda r:r['b']['g50'],'%.0f')
L('gap max (ns)',lambda r:r['b']['gm'],'%.0f')
L('queue mean (B)',lambda r:r['q']['m'],'%.0f')
L('queue p99 (B)',lambda r:r['q']['p99'],'%.0f')
L('queue max (B)',lambda r:r['q']['mx'],'%.0f')
L('bg acked (MB)',lambda r:r['f']['bgak']/1e6,'%.1f')
L('bg goodput (Gbps)',lambda r:r['f']['bggp']/1e9,'%.6f')
L('PFC',lambda r:r['p'],'%.0f')
L('retx',lambda r:r['f']['rx'],'%.0f')
e=R['E DCQCN'];b=R['both']
print('\n=== HARD GATES: both vs DCQCN ===')
def g(n,c,d): print('  %-40s %s  %s'%(n,'PASS' if c else 'FAIL',d))
g('backlogged busy >= 0.99',b['b'] and b['b']['f']>=0.99,
  '%.6f'%b['b']['f'] if b['b'] else 'NA')
bi=100.0*(e['f']['bct']-b['f']['bct'])/e['f']['bct']
g('BCT improves >= 1%',bi>=1.0,'%+.2f%%'%bi)
gi=100.0*(b['f']['gp']-e['f']['gp'])/e['f']['gp']
g('batch goodput improves >= 1%',gi>=1.0,'%+.2f%%'%gi)
g('p99 FCT not worse',b['f']['p99']<=e['f']['p99'],
  '%.1f vs %.1f us'%(b['f']['p99']*1e6,e['f']['p99']*1e6))
if e['f']['bggp'] and b['f']['bggp']:
    bd=100.0*(b['f']['bggp']-e['f']['bggp'])/e['f']['bggp']
    g('bg goodput drop <= 1%',bd>=-1.0,'%+.2f%%'%bd)
g('queue max < 256 KB',b['q'] and b['q']['mx']<Q,
  '%.0f vs %d'%(b['q']['mx'],Q) if b['q'] else 'NA')
g('PFC/drop/retx = 0',b['p']==0 and b['f']['rx']==0,
  'pfc=%d retx=%d'%(b['p'],b['f']['rx']))
