cd /work/simulation/src/point-to-point/model
echo "=== GetPfcThreshold + buffer setup ==="
sed -n '92,120p' switch-mmu.cc
echo
echo "=== how is total buffer / shared pool set? ==="
grep -nE "buffer_size|shared_bytes|total_hdrm|SetBufferSize|ConfigureBuffer" switch-mmu.cc | head -12
echo
echo "=== ecnThresholdBytes: what the CBAP controller uses (400000 from link file) ==="
grep -rn "ecnThresholdBytes" rdma-hw.cc | head -6
