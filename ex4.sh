cd /work/simulation/experiment/scheme1_sba
echo "=== (4) H_eff legs, measured ==="
echo "--- leg 1: queue_sample -> control sees it (port_summary) ==="
awk -F, 'NR>1 && NR<=6 {printf "  sample=%s delivery=%s  lag=%.1f us\n", $1, $2, ($2-$1)/1000}' au_s3_rho090_out/port_summary.csv
echo
echo "--- leg 2+3: rate command epoch -> observable rate change (rho=0.90 flow 1) ==="
awk -F, 'NR>1 && $2==1 && $1>=2.00000 && $1<=2.00030 {printf "  t=%.6f rate=%.4f\n", $1, $8/1e6}' au_s3_rho090_out/selected_flow_timeseries.csv | head -16
echo
echo "--- when does the queue first respond after release? (rho=0.90) ==="
awk -F, 'NR>1 && $1>=1.99999 && $1<=2.00012 {printf "  t=%.6f q=%d B util=%.4f tx_delta=%d\n", $1, $3, $4, $5}' au_s3_rho090_out/selected_link_timeseries.csv | head -14
echo
echo "=== first DATA at bottleneck: first nonzero tx after release 2.000005 ==="
for t in 055 09875; do
  n=au_s3_rho$t
  printf "  %-18s " $n
  awk -F, 'NR>1 && $1>2.000005 && $3>0 {printf "first q>0 at t=%.6f (%.1f us after release)\n", $1, ($1-2.000005)*1e6; exit}' ${n}_out/selected_link_timeseries.csv
done
