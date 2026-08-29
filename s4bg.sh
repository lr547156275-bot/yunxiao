set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S4 background flow: the scenario where it COMPLETES (4GB in 5.5s) ==="
echo "    so bg_fct and bg_slowdown are defined here, unlike S1/S2/S3/S6"
for a in dcqcn dctcp timely hpcc; do
  printf "  %-8s " "$a"
  awk -F, 'NR>1 && $6==65 {printf "acked=%.3f GB  completed=%s  fct=%.4f s  goodput=%.3f Gbps\n", $12/1e9, $13, $11, $14/1e9}' m_${a}_s4_seed2_out/flow_summary.csv
done
echo
echo "  ideal FCT at the 9.5 Gbps app cap = 4.0e9*8/9.5e9 = 3.3684 s"
echo "  slowdown = actual / ideal:"
for a in dcqcn dctcp timely hpcc; do
  printf "  %-8s " "$a"
  awk -F, 'NR>1 && $6==65 {printf "%.4f x\n", $11/3.36842}' m_${a}_s4_seed2_out/flow_summary.csv
done
