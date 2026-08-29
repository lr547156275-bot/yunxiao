cd /work/simulation
echo "=== migration step params: configured values in the S3 core cell ==="
grep -nE "CBAP_MIGRATION_(RISE|DECAY|MAX_RTT|RELEASE)|BUDGET_Q" experiment/scheme1_sba/cr_s3_rho040.txt
echo
echo "=== their defaults / parse sites ==="
grep -nE "migrationRiseBase|migrationRiseSkew|migrationDecayBase" src/point-to-point/model/rdma-hw.h scratch/third.cc | head
echo
echo "=== ReplanCbapSbaMigrationTargets: does it SET rate or only target? (2225-2265) ==="
sed -n '2225,2262p' src/point-to-point/model/rdma-hw.cc
