cd /work/simulation/experiment/scheme1_sba
for n in qc_s3_rho090 qc_s3_rho09875; do
  grep -q "^CBAP_QC_SAFETY_MARGIN_BYTES" ${n}.txt || echo "CBAP_QC_SAFETY_MARGIN_BYTES 67072" >> ${n}.txt
  printf "  %-18s M_safe=%s\n" "$n" "$(awk '/^CBAP_QC_SAFETY_MARGIN_BYTES/{print $2}' ${n}.txt)"
done
