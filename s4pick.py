C=10e9; N=64; Rmin=100e6; Rold=9.5e9
rmin=(N*Rmin-(C-Rold))/Rold
rmax=1-Rmin/Rold
print("S4 interval: [%.7f, %.7f]" % (rmin,rmax))
print("S3 test points and their S4 validity:")
for r in (0.55,0.75,0.90,0.9875):
    ok = rmin <= r <= rmax
    print("  rho=%-7s %s" % (r, "VALID" if ok else "INFEASIBLE (below rho_min)"))
print()
print("Choosing 0.90 for S4: valid, and directly comparable to the S3 0.90 cell.")
old=(1-0.90)*Rold; new=C-old
print("  S4 rho=0.90 -> R_old=%.4f G  R_new=%.4f G  per-flow=%.4f Mbps"
      % (old/1e9,new/1e9,new/N/1e6))
