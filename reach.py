C=10e9; H=175e-6; SOFT=524288.0; HARD=1048575.0; ONW=1048; N=64
print("=== can a boost alone reach YELLOW (soft=%.0f B = %.2f us)? ===" % (SOFT, SOFT*8/C*1e6))
q_obs = 56592.0   # measured peak at rho=0.90
print("  measured queue peak rho=0.90      : %8.0f B (%6.2f us)" % (q_obs, q_obs*8/C*1e6))
marg = N*ONW
print("  packetization margin (64 x 1048)  : %8.0f B (%6.2f us)" % (marg, marg*8/C*1e6))
for b in (0.30, 0.50, 1.0, 2.0):
    add = b*C*H/8.0
    tot = q_obs + add + marg
    print("  boost=%.2fC -> +%8.0f B ; Q_safe=%8.0f B (%6.2f us)  %s"
          % (b, add, tot, tot*8/C*1e6, "YELLOW" if tot>=SOFT else "still GREEN"))
print()
need = (SOFT - q_obs - marg)*8.0/H
print("  boost needed to just reach soft   : %.3f C  (%.2f Gbps)" % (need/C, need/1e9))
print("  ...but sumR = C + boost would be  : %.2f Gbps offered on a 10 G link" % ((C+need)/1e9))
print()
print("=== the real ceiling: what can senders actually emit? ===")
print("  64 flows x m_max_rate 10 G each = 640 G nominal, so pacing is the only limit.")
print("  But per-flow rate at rho=0.90 is 143.75 Mbps; a 0.3C boost spread over")
print("  64 flows adds %.2f Mbps/flow." % (0.30*C/N/1e6))
print()
print("  KEY POINT: the queue is drained at C=10G continuously.  A sustained")
print("  offered load of C+boost only accumulates while it persists; the")
print("  measured 45.27 us peak already includes the full 64-way sync burst.")
print("  To hold 419 us of queue the batch would have to offer >C for 419us+,")
print("  i.e. ~84 consecutive epochs of unconfirmed boost -- which the")
print("  single-outstanding-boost rule forbids by construction.")
