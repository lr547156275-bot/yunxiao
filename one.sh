cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
  > /work/matrix_logs/au_s3_rho090.log 2>&1
echo "exit=$?"
echo "=== stage counts ==="
awk -F, 'NR>1{c[$5]++} END{for(s in c) printf "  %-40s %d\n", s, c[s]}' au_s3_rho090_out/actuation.csv | sort -k2 -rn | head
echo "ONE_DONE"
