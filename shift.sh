cd /work/simulation
echo "=== shift declaration / default ==="
grep -nE "\bshift\b" scratch/third.cc | grep -viE "a_shift\[j\]" | head -8
echo
echo "=== ConfigNPort called with what? ==="
grep -nE "ConfigNPort" scratch/third.cc
echo
python3 - <<'PY'
C=10e9; buffer_size=8*1024*1024; reserve=4*1024
# switch 84: ports 1..8 (dev0 = loopback). 4 x 1us (hosts), 4 x 2us (uplinks)
h1=int(10e9*1000/8/1e9*3)     # 1us delay
h2=int(10e9*2000/8/1e9*3)     # 2us delay
total_hdrm=4*h1+4*h2
total_rsrv=8*reserve
free=buffer_size-total_hdrm-total_rsrv
print("  headroom: 1us port=%d B, 2us port=%d B" % (h1,h2))
print("  total_hdrm=%d  total_rsrv=%d  buffer=%d" % (total_hdrm,total_rsrv,buffer_size))
print("  free (shared_used=0) = %d B" % free)
for shift in (2,3,4):
    t=free>>shift
    print("   shift=%d -> thresh=%d B = %.2f us of 10G" % (shift,t,t*8/C*1e6))
print()
print("  observed S3 egress queue peak = 56592 B = 45.27 us")
print("  -> the EGRESS queue peak is far below any of these INGRESS thresholds,")
print("     which is consistent with PFC=0 measured in every cell.")
PY
