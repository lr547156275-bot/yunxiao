set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== per-flow admitted/target rates: does the floor still bind? ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  echo "--- $c ---"
  # rate_transition.csv records target changes; look at the new-batch flows
  head -1 ${c}_out/rate_transition.csv | tr ',' '\n' | nl | head -8
  break
done
echo
echo "=== distinct target rates armed for incast flows (from rate_transition) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {t=$(h["target_rate_bps"]); if(t!="" && t+0>0) c[t]++}
    END{n=0; for(k in c) n++; printf "distinct_targets=%d  ", n
        # show the smallest few
        m=1e18; for(k in c) if(k+0<m) m=k+0
        printf "min_target=%.4f Mbps\n", m/1e6}' ${c}_out/rate_transition.csv 2>/dev/null || echo "no rate_transition"
done
echo
echo "=== MIN_RATE = 100 Mbps. Is min_target at the floor (bound) or above (free)? ==="
echo
echo "=== applied_rate_audit: sum of applied rates at the handover epoch ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  echo "--- $c ---"
  head -1 ${c}_out/applied_rate_audit.csv | tr ',' '\n' | nl | head -10
  break
done
