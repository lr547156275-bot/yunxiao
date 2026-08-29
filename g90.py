import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; PAY=1000.0; WIRE=1048.0; R=WIRE/PAY
Q_ABS=1048575.0; M_SAFE=67072.0
M_ACT=0.30*C*175e-6/8.0
Q_RED=Q_ABS-M_SAFE; Q_HIGH=Q_RED-M_ACT; Q_LOW=0.5*Q_ABS
EP=5000.0
d='qc_s3_rho090_out'
qc=list(csv.DictReader(open(d+'/qc_trace.csv')))
lk=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
def n(v,x=0.0):
    try: return float(v)
    except: return x
print("=== S3 rho=0.90, hard gates ===")
print("  qc_trace rows=%d cols=%d" % (len(qc), len(qc[0])))
q0=[n(r['q0']) for r in qc]; qs=[n(r['q_stop']) for r in qc]
qsafe=[n(r['q_safe']) for r in qc]
qlink=[n(r['queue_bytes']) for r in lk]
bg=[r for r in fs if r['src']=='65']; bgid=set(id(r) for r in bg)
inc=[r for r in fs if id(r) not in bgid]; done=[r for r in inc if r['completed']=='1']
g=[]
def ck(k,ok,det): g.append((k,ok,det)); 
ck("64/64 incast", len(done)==64, "%d/%d"%(len(done),len(inc)))
ck("background in summary", len(bg)>0, "%d bg rows, acked=%.3f Gb"%(len(bg), n(bg[0]['acked_bytes'])*8/1e9 if bg else 0))
pk=max(qlink)
ck("actual queue peak <= Q_abs", pk<=Q_ABS, "%.0f B = %.1f%% of Q_abs"%(pk,100*pk/Q_ABS))
pfc=sum(n(r.get('pfc_pause_ns_delta',0)) for r in lk)
ev=sum(n(r.get('pfc_event_delta',0)) for r in lk)
ck("PFC=0", pfc==0 and ev==0, "pause=%.0f ev=%.0f"%(pfc,ev))
rtx=sum(n(r['retx_bytes']) for r in fs)
ck("retransmission=0", rtx==0, "%.0f B"%rtx)
v=[i for i,r in enumerate(qc) if n(r['q_stop'])<n(r['q0'])-1]
ck("Q_stop < q0 same-epoch = 0", len(v)==0, "%d"%len(v))
dup=sum(n(r['duplicate_qp_count']) for r in qc)
ck("duplicate floor count=0", dup==0, "%.0f"%dup)
fw=set(n(r['floor_wire_bps']) for r in qc if n(r['owns_rates'])==1)
fp=set(n(r['floor_payload_bps']) for r in qc if n(r['owns_rates'])==1)
ck("floor payload=6.500G when owning", any(abs(x-6.5e9)<1e6 for x in fp),
   "payload set: %s" % sorted(x/1e9 for x in fp)[-3:])
ck("floor wire=6.812G when owning", any(abs(x-6.812e9)<2e6 for x in fw),
   "wire set: %s" % sorted(x/1e9 for x in fw)[-3:])
sd=[n(r['sender_effective_wire_bps']) for r in qc]
ar=[n(r['arrival_safe_wire_bps']) for r in qc]
ck("sender and arrival separately reported",
   any(a!=s for a,s in zip(ar,sd)), "differ in %d rows"%sum(1 for a,s in zip(ar,sd) if a!=s))
red=[i for i,r in enumerate(qc) if r['zone']=='RED']
segs=[]; cur=None
for i,r in enumerate(qc):
    if r['zone']=='RED':
        cur=[i,i] if cur is None else [cur[0],i]
    elif cur: segs.append(tuple(cur)); cur=None
if cur: segs.append(tuple(cur))
ck("RED can exit", (not segs) or segs[-1][1]<len(qc)-2,
   "%d segments, total %.2f ms, longest %.3f ms" %
   (len(segs), len(red)*EP/1e6, (max((b-a+1) for a,b in segs)*EP/1e6) if segs else 0))
both=[r for r in qc if n(r['boost_effective'])>0 and n(r['drain'])>0]
ck("boost/drain not both nonzero", len(both)==0, "%d"%len(both))
iv=sum(n(r['invariant_violations']) for r in qc)
ck("controller invariant violations=0", iv==0, "%.0f"%iv)
step=35; resid=[]
for i in range(len(qc)-step):
    p=max(q0[i:i+step+1]); rr=p-qs[i]
    if rr>0: resid.append(rr)
resid.sort()
ck("Q_stop residual max <= M_safe", (not resid) or resid[-1]<=M_SAFE,
   "max=%.0f p95=%.0f vs M_safe=%.0f"%(resid[-1] if resid else 0,
     resid[int(0.95*(len(resid)-1))] if resid else 0, M_SAFE))
print()
zc={}
for r in qc: zc[r['zone']]=zc.get(r['zone'],0)+1
print("  zones: %s" % {k:"%d (%.2f%%)"%(v,100.0*v/len(qc)) for k,v in sorted(zc.items())})
b=[n(r['boost_effective']) for r in qc]; dr=[n(r['drain']) for r in qc]
sr=[n(r['sumR_effective']) for r in qc]
print("  boost>0: %d epochs max %.4fC | drain>0: %d max %.4fC"
      % (len([x for x in b if x>0]), max(b)/C, len([x for x in dr if x>0]), max(dr)/C))
print("  sumR>C: %d | sumR<C: %d | sumR min=%.3fG max=%.3fG"
      % (len([x for x in sr if x>C]), len([x for x in sr if x<C]), min(sr)/1e9, max(sr)/1e9))
print("  queue peak(link)=%.0f B (%.2f us) = %.1f%% of Q_abs" % (pk, pk*8/C*1e6, 100*pk/Q_ABS))
if done:
    f=sorted(n(r['fct']) for r in done)
    print("  FCT mean=%.4f p99=%.4f ms  BCT=%.4f ms"
          % (sum(f)/len(f)*1e3, f[int(0.99*(len(f)-1))]*1e3,
             (max(n(r['finish_time']) for r in done)-min(n(r['start_time']) for r in done))*1e3))
print()
fail=0
for k,ok,det in g:
    print("  [%s] %-40s %s" % ("PASS" if ok else "FAIL", k, det))
    if not ok: fail+=1
print()
print("  %d/%d gates passed" % (len(g)-fail, len(g)))
