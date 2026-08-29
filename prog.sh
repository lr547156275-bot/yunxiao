echo "=== running processes ==="
ps -eo etime,cmd | grep -E "third cr_s3" | grep -v grep
echo "=== sim time reached ==="
for n in cr_s3_legacy5050 cr_s3_rho000; do
  printf "  %-20s " $n
  tail -3 /work/matrix_logs/${n}.log 2>/dev/null | tr '\n' ' '
  echo
done
echo "=== stop time in config ==="
grep -h SIMULATOR_STOP_TIME /work/simulation/experiment/scheme1_sba/cr_s3_rho040.txt
