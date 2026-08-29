set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== migration keys actually set in the frozen cell ==="
grep -E "^CBAP_MIGRATION|^CBAP_ETA" m_cbapsba_s3_seed2.txt | sed 's/^/  /'
echo "=== compiled defaults for migration params (rdma-hw.h) ==="
grep -n -A3 "migrationEnabled(false)" /work/simulation/src/point-to-point/model/rdma-hw.h | sed 's/^/  /'
echo "=== cbap link file format: link_id node if rate qmax ? ? ==="
head -1 s3_cbap_link.txt | sed 's/^/  count: /'
sed -n '2p' s3_cbap_link.txt | sed 's/^/  row: /'
grep -n "qmax\|Qmax" /work/simulation/scratch/third.cc | grep -i cbap | head -4 | sed 's/^/  /'
echo "=== budget fractions / drain ratio defaults ==="
grep -nE "budgetQLowFraction|budgetQHighFraction|maxDrainRatio|oldBatchWeight|newBatchWeight" /work/simulation/src/point-to-point/model/rdma-hw.h | head -8 | sed 's/^/  /'
