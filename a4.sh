set -u
cd /work/simulation/src/point-to-point/model
echo "=== Q4: where does a CNP arrive, and is it gated for CBAP flows? ==="
grep -n "cnp\|Cnp\|CNP" rdma-hw.cc | grep -iE "handle|recv|arriv" | head -6 | sed 's/^/  /'
echo
echo "=== is the DCQCN rate-decrease path skipped while a CBAP flow is in SBA phase? ==="
grep -n "handedOff\|sbaEnabled\|cbap.phase" rdma-hw.cc | grep -iE "if.*!|return|skip" | head -8 | sed 's/^/  /'
