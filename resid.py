import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; H_NS=175000.0; EPOCH_NS=5000.0
Q_ABS=1048575.0
for cell in ('qc_s3_rho090','qc_s3_rho09875'):
    f=cell+'_out/qc_trace.csv'
    rows=list(csv.DictReader(open(f)))
    t=[float(r['time_ns']) for r in rows]
    q=[float(r['q_current']) for r in rows]
    qs=[float(r['q_stop']) for r in rows]
    n=len(rows)
    step=int(H_NS/EPOCH_NS)   # 35 epochs per guard window
    resid=[]
    worst=None
    for i in range(n-step):
        peak=max(q[i:i+step+1])
        r=peak-qs[i]
        resid.append(r)
        if worst is None or r>worst[0]:
            worst=(r,i,peak,qs[i],q[i])
    pos=[x for x in resid if x>0]
    pos.sort()
    print("=== %s ===" % cell)
    print("  epochs analysed        : %d" % len(resid))
    print("  residual > 0           : %d (%.1f%%)" % (len(pos),100.0*len(pos)/len(resid)))
    if pos:
        print("  residual mean/p95/p99/max: %.0f / %.0f / %.0f / %.0f B"
              % (sum(pos)/len(pos), pos[int(0.95*(len(pos)-1))],
                 pos[int(0.99*(len(pos)-1))], pos[-1]))
    print("  actual queue peak      : %.0f B (%.1f%% of Q_abs)"
          % (max(q), 100.0*max(q)/Q_ABS))
    print("  Q_stop peak            : %.0f B (%.1f%% of Q_abs)"
          % (max(qs), 100.0*max(qs)/Q_ABS))
    if worst:
        r,i,peak,qsi,qi=worst
        print("  WORST residual %.0f B at t=%.1f us:" % (r,t[i]/1e3))
        print("    Q_current=%.0f  Q_stop=%.0f  actual peak in next 175us=%.0f"
              % (qi,qsi,peak))
        rr=rows[i]
        print("    boost_cmd=%s boost_eff=%s drain=%s pending=%s zone=%s"
              % (rr['boost_commanded'],rr['boost_effective'],rr['drain'],
                 rr['pending_generation'],rr['zone']))
    print()
