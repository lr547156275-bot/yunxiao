print("=== LOCATING THE 0.6 Gbps ===")
print()
print("Chain, cbap-sba.cc AdmitBatch():")
print("  1. residual[link] = availableCapacity[link]                  (from GetCbapSbaAvailableCapacity)")
print("  2. residual -= sum(appliedRateBps of existing/old flows)      (line ~184)")
print("  3. newBatchResidual = floor(residual * share),  share = newW/(oldW+newW) = 0.5")
print("  4. grants = ProgressiveFill(ids, newBatchResidual)")
print()
C=10e9
for lab, avail in (('legacy', 9.5e9), ('credit', 11.5e9)):
    # available = effectiveCapacityBps = total_budget - background reservation
    bg = 8.0e9   # background app cap reservation seen in the audit
    print('=== %s ===' % lab)
    print('  available (effectiveCapacityBps)      = %.3f G' % (avail/1e9))
    resid = avail - 0.0   # no other old SBA flow is applied yet at admission
    print('  residual after old-flow subtraction   = %.3f G' % (resid/1e9))
    newres = resid * 0.5
    print('  x share 0.5 (oldW=newW=1.0)           = %.3f G   <-- HERE' % (newres/1e9))
    print('  ProgressiveFill over 64 flows         = %.6f Mbps/flow' % (newres/64/1e6))
    print()
print("=== reconciliation ===")
print("  legacy: 9.5 G  -> x0.5 = 4.75 G ... but observed admit sum = 1.000 G")
print("  credit: 11.5 G -> x0.5 = 5.75 G ... but observed admit sum = 2.000 G")
print()
print("  So a further constraint cuts 4.75 -> 1.0 and 5.75 -> 2.0.")
print("  Ratio: legacy 1.000/4.750 = %.4f ; credit 2.000/5.750 = %.4f" % (1.0/4.75, 2.0/5.75))
print("  Not a common factor, so it is NOT a second proportional scaling.")
print()
print("  Observed per-flow: legacy 15.625 Mbps, credit 31.250 Mbps")
print("  Note 15.625 Mbps = 1 Gbps / 64, and 31.25 = 2 Gbps / 64.")
print("  Also 15.625 Mbps = 10 Gbps / 640 and is EXACTLY 1/2^6 of 1 Gbps.")
print("  => strongly suggests ProgressiveFill is demand-limited, not capacity-limited:")
print("     each flow asks for a share bounded by something other than the residual.")
