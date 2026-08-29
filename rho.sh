cd /work/simulation
echo "=== (7) qLow/qHigh: do they come from ECN KMIN/KMAX? ==="
grep -nE "budgetQLowFraction|budgetQHighFraction" src/point-to-point/model/rdma-hw.cc | head
echo "  --- defaults:"
grep -nE "budgetQLowFraction|budgetQHighFraction" src/point-to-point/model/rdma-hw.h
echo "  --- config keys:"
grep -nE "BUDGET_Q_LOW|BUDGET_Q_HIGH|budget_q_low|budget_q_high" scratch/third.cc | head -4
echo "  --- ecnThresholdBytes source in the link file:"
echo "     s3_cbap_link.txt = '0 84 1 10000000000 400000 0 1'  -> field5=ecnThresholdBytes=400000"
grep -nE "ecnThresholdBytes" src/point-to-point/model/rdma-hw.h | head -3
echo
python3 - <<'PY'
C=10e9; N=64; Rmin=100e6; Rold=8e9
print("=== (2) rho feasible interval, S3 ===")
rho_min=max(0.0,(N*Rmin-(C-Rold))/Rold)
# rho_max = 1 - sum_old_min_rate/R_old_entry ; the old side is ONE background flow
sum_old_min=Rmin
rho_max=min(1.0,1.0-sum_old_min/Rold)
print("  rho_min = max(0,(N*Rmin-(C-Rold))/Rold) = (64*0.1G-2.0G)/8.0G = %.6f" % rho_min)
print("  rho_max = 1 - sum_old_min/Rold = 1 - 0.1/8.0        = %.6f" % rho_max)
print("  -> spec expects 0.55 and 0.9875 :  %s / %s"
      % ("MATCH" if abs(rho_min-0.55)<1e-9 else "MISMATCH",
         "MATCH" if abs(rho_max-0.9875)<1e-9 else "MISMATCH"))
print()
print("=== per-flow base rate at each test rho ===")
for r in (0.55,0.75,0.90,0.9875):
    old=(1-r)*Rold; new=C-old
    print("  rho=%.4f  R_old_base=%.4f G  R_new_base=%.4f G  per-flow=%.4f Mbps  old>=Rmin? %s"
          % (r, old/1e9, new/1e9, new/N/1e6, "yes" if old>=Rmin-1 else "NO"))
print()
print("=== (6) drain headroom ===")
floor_inc=N*Rmin; floor_bg=Rmin
print("  incast floor = 64*100M = %.1f G" % (floor_inc/1e9))
print("  background floor       = %.1f G" % (floor_bg/1e9))
print("  total floor            = %.1f G   (spec expects 6.5 G: %s)"
      % ((floor_inc+floor_bg)/1e9, "MATCH" if abs(floor_inc+floor_bg-6.5e9)<1 else "MISMATCH"))
print("  drain headroom = C - total floor = %.1f G  (spec expects 3.5 G: %s)"
      % ((C-floor_inc-floor_bg)/1e9, "MATCH" if abs(C-floor_inc-floor_bg-3.5e9)<1 else "MISMATCH"))
print("  sum(min rates) < C ?  %s" % (floor_inc+floor_bg < C))
PY
