C=10e9; H=175e-6; SOFT=524288.0; HARD=1048575.0
Q0=56592.0; BOOST=0.30*C
print("=== item 7 reachability check: PERSISTENT absolute boost ===")
print("  Q_current            = %8.0f B (%6.2f us)" % (Q0, Q0*8/C*1e6))
print("  Q_soft               = %8.0f B (%6.2f us)" % (SOFT, SOFT*8/C*1e6))
print("  boost_effective      = %.2f C = %.1f Gbps excess" % (BOOST/C, BOOST/1e9))
fill_Bps = BOOST/8.0                     # bytes per second of accumulation
t_soft = (SOFT-Q0)/fill_Bps
print()
print("  fill rate            = %.0f B/s = %.3f B/us" % (fill_Bps, fill_Bps/1e6))
print("  time to reach soft   = (%.0f - %.0f)/%.0f = %.6f s = %.3f ms"
      % (SOFT, Q0, fill_Bps, t_soft, t_soft*1e3))
print("    spec says ~1.247 ms -> %s" % ("MATCH" if abs(t_soft*1e3-1.247)<0.01 else "MISMATCH"))
t_brake = t_soft - H
print("  minus %.0f us brake latency = %.3f ms  (when YELLOW must engage)" % (H*1e6, t_brake*1e3))
print("    spec says ~1.072 ms -> %s" % ("MATCH" if abs(t_brake*1e3-1.072)<0.01 else "MISMATCH"))
print()
print("=== is there enough time in the batch? ===")
bct=87.9173e-3
print("  S3 rho=0.90 BCT = %.3f ms ; time-to-YELLOW %.3f ms is %.2f%% of it"
      % (bct*1e3, t_brake*1e3, 100*t_brake/bct))
print("  -> ample: YELLOW should engage ~1.07 ms into an ~88 ms collective.")
print()
print("=== Q_stop: net backlog until the brake can first take effect ===")
print("  Q_stop = Q_current + (sumR_effective - C)*H_guard/8  [+ pending delta]")
for q in (Q0, 200000.0, 400000.0, SOFT-70000, SOFT):
    qs = q + BOOST*H/8.0
    zone = "RED" if qs>=HARD else ("YELLOW" if qs>=SOFT else "GREEN")
    print("   Q=%8.0f B -> Q_stop=%8.0f B (%7.2f us)  %s" % (q, qs, qs*8/C*1e6, zone))
print()
print("  YELLOW triggers when Q_stop >= soft, i.e. Q >= %.0f B (%.2f us)"
      % (SOFT-BOOST*H/8.0, (SOFT-BOOST*H/8.0)*8/C*1e6))
print("  reached at t = %.3f ms of sustained boost -- matches the brake-latency")
print("  figure above, so the soft zone is entered EARLY ENOUGH to stop before hard.")
