C = 10e9          # bit/s
RTT_US = 15.2     # simulator's own maxRtt for this topology
print('=== base RTT and queue-byte conversions (C = 10 Gbps) ===')
print('  base RTT = %.1f us   (simulator maxRtt=15200 ns; hop derivation gives 15.4 us)' % RTT_US)
print('  BDP      = %.0f B    (simulator reports maxBdp=19000)' % (C*RTT_US*1e-6/8))
print()
print('  queue at a given delay:  q_bytes = C * delay_s / 8')
for frac in (0.25, 0.50, 0.80, 1.00):
    d = RTT_US*frac
    print('    %.2f RTT = %6.2f us -> %7.0f B' % (frac, d, C*d*1e-6/8))
print()
print('=== the eight preflight cells use ===')
print('  target 0.25 RTT =  %.0f B ; 0.50 RTT = %.0f B ; 0.80 RTT = %.0f B'
      % (C*0.25*RTT_US*1e-6/8, C*0.50*RTT_US*1e-6/8, C*0.80*RTT_US*1e-6/8))
print('  hard limit 1.00 RTT = %.0f B  (all three new modes)' % (C*1.00*RTT_US*1e-6/8))
print()
print('=== context: existing thresholds, for comparison ===')
print('  ECN KMIN (switch marking)      = 400000 B = %.1f us of delay = %.1f RTT'
      % (400000*8/C*1e6, 400000*8/C*1e6/RTT_US))
print('  CBAP admission-budget qmin/qmax= 200000/400000 B')
print('  measured CBAP-SBA queue peak   =  ~56000 B = %.1f us = %.2f RTT'
      % (56000*8/C*1e6, 56000*8/C*1e6/RTT_US))
print()
print('  NOTE: q_hard at 1.00 RTT = 19000 B is BELOW the measured 56000 B peak.')
print('        The observed peak is a transient above the planned steady state;')
print('        this matters for choosing the horizon and is reported, not tuned away.')
