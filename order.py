print("=== SOURCE-ORDER RESOLUTION (cbap-sba.cc AdmitBatch) ===")
print("  line 177  residual = availableCapacity")
print("  line 185  residual -= existing->second.appliedRateBps      <- old reservation FIRST")
print("  line 223  newBatchResidual = residual")
print("  line 225  share = newW/(oldW+newW) = 0.5")
print("  line 228  newBatchResidual *= share                        <- weight SECOND")
print("  line 231  grants = ProgressiveFill(ids, newBatchResidual)")
print()
print("  => the formula is  (C - old) * 0.5,  NOT  C*0.5 - old")
print("  => exactly ONE old subtraction and ONE weight application")
print()
print("=== does (C - old) * 0.5 reproduce the measured grants? ===")
for lab, eff, obs_sum in (('legacy', 10.0e9, 1.0e9), ('credit', 12.0e9, 2.0e9)):
    # solve for the old reservation that the data implies
    implied_old = eff - obs_sum/0.5
    print('  %-7s effective=%.1f G  observed grant sum=%.3f G' % (lab, eff/1e9, obs_sum/1e9))
    print('          (C-old)*0.5 = %.3f  =>  implied old reservation = %.3f G'
          % (obs_sum/1e9, implied_old/1e9))
print()
print("  legacy implies old = 8.0 G ; credit implies old = 8.0 G   <- CONSTANT")
print("  8.0 G is exactly APP_RATE_CAP_BPS for the background flow in S3.")
print()
print("=== so the closed arithmetic is ===")
for lab, eff in (('legacy',10.0e9),('credit',12.0e9)):
    old=8.0e9
    r1=eff-old
    r2=r1*0.5
    print('  %-7s: (%.1f - %.1f) = %.1f  x0.5 = %.3f G  /64 = %.4f Mbps'
          % (lab, eff/1e9, old/1e9, r1/1e9, r2/1e9, r2/64/1e6))
print()
print("  legacy 15.625 Mbps  <- matches measured admit_rate_bps exactly")
print("  credit 31.250 Mbps  <- matches measured admit_rate_bps exactly")
print()
print("=== CORRECTION to my previous report ===")
print("  I wrote 'residual -4.0 G then x0.5'. Both parts were wrong:")
print("   * the reservation is 8.0 G (the background app cap), not 4.0 G;")
print("   * I mislabelled the order as C*0.5-old in one place.")
print("  The 4.0 G figure came from eta_feasibility's old_share, which belongs to")
print("  the MIGRATION replan path, not to AdmitBatch. Two different allocators.")
print("  No duplicate weighting and no duplicate subtraction exist.")
