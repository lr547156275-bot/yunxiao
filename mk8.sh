set -u
cd /work/simulation/experiment/scheme1_sba
RTT_US=15.2
H_US=15.0            # epoch 5 + planning 5 + control 5, from the config
OVERSUB=0.20         # same order as the existing maxDrainRatio=0.20
DRAIN=0.20           # start from the established value, not tuned
MARGIN=0             # no PFC XOFF figure available; hard bound comes from delay
for tag in s3 s4; do
  # legacy: the frozen config verbatim
  n=qc_${tag}_legacy
  sed "s|m_cbapsba_${tag}_seed2_out/|${n}_out/|g" m_cbapsba_${tag}_seed2.txt > ${n}.txt
  mkdir -p ${n}_out
  for frac in 025 050 080; do
    case $frac in 025) f=0.25;; 050) f=0.50;; 080) f=0.80;; esac
    tgt=$(python3 -c "print('%.4f' % ($f*$RTT_US))")
    n=qc_${tag}_t${frac}
    sed "s|m_cbapsba_${tag}_seed2_out/|${n}_out/|g" m_cbapsba_${tag}_seed2.txt > ${n}.txt
    {
      echo "CBAP_DELAY_CREDIT_ENABLE 1"
      echo "CBAP_QUEUE_DELAY_TARGET_US $tgt"
      echo "CBAP_QUEUE_DELAY_HARD_LIMIT_US $RTT_US"
      echo "CBAP_CREDIT_HORIZON_US $H_US"
      echo "CBAP_MAX_OVERSUB_RATIO $OVERSUB"
      echo "CBAP_MAX_DRAIN_RATIO $DRAIN"
      echo "CBAP_QUEUE_SAFETY_MARGIN_BYTES $MARGIN"
      echo "CBAP_DELAY_CREDIT_FILE ${n}_out/delay_credit.csv"
    } >> ${n}.txt
    mkdir -p ${n}_out
  done
done
echo "=== 8 configs written ==="
ls qc_s[34]_*.txt | sed 's/^/  /'
echo "=== verify: legacy has no credit keys; new modes have all 8 ==="
for f in qc_s3_legacy.txt qc_s3_t050.txt; do
  printf "  %-20s credit keys=%s\n" "$f" "$(grep -c '^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_HORIZON\|^CBAP_MAX_OVERSUB\|^CBAP_MAX_DRAIN\|^CBAP_QUEUE_SAFETY' $f)"
done
echo "=== and that nothing else differs from the frozen config ==="
diff <(grep -v '^CBAP_DELAY_CREDIT\|^CBAP_QUEUE_DELAY\|^CBAP_CREDIT_HORIZON\|^CBAP_MAX_OVERSUB\|^CBAP_MAX_DRAIN\|^CBAP_QUEUE_SAFETY' qc_s3_t050.txt | sed 's|qc_s3_t050_out/|m_cbapsba_s3_seed2_out/|g') m_cbapsba_s3_seed2.txt && echo "  s3_t050: identical apart from the 8 new keys"
