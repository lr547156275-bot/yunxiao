cd /work/simulation
echo "=== pfc_a_shift setup: exact value for the bottleneck (3830-3850) ==="
sed -n '3830,3850p' scratch/third.cc
echo
echo "=== total_rsrv / total_hdrm computation ==="
sed -n '120,140p' src/point-to-point/model/switch-mmu.cc
echo
echo "=== is there any accessor to read ingress_bytes / shared_used from outside? ==="
grep -nE "ingress_bytes|shared_used_bytes|total_hdrm|total_rsrv|GetPfcThreshold|GetSharedUsed|GetPfcOccupancy" src/point-to-point/model/switch-mmu.h
