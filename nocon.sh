cd /work/simulation/src/point-to-point/model
echo "=== does the C++ EVER confirm a pending command? ==="
grep -nE "qcPendingGeneration = 0|qcBoostEffectiveBps =" rdma-hw.cc
echo
echo "=== the reference python confirms via an explicit 'confirm' argument. ==="
echo "=== what plays that role in C++? search for the ETA comparison: ==="
grep -nE "qcPendingEtaNs" rdma-hw.cc
echo
echo "=== first rows of the qc trace: is boost_commanded even set? ==="
head -3 /work/simulation/experiment/scheme1_sba/qc_s3_rho090_out/qc_trace.csv
awk -F, 'NR>1 && $6>0 {print "  first boost_commanded>0 at row "NR": "$0; exit}' \
  /work/simulation/experiment/scheme1_sba/qc_s3_rho090_out/qc_trace.csv
echo "  rows with boost_commanded>0: $(awk -F, 'NR>1 && $6>0' /work/simulation/experiment/scheme1_sba/qc_s3_rho090_out/qc_trace.csv | wc -l)"
