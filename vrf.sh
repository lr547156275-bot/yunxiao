cd /work/simulation
echo "=== the sampler fprintf format string (check the trailing newline escape) ==="
grep -n -A4 'fprintf(cbap_pfc_audit_csv,$' scratch/third.cc | head -24
echo
echo "=== call site ==="
grep -n "SampleCbapPfcAudit" scratch/third.cc
echo
echo "=== switch-mmu.h included? ==="
grep -nE "#include.*switch-mmu|#include.*switch-node" scratch/third.cc | head
