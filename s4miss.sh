set -u
D=/work/simulation/experiment/scheme1_sba
echo "=== does S4 declare the flow-timeseries output file? ==="
grep -nE "FLOW_TIMESERIES|SELECTED_FLOW|ROUND_TRACE" $D/m_cbapsba_s4_seed2.txt | sed 's/^/  s4: /'
echo "--- compare with s3 (which HAS the file) ---"
grep -nE "FLOW_TIMESERIES|SELECTED_FLOW|ROUND_TRACE" $D/m_cbapsba_s3_seed2.txt | sed 's/^/  s3: /'
echo
echo "=== what files DID s4 dcqcn produce? ==="
ls $D/m_dcqcn_s4_seed2_out/ | sed 's/^/  /'
echo
echo "=== and s3 dcqcn for comparison ==="
ls $D/m_dcqcn_s3_seed2_out/ | sed 's/^/  /'
