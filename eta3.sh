set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== handoff_rate per incast flow (the per-flow target after the split) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {r=$(h["handoff_rate"])+0; if(r>0){n++; s+=r; if(mn==0||r<mn)mn=r; if(r>mx)mx=r}}
    END{if(n==0){print "no handoff_rate rows"; exit}
        printf "n=%d  mean=%.3f Mbps  min=%.3f  max=%.3f\n", n, s/n/1e6, mn/1e6, mx/1e6}' ${c}_out/sba_events.csv
done
echo
echo "=== grant_rate (what the planner granted the new batch) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
    {r=$(h["grant_rate"])+0; if(r>0){n++; s+=r; if(mn==0||r<mn)mn=r; if(r>mx)mx=r}}
    END{printf "n=%d  mean=%.4f Mbps  min=%.4f  max=%.4f\n", n, s/n/1e6, mn/1e6, mx/1e6}' ${c}_out/sba_events.csv
done
echo
echo "=== the actual rate the 64 incast flows converge to (from flow goodput) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$14} END{printf "mean per-flow goodput=%.3f Mbps  aggregate=%.3f Gbps\n", s/n/1e6, s/1e9}' ${c}_out/flow_summary.csv
done
echo
echo "=== IMPLIED eta_eff from the aggregate split during the collective ==="
echo "    incast aggregate + background share should be <= 10 G"
