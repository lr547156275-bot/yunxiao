C=10e9; N=64; Rmin=100e6
print("=== S3 (R_old_entry = 8.0 G) ===")
for name,Rold in (("S3",8.0e9),("S4",9.5e9)):
    rho_min=max(0.0,(N*Rmin-(C-Rold))/Rold)
    rho_max=min(1.0,1.0-Rmin/Rold)
    print("%s: R_old=%.2f G" % (name,Rold/1e9))
    print("   rho_min = (%.1f - %.1f)/%.1f = %.7f" % (N*Rmin/1e9,(C-Rold)/1e9,Rold/1e9,rho_min))
    print("   rho_max = 1 - %.1f/%.1f       = %.7f" % (Rmin/1e9,Rold/1e9,rho_max))
print()
print("spec claims for S4: rho_min=0.6210526  rho_max=0.9894737")
r_min_s4=(N*Rmin-(C-9.5e9))/9.5e9
r_max_s4=1-Rmin/9.5e9
print("computed         : rho_min=%.7f  rho_max=%.7f" % (r_min_s4,r_max_s4))
print("match: %s / %s" % (abs(r_min_s4-0.6210526)<1e-7, abs(r_max_s4-0.9894737)<1e-7))
print()
print("=== S4 per-flow at the S3 test points, and at S4's own bounds ===")
for r in (0.6210526,0.75,0.90,0.9894737):
    old=(1-r)*9.5e9; new=C-old
    print("  rho=%.7f  R_old=%.4f G  R_new=%.4f G  per-flow=%.4f Mbps  old>=Rmin=%s"
          % (r,old/1e9,new/1e9,new/N/1e6,old>=Rmin-1))
print()
print("  NOTE S3 test point 0.55 is BELOW S4's rho_min=0.6210526 -> infeasible in S4")
print("  NOTE the S4 cell already run last round used rho=0.40, also below rho_min;")
print("       its eta_feasible=0.6211 clamped it, which is exactly rho_min.")
