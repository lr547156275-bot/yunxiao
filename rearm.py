C=10e9; H=175e-6; SOFT=524288.0; HARD=1048575.0
N=64; ONW=1048; MINR=100e6
MAXB=0.30*C
FLOOR=N*MINR+MINR
MAXD=C-FLOOR
print("=== MAX_DRAIN from the existing floor (no new parameter) ===")
print("  total floor = 64*100M + 100M = %.1f G" % (FLOOR/1e9))
print("  MAX_DRAIN   = C - floor      = %.1f G = %.3f C" % (MAXD/1e9, MAXD/C))
print()
print("=== rearm margin derived from packetization + actuation uncertainty ===")
print("  Both terms already exist; nothing new is introduced.")
pk = N*ONW
print("  packetization  = N * on_wire      = %d * %d = %7.0f B (%.2f us)" % (N,ONW,pk,pk*8/C*1e6))
act = MAXB*H/8.0
print("  actuation      = MAX_BOOST*H/8    = %7.0f B (%.2f us)" % (act, act*8/C*1e6))
rearm_margin = pk + act
print("  rearm_margin   = sum             = %7.0f B (%.2f us)" % (rearm_margin, rearm_margin*8/C*1e6))
rearm = SOFT - rearm_margin
print("  rearm line     = Q_soft - margin = %7.0f B (%.2f us)" % (rearm, rearm*8/C*1e6))
print("  -> a positive boost may only resume once Q_stop < %.0f B" % rearm)
print("     i.e. far enough below soft that one full boost step plus one")
print("     synchronous burst cannot immediately re-cross soft.")
print()
print("=== the signed law: verify it is continuous and monotone ===")
def u(qstop):
    p=max(0.0,min(1.0,(qstop-SOFT)/(HARD-SOFT)))
    return MAXB*(1-p)-MAXD*p, p
print("   Q_stop        p       u          boost      drain")
for q in (SOFT, SOFT+0.1*(HARD-SOFT), SOFT+0.25*(HARD-SOFT),
          SOFT+0.5*(HARD-SOFT), SOFT+0.75*(HARD-SOFT), SOFT+0.9*(HARD-SOFT), HARD):
    val,p=u(q)
    print("  %9.0f  %.4f  %+8.4fC  %8.4fC  %8.4fC"
          % (q,p,val/C,max(val,0)/C,max(-val,0)/C))
print()
zero_p = MAXB/(MAXB+MAXD)
q_zero = SOFT + zero_p*(HARD-SOFT)
print("  u crosses zero at p = MAX_BOOST/(MAX_BOOST+MAX_DRAIN) = %.4f" % zero_p)
print("    -> Q_stop = %.0f B (%.2f us), i.e. %.1f%% into the YELLOW band"
      % (q_zero, q_zero*8/C*1e6, 100*zero_p))
print("  So drain begins BEFORE hard, continuously -- no fixed point at sumR==C")
print("  because u is strictly decreasing in Q_stop across the whole band.")
print()
print("=== does this remove the old fixed point? ===")
print("  Old: YELLOW floor was boost=0 -> sumR=C -> dQ/dt=0 -> parked at 99.6%% hard.")
print("  New: at that same queue, p=%.4f -> u=%+.4fC -> drain=%.4fC -> sumR=%.3f G < C"
      % (u(1044749.0)[1], u(1044749.0)[0]/C, max(-u(1044749.0)[0],0)/C,
         (C+u(1044749.0)[0])/1e9))
print("  -> the queue now falls from there.  No new threshold was added.")
