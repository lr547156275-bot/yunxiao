import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
print("=== the floor is 6.3 G, not 6.5 G ===")
print("  C - 0.3700C = %.3f G" % ((C-0.37*C)/1e9))
print("  6.3 G / 100 Mbps = %.0f flows" % (6.3e9/100e6))
print("  expected: 64 incast + 1 background = 65 flows -> 6.5 G")
print("  actual  : 63 flows -> the protected set is missing 2")
print()
print("  My loop inserts flows from s_cbapFlows that are active, not finished,")
print("  have qp+hw, AND whose path contains linkId. Then:")
print("    floorBps = sum(minRate over that set)")
print("  It does NOT add the background flow's minimum rate separately -- the")
print("  background is in s_cbapFlows as batch 0, so it SHOULD be counted...")
print("  unless it is excluded by one of the predicates.")
print()
print("=== but the deeper problem: Q_stop < Q_current 8672 times ===")
rows=list(csv.DictReader(open('qc_s3_rho090_out/qc_trace.csv')))
bad=[r for r in rows if float(r['q_stop'])<float(r['q_current'])-1]
print("  violations: %d" % len(bad))
if bad:
    b=bad[0]
    print("  first violation:")
    for k in ('time_ns','q_current','q_stop','q_safe','boost_effective','drain','pending_generation','zone'):
        print("    %-20s %s" % (k, b[k]))
    q=float(b['q_current']); qs=float(b['q_stop']); d=float(b['drain'])
    print("    Q_current - Q_stop = %.0f B" % (q-qs))
    print("    drain*H/8          = %.0f B" % (d*175e-6/8))
    print()
    print("  THE TRACE IS THE PROBLEM, NOT THE CONTROLLER:")
    print("  SampleCbapQcTrace recomputes q_stop itself with the OLD endpoint")
    print("  formula (qStop = queueBytes + excess*hGuard/8), independently of")
    print("  what QueueControllerEpoch computed.  So the trace still shows the")
    print("  old broken value while the controller may be using the new one.")
