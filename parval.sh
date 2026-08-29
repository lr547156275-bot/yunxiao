set -u
L=/work/matrix_logs
P=$L/pre_freeze_run
echo "=== S1: wall time serial (pre-freeze) vs parallel (now) ==="
for a in dcqcn dctcp timely hpcc; do
  s=$(awk -F= '$1=="wall_seconds"{print $2}' $P/m_${a}_s1_seed2.manifest 2>/dev/null)
  n=$(awk -F= '$1=="wall_seconds"{print $2}' $L/m_${a}_s1_seed2.manifest 2>/dev/null)
  j=$(awk -F= '$1=="parallel_jobs"{print $2}' $L/m_${a}_s1_seed2.manifest 2>/dev/null)
  printf "  %-8s serial=%-5ss  now=%-5ss  jobs=%s\n" "$a" "${s:-?}" "${n:-?}" "${j:-1}"
done
echo
echo "=== do the PARALLEL cells reproduce the serial results exactly? ==="
echo "    (determinism check: parallelism must not change any number)"
for a in timely hpcc; do
  d=/work/simulation/experiment/scheme1_sba/m_${a}_s1_seed2_out
  printf "  %-8s " "$a"
  awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11} END{printf "incast=%d/16 mean_fct=%.6f ms\n", n, s/n*1000}' $d/flow_summary.csv
done
echo "  pre-freeze reference: timely 17.759 p99 / hpcc 4.092 p99 (from final_results.csv)"
echo
echo "=== both hashes recorded on the parallel cells? ==="
for a in timely hpcc; do
  printf "  %-8s " "$a"
  b=$(awk -F= '$1=="binary_sha256"{print substr($2,1,12)}' $L/m_${a}_s1_seed2.manifest)
  p=$(awk -F= '$1=="p2p_lib_sha256"{print substr($2,1,12)}' $L/m_${a}_s1_seed2.manifest)
  echo "third=$b p2p=$p"
done
