set -u
cd /work/simulation
echo "=== where does ecnThresholdBytes come from? ==="
grep -rn "ecnThresholdBytes" src/point-to-point/model/rdma-hw.h scratch/third.cc | head -6 | sed 's/^/  /'
echo
echo "=== the cbap link file supplies it (col 5) ==="
cat experiment/scheme1_sba/s3_cbap_link.txt | sed 's/^/  /'
echo "  format: link_id node if rate_bps ECN_THRESHOLD ? ?"
echo
echo "=== so for the CBAP budget band: qEcn = 400000 ==="
python3 -c "
q=400000
print('  budgetQMin = 0.5 * %d = %d B' % (q, 0.5*q))
print('  budgetQMax = 1.0 * %d = %d B' % (q, 1.0*q))
print('  -> the admission budget starts decaying at 200 KB and floors at 400 KB')
"
echo
echo "=== and what metrics.py calls qmin/qmax ==="
grep -n "qmin_bytes\|qmax_bytes\|link_qmax" experiment/scheme1_sba/metrics.py | head -6 | sed 's/^/  /'
