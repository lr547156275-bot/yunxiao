import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
print("=== how many links does GetCbapSbaAvailableCapacity report? ===")
print("   (ProgressiveFill takes min over ALL links on the path)")
print("   s3_cbap_link.txt declares:")
for i,l in enumerate(open('s3_cbap_link.txt')):
    print('     %s' % l.rstrip())
print()
print("=== and the path each incast flow takes ===")
n=0
for l in open('s3_cbap_path.txt'):
    if n<3: print('     %s' % l.rstrip())
    n+=1
print('     ... %d lines total' % n)
print()
print("=== so ProgressiveFill only sees link 0 (84:1). Then the split is: ===")
for lab,eff in (('legacy',10.0e9),('credit',12.0e9)):
    nb = eff*0.5
    print('  %-7s newBatchResidual = %.3f G ; /64 = %.4f Mbps ; observed = %s'
          % (lab, nb/1e9, nb/64/1e6, '15.625' if lab=='legacy' else '31.250'))
print()
print("=== the discrepancy factor ===")
print("  legacy: predicted 78.125 vs observed 15.625 Mbps -> factor 5.000")
print("  credit: predicted 93.750 vs observed 31.250 Mbps -> factor 3.000")
print()
print("  5.0 and 3.0 are not constant, but note:")
print("    legacy observed 1.000 G = 10.0 G x 0.10")
print("    credit observed 2.000 G = 12.0 G x 0.1667")
print("  and 1.0 = 10.0/2 - 4.0 ; 2.0 = 12.0/2 - 4.0")
print("  => a CONSTANT 4.0 G is subtracted from the new-batch half in both cases.")
print("     4.0 G is exactly the background flow's applied reservation at that")
print("     moment (the audit showed background admit_rate = 10 G, app-capped to")
print("     8 G, and eta gives old_share 4.0 G in the credit run).")
