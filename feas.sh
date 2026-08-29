set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== THE core test: is sum(targets) <= C ? ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  echo "--- $c ---"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {ce=$(h["C_effective_l"])+0; ts=$(h["target_rate_sum_bps"])+0; n++
     if(ts>ce+1e3){ over++; if(ts/ce>wr){wr=ts/ce; wts=ts; wce=ce} }
     if(ts>mx)mx=ts; sum+=ts; if(ce>0)lastce=ce}
    END{printf "  epochs=%d  C_eff=%.3f G  max_target_sum=%.3f G  mean=%.3f G\n", n, lastce/1e9, mx/1e9, sum/n/1e9
        if(over>0) printf "  INFEASIBLE in %d/%d epochs; worst ratio %.3fx (%.3f G vs %.3f G)\n", over, n, wr, wts/1e9, wce/1e9
        else       printf "  FEASIBLE in all %d epochs (target sum never exceeded C)\n", n}' ${c}_out/applied_rate_audit.csv
done
echo
echo "=== background rate recorded per epoch (this is R_old the formula uses) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {b=$(h["background_rate_bps"])+0; if(b>0){n++; s+=b; if(b>mx)mx=b; if(mn==0||b<mn)mn=b}}
    END{printf "R_old: mean=%.3f G  min=%.3f G  max=%.3f G  (n=%d)\n", s/n/1e9, mn/1e9, mx/1e9, n}' ${c}_out/applied_rate_audit.csv
done
echo
echo "=== implied eta_eff:  eta = 1 - oldShare/R_old, where oldShare ~ background target ==="
echo "    (theory for S3: R_old=8G -> eta_feasible = (6.4 - 2.0)/8.0 = 0.550)"
