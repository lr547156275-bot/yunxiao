set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S3 incast FCT: feasibility build vs frozen baseline ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11; a[n]=$11}
    END{ asort_done=0
         # p99 via simple sort
         for(i=1;i<=n;i++) for(j=i+1;j<=n;j++) if(a[j]<a[i]){t=a[i];a[i]=a[j];a[j]=t}
         p99=a[int(n*0.99+0.999)]; if(p99=="")p99=a[n]
         printf "n=%d mean=%.3fms p99=%.3fms max=%.3fms\n", n, s/n*1000, p99*1000, a[n]*1000 }' ${c}_out/flow_summary.csv
done
echo
echo "=== S3 queue + ECN over the collective window (t >= 1.9s) ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR>1 && $1>=1.9 {n++; q+=$3; if($3>mx)mx=$3; e+=$6; if($3>400000)k++}
    END{printf "q_mean=%9.0f q_peak=%9.0f ecn=%-7d over_KMIN=%6.2f%%\n", q/n, mx, e, k/n*100}' ${c}_out/selected_link_timeseries.csv
done
echo
echo "=== background flow (id 0) delivered bytes ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR>1 && $6==65 {printf "acked=%.0f B (%.3f GB) completed=%s\n", $12, $12/1e9, $13}' ${c}_out/flow_summary.csv
done
echo
echo "=== PFC / drops / retx ==="
for c in f_cbapsba_s3_seed2 m_cbapsba_s3_seed2; do
  printf "  %-22s " "$c"
  awk -F, 'NR>1{p+=$8; d+=$9} END{printf "pfc_events=%d pause_ns=%d  ", p, d}' ${c}_out/selected_link_timeseries.csv
  awk -F, 'NR>1{r+=$15; e+=$16} END{printf "retx_bytes=%d retx_events=%d\n", r, e}' ${c}_out/flow_summary.csv
done
