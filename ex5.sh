cd /work/simulation/experiment/scheme1_sba
echo "=== structural first-burst / in-flight bytes at the bottleneck ==="
echo "  64 flows x 1 wire packet (1064 B cfg / 1048 B observed) = 64*1048 = 67072 B = 53.66 us"
echo "  measured first queue jump (rho=0.90): 33536 B = 32 x 1048"
awk -F, 'NR>1 && $1>=2.000015 && $1<=2.000035 {printf "  t=%.6f q=%d B = %.1f packets of 1048\n", $1, $3, $3/1048}' au_s3_rho090_out/selected_link_timeseries.csv
echo
echo "=== H_eff summary per rho: release -> first q>0, and -> first rate change ==="
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  q=$(awk -F, 'NR>1 && $1>2.000005 && $3>0 {printf "%.6f", $1; exit}' ${n}_out/selected_link_timeseries.csv)
  r0=$(awk -F, 'NR>1 && $2==1 && $1>=2.0 {print $8; exit}' ${n}_out/selected_flow_timeseries.csv)
  rc=$(awk -F, -v r0="$r0" 'NR>1 && $2==1 && $1>2.000005 && $8!=r0 {printf "%.6f", $1; exit}' ${n}_out/selected_flow_timeseries.csv)
  printf "  rho=%-7s first_q>0=%s (%.1f us)   first_rate_change=%s (%s us)\n" "$t" "$q" "$(python3 -c "print(($q-2.000005)*1e6)")" "${rc:-none}" "$([ -n "$rc" ] && python3 -c "print('%.1f'%(($rc-2.000005)*1e6))" || echo NA)"
done
echo
echo "=== outcome metrics: 4 rho + HPCC ==="
printf "  %-14s %-10s %-10s %-10s %-10s %-8s %-8s %s\n" cell BCT_ms FCTmean FCTp99 qpeak_B qdelay_us PFC retx
for n in au_s3_rho055 au_s3_rho075 au_s3_rho090 au_s3_rho09875 au_s3_hpcc; do
  read bct fm fp <<< $(awk -F, 'NR>1 && $6!=65 && $13==1 {n++; if(n==1||$9<mn)mn=$9; if(n==1||$10>mx)mx=$10; s+=$11; a[n]=$11}
    END{asort(a); printf "%.4f %.4f %.4f", (mx-mn)*1e3, s/n*1e3, a[int(0.99*(n-1))+1]*1e3}' ${n}_out/flow_summary.csv 2>/dev/null || echo "0 0 0")
  read qp pf <<< $(awk -F, 'NR>1{if($3>q)q=$3; p+=$9} END{printf "%d %d", q, p}' ${n}_out/selected_link_timeseries.csv)
  rx=$(awk -F, 'NR>1{s+=$15} END{print s+0}' ${n}_out/flow_summary.csv)
  printf "  %-14s %-10s %-10s %-10s %-10s %-8.2f %-8s %s\n" "${n#au_s3_}" "$bct" "$fm" "$fp" "$qp" "$(python3 -c "print($qp*8/10e9*1e6)")" "$pf" "$rx"
done
