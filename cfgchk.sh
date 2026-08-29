set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== what the cell config actually contains ==="
grep -E "^CBAP_DELAY_CREDIT|^CBAP_QUEUE_DELAY|^CBAP_CREDIT_HORIZON|^CBAP_MAX_OVERSUB|^CBAP_MAX_DRAIN|^CBAP_QUEUE_SAFETY" fx_s3_t025.txt | sed 's/^/  /'
echo
echo "=== does third.cc parse CBAP_MAX_DRAIN_RATIO into the right variable? ==="
grep -n "CBAP_MAX_DRAIN_RATIO" /work/simulation/scratch/third.cc | sed 's/^/  /'
grep -n "creditMaxDrainRatio = \|maxDrainRatio = " /work/simulation/scratch/third.cc | sed 's/^/  /'
echo
echo "=== is CBAP_MAX_DRAIN_RATIO already used by the OLD decay parameter? ==="
grep -n "cbap_max_drain_ratio\|cbap_credit_max_drain_ratio" /work/simulation/scratch/third.cc | sed 's/^/  /'
