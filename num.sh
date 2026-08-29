cd /work/simulation/src/point-to-point/model
echo "=== existing pfcBound / safety margin computation (475-500) ==="
sed -n '475,500p' rdma-hw.cc
echo
echo "=== the derived delay budget numbers ==="
python3 - <<'PY'
C=10e9
qecn=400000          # s3_cbap_link.txt field: ecnThresholdBytes
msg=1048576          # 1 MiB
print("  tx_delay        = %.2f us  (1 MiB at 10G)" % (msg*8/C*1e6))
print("  q_ecn=400000 B  -> %.2f us of queue at 10G" % (qecn*8/C*1e6))
for m in (0, 19000, 38000):
    print("  pfc_safe(margin=%6d B) = %.2f us" % (m, (qecn-m)*8/C*1e6))
print("  1 RTT of queue at 10G (19000 B) = %.2f us" % (19000*8/C*1e6))
print("  observed peak queue in S3 = 56592 B = %.2f us" % (56592*8/C*1e6))
print()
print("  hard_delay = min(tx_delay, pfc_safe) ; soft = 0.5*hard")
hard=min(msg*8/C, (qecn-19000)*8/C)
print("  -> hard = %.2f us, soft = %.2f us" % (hard*1e6, 0.5*hard*1e6))
print("  horizon = 5.0 us (measured sample->delivery lag = one control epoch)")
print("  at C=10G, 5 us of oversub at rate (A-C) fills (A-C)*5e-6/8 bytes")
print("  e.g. A=1.5C -> %.0f B per epoch" % (0.5*C*5e-6/8))
PY
