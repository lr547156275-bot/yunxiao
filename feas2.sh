set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== when are these epochs? is any of them DURING the handover (t>=1.9s)? ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {e=$(h["epoch"])+0; if(mn==0||e<mn)mn=e; if(e>mx)mx=e}
    END{printf "epoch range %d..%d\n", mn, mx}' ${c}_out/applied_rate_audit.csv
done
echo
echo "=== is there a time column? show one row verbatim ==="
head -1 f_cbapsba_s3_seed2_out/applied_rate_audit.csv
sed -n '2p' f_cbapsba_s3_seed2_out/applied_rate_audit.csv
echo
echo "=== compare the two files byte-for-byte: identical? ==="
if cmp -s f_cbapsba_s3_seed2_out/applied_rate_audit.csv m_cbapsba_s3_seed2_out/applied_rate_audit.csv; then
  echo "  IDENTICAL -> this audit does not reflect the migration replan path at all"
else
  echo "  DIFFER -> lines differing: $(diff f_cbapsba_s3_seed2_out/applied_rate_audit.csv m_cbapsba_s3_seed2_out/applied_rate_audit.csv | grep -c '^[<>]')"
fi
echo
echo "=== sba_events.csv: does it record the migration replan (where my patch runs)? ==="
head -1 f_cbapsba_s3_seed2_out/sba_events.csv
echo "  rows f: $(awk 'END{print NR-1}' f_cbapsba_s3_seed2_out/sba_events.csv)  m: $(awk 'END{print NR-1}' m_cbapsba_s3_seed2_out/sba_events.csv)"
if cmp -s f_cbapsba_s3_seed2_out/sba_events.csv m_cbapsba_s3_seed2_out/sba_events.csv; then echo "  sba_events IDENTICAL"; else echo "  sba_events DIFFER: $(diff f_cbapsba_s3_seed2_out/sba_events.csv m_cbapsba_s3_seed2_out/sba_events.csv | grep -c '^[<>]') lines"; fi
