set -u
L=/work/matrix_logs
D=/work/simulation/experiment/scheme1_sba
echo "=== is the S4 dcqcn cell actually complete and valid? ==="
grep -E "^(completed_incast|expected_incast|trace_complete|exit_code|stop_time|wall_seconds)" $L/m_dcqcn_s4_seed2.manifest | sed 's/^/  /'
echo
echo "=== trace really reaches 5.5s? ==="
awk -F, 'NR>1{t=$1} END{printf "  last_trace_t=%.4f  rows=%d\n", t, NR-1}' $D/m_dcqcn_s4_seed2_out/selected_link_timeseries.csv
echo "  pre-freeze rows for the same cell:"
ls -la $L/pre_freeze_run/../*/ >/dev/null 2>&1
echo
echo "=== compare results: now vs pre-freeze final_results ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11; a[n]=$11} END{
  for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)if(a[j]<a[i]){t=a[i];a[i]=a[j];a[j]=t}
  printf "  now: incast=%d/64 mean=%.3f ms p99=%.3f ms\n", n, s/n*1000, a[int(n*0.99+0.999)]*1000}' \
  $D/m_dcqcn_s4_seed2_out/flow_summary.csv
echo "  pre-freeze reference (final_results.csv): dcqcn s4 mean=1126.615 p99=1127.321 ms"
echo
echo "=== KEY: how many flows did the BACKGROUND deliver? (drives event count) ==="
awk -F, 'NR>1 && $6==65 {printf "  bg acked=%.0f B (%.3f GB) completed=%s fct=%s\n", $12, $12/1e9, $13, $11}' \
  $D/m_dcqcn_s4_seed2_out/flow_summary.csv
