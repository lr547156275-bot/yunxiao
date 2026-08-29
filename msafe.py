import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9; Q_ABS=1048575.0; H_NS=175000.0; EPOCH_NS=5000.0
ONW=1048; N=64; MAXB=0.30*C; H=175e-6
print("=== M_safe from the measured residual (item 3) ===")
print("  The old residual was CORRUPTED by the illegal drain (Q_stop fell below")
print("  Q_current in 1.7% of epochs).  Those epochs must be excluded, since")
print("  the residual there measures the bug, not prediction uncertainty.")
allr=[]
for cell in ('qc_s3_rho090','qc_s3_rho09875'):
    rows=list(csv.DictReader(open(cell+'_out/qc_trace.csv')))
    q=[float(r['q_current']) for r in rows]
    qs=[float(r['q_stop']) for r in rows]
    dr=[float(r['drain']) for r in rows]
    step=int(H_NS/EPOCH_NS)
    kept=[]
    for i in range(len(rows)-step):
        if qs[i] < q[i]-1: continue          # invariant already violated
        if dr[i] > 0.35*C+1: continue        # illegal drain epoch
        r=max(q[i:i+step+1])-qs[i]
        if r>0: kept.append(r)
    kept.sort()
    allr.extend(kept)
    print("  %-16s clean residual>0: %d  p95=%.0f p99=%.0f max=%.0f B"
          % (cell,len(kept),
             kept[int(0.95*(len(kept)-1))] if kept else 0,
             kept[int(0.99*(len(kept)-1))] if kept else 0,
             kept[-1] if kept else 0))
allr.sort()
if allr:
    m_unc=allr[-1]
    print()
    print("  M_unc (max clean residual) = %.0f B (%.2f us)" % (m_unc, m_unc*8/C*1e6))
    print("  p95=%.0f p99=%.0f B" % (allr[int(0.95*(len(allr)-1))], allr[int(0.99*(len(allr)-1))]))
else:
    m_unc=0.0
    print("  no clean residual samples -- all drain epochs were illegal")
m_pkt=N*ONW
print("  M_pkt (N*on_wire)          = %.0f B (%.2f us)" % (m_pkt, m_pkt*8/C*1e6))
m_safe=m_unc+m_pkt
m_act=MAXB*H/8.0
print("  M_safe = M_unc + M_pkt     = %.0f B" % m_safe)
print("  M_act  = MAX_BOOST*H/8     = %.0f B" % m_act)
print()
q_red=Q_ABS-m_safe; q_high=q_red-m_act; q_low=0.5*Q_ABS
print("  Q_abs  = %9.0f B (%.2f us)" % (Q_ABS, Q_ABS*8/C*1e6))
print("  Q_red  = %9.0f B (%.2f us)" % (q_red, q_red*8/C*1e6))
print("  Q_high = %9.0f B (%.2f us)" % (q_high, q_high*8/C*1e6))
print("  Q_low  = %9.0f B (%.2f us)" % (q_low, q_low*8/C*1e6))
ok = 0 < q_low < q_high < q_red < Q_ABS
print("  ordering 0 < Q_low < Q_high < Q_red < Q_abs : %s" % ("OK" if ok else "VIOLATED"))
if not ok:
    print("  -> M_safe is too large for the band; report rather than truncate.")
