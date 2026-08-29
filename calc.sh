cd /work/simulation/experiment/scheme1_sba
echo "=== topology: bottleneck switch 84, its port count and link rates/delays ==="
f=$(grep -h "^TOPOLOGY_FILE" cr_s3_rho040.txt | awk '{print $2}'); echo "  $f"
head -1 "$f"
echo "  lines mentioning node 84:"; awk 'NR>2 && ($1==84||$2==84)' "$f" | head -3
echo "  count of links at 84: $(awk 'NR>2 && ($1==84||$2==84)' "$f" | wc -l)"
echo
echo "=== BUFFER_SIZE from config ==="
grep -hE "^BUFFER_SIZE" cr_s3_rho040.txt
echo
python3 - <<'PY'
C=10e9
buffer_size=8*1024*1024        # BUFFER_SIZE 8 (MB) from config
reserve=4*1024
n_port=85                      # to be confirmed from topology
# headroom = rate*delay/8/1e9*3
rate=10e9; delay_ns=1000       # 1us link delay typical; confirm
hdrm=int(rate*delay_ns/8/1e9*3)
print("  per-port headroom = %d B  (rate*delay/8/1e9*3, delay=%dns)" % (hdrm, delay_ns))
for npt in (64, 85):
    th=hdrm*npt; tr=reserve*npt
    for shift in (3,):
        free=buffer_size-th-tr
        print("  n_port=%3d: total_hdrm=%d total_rsrv=%d  free=%d  thresh(shared=0,shift=%d)=%d B = %.2f us"
              % (npt, th, tr, free, shift, free>>shift, (free>>shift)*8/C*1e6))
print()
print("  NOTE: threshold SHRINKS as shared_used_bytes grows:")
free0=buffer_size-hdrm*64-reserve*64
for su in (0, 100000, 500000, 1000000, 2000000):
    print("    shared_used=%7d B -> thresh=%7d B = %6.2f us" % (su, (free0-su)>>3, ((free0-su)>>3)*8/C*1e6))
PY
