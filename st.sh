set -u
D=/work/simulation/experiment/scheme1_sba/g_cbapsba_s3_seed2_out
ps -o etime,time,pcpu,rss -p $(pgrep -f "third g_cbapsba_s3" | head -1) 2>/dev/null | tail -1 | sed 's/^/  cpu: /'
awk -F, 'NR>1{t=$1; e+=$6; if($3>mx)mx=$3} END{
  printf "  sim_t=%.4f / 3.0 s (%.1f%%)  rows=%d\n", t, t/3.0*100, NR-1
  printf "  ECN so far=%d   queue peak so far=%.0f B\n", e, mx
}' $D/selected_link_timeseries.csv 2>/dev/null || echo "  no trace yet"
