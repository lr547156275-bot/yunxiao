C=10e9; H=175e-6
Qc=1132888.0; Qs=954578.0; drain=8151303275.0
diff=Qc-Qs
term=drain*H/8.0
print("=== item 1: verify the attribution ===")
print("  Q_current - Q_stop      = %.0f B" % diff)
print("  drain * H_guard / 8     = %.0f B" % term)
print("  difference              = %.0f B (%.4f%%)" % (abs(diff-term), 100*abs(diff-term)/term))
print("  -> %s" % ("CONFIRMED: the endpoint formula subtracted future drain from the CURRENT queue"
                   if abs(diff-term)<200 else "does NOT match"))
print()
print("=== item 5: is M_unc already inclusive of packetization? ===")
print("  M_unc = max(actual_peak - Q_stop) = 62,397 B")
print("  This is a TOTAL residual: it is measured as actual minus predicted, so")
print("  any packetization error already shows up inside it.  Adding M_pkt on")
print("  top would count the same bytes twice.")
m_unc=62397.0; m_pkt=67072.0
print("  M_safe = max(M_unc, M_pkt) = max(%.0f, %.0f) = %.0f B" % (m_unc,m_pkt,max(m_unc,m_pkt)))
m_safe=max(m_unc,m_pkt)
Q_ABS=1048575.0
m_act=0.30*C*H/8.0
q_red=Q_ABS-m_safe; q_high=q_red-m_act; q_low=0.5*Q_ABS
print()
print("  Q_abs  = %9.0f B = %7.2f us" % (Q_ABS, Q_ABS*8/C*1e6))
print("  Q_red  = %9.0f B = %7.2f us   (spec: 981,503 / 785.20)" % (q_red, q_red*8/C*1e6))
print("  M_act  = %9.0f B" % m_act)
print("  Q_high = %9.0f B = %7.2f us   (spec: 915,878 / 732.70)" % (q_high, q_high*8/C*1e6))
print("  Q_low  = %9.0f B = %7.2f us" % (q_low, q_low*8/C*1e6))
print("  match spec: Q_red %s  Q_high %s"
      % ("YES" if abs(q_red-981503)<2 else "NO", "YES" if abs(q_high-915878)<2 else "NO"))
print("  ordering: %s" % ("OK" if 0<q_low<q_high<q_red<Q_ABS else "VIOLATED"))
print()
print("=== item 3: what the max-prefix formula gives at that worst epoch ===")
print("  q0 = Q_current = %.0f B" % Qc)
print("  Any drain can only REDUCE q1/q2 below q0, so max-prefix returns q0.")
print("  Q_stop = %.0f B, not %.0f B.  Difference from the old value: %.0f B"
      % (Qc, Qs, Qc-Qs))
print("  This satisfies Q_stop >= Q_current BY CONSTRUCTION, not by clamping.")
