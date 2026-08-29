import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
for cell in ('qc_s3_rho090',):
    rows=list(csv.DictReader(open(cell+'_out/qc_trace.csv')))
    dr=[float(r['drain']) for r in rows if float(r['drain'])>0]
    print("=== drain values actually commanded (%s) ===" % cell)
    print("  epochs with drain>0 : %d" % len(dr))
    print("  drain min/max       : %.4f C / %.4f C" % (min(dr)/C, max(dr)/C))
    print("  LEGITIMATE MAX_DRAIN: 0.3500 C (= C - 6.5G floor)")
    over=[d for d in dr if d>0.35*C+1]
    print("  epochs exceeding it : %d (%.1f%%)" % (len(over),100.0*len(over)/len(dr)))
    print()
    print("  -> drain reaches %.2f C = %.2f Gbps, which is %.1fx the legal bound."
          % (max(dr)/C, max(dr)/1e9, max(dr)/(0.35*C)))
    print()
    print("=== how many rows violate Q_stop >= Q_current? ===")
    v=[r for r in rows if float(r['q_stop'])<float(r['q_current'])-1]
    print("  violations: %d of %d (%.1f%%)" % (len(v),len(rows),100.0*len(v)/len(rows)))
    print()
    print("=== and sumR_effective: does it go below the 6.5 G floor? ===")
    s=[float(r['sumR_effective']) for r in rows]
    print("  sumR min = %.3f G  (floor is 6.5 G)" % (min(s)/1e9))
    below=[x for x in s if x<6.5e9-1]
    print("  epochs below floor: %d (%.1f%%)" % (len(below),100.0*len(below)/len(s)))
    print()
    print("=== root cause chain ===")
    print("  1. drain is computed as (qStop - softBytes)*8/hGuard with a cap of")
    print("     maxDrain, but maxDrain uses activeSenders which can be 0 or 1")
    print("     in the tail -> floorBps collapses -> maxDrain approaches C.")
    print("  2. With drain up to 8.15 G, Q_stop = Q + (boost-drain)*H/8 goes")
    print("     NEGATIVE-ward, so Q_stop < Q_current and the controller believes")
    print("     the queue is about to empty when it is actually at 1.13 MB.")
    print("  3. Never entering RED (needs Q_safe>=hard) it keeps holding.")
