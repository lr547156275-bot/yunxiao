set -u
cd /work/simulation/experiment/scheme1_sba
mk() {  # $1=name  $2=core_enable  $3=rho
  local n=$1
  sed "s|m_cbapsba_s3_seed2_out/|${n}_out/|g" m_cbapsba_s3_seed2.txt \
    | grep -v "^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_\|^CBAP_MAX_OVERSUB\|^CBAP_QUEUE_SAFETY" > ${n}.txt
  {
    echo "CBAP_CORE_INITIAL_RELEASE $2"
    echo "CBAP_INITIAL_RELEASE_RATIO $3"
    echo "CBAP_DELAY_CREDIT_ENABLE 0"
    echo "CBAP_ETA_FEASIBILITY_TRACE 1"
    echo "CBAP_ETA_FEASIBILITY_FILE ${n}_out/eta_feasibility.csv"
  } >> ${n}.txt
  mkdir -p ${n}_out
  printf "  %-22s core=%s rho=%s\n" "${n}.txt" "$2" "$3"
}
mk cr_s3_legacy5050 0 0.0
mk cr_s3_rho000     1 0.0
mk cr_s3_rho040     1 0.4
mk cr_s3_rho060     1 0.6
echo "=== confirm credit/lease OFF and no 50:50 keys leaked in ==="
for f in cr_s3_legacy5050.txt cr_s3_rho040.txt; do
  printf "  %-22s credit=%s core=%s rho=%s\n" "$f" \
    "$(awk '/^CBAP_DELAY_CREDIT_ENABLE/{print $2}' $f)" \
    "$(awk '/^CBAP_CORE_INITIAL_RELEASE/{print $2}' $f)" \
    "$(awk '/^CBAP_INITIAL_RELEASE_RATIO/{print $2}' $f)"
done
echo "=== everything else identical to the frozen S3 config? ==="
diff <(grep -v "^CBAP_CORE_INITIAL_RELEASE\|^CBAP_INITIAL_RELEASE_RATIO\|^CBAP_DELAY_CREDIT_ENABLE\|^CBAP_ETA_FEASIBILITY" cr_s3_rho040.txt | sed 's|cr_s3_rho040_out/|m_cbapsba_s3_seed2_out/|g') \
     <(grep -v "^CBAP_ETA_FEASIBILITY" m_cbapsba_s3_seed2.txt) \
  && echo "  identical apart from the new keys"
