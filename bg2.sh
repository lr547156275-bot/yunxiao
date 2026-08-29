cd /work/simulation
python2 ./waf build > /work/matrix_logs/build_gen3.log 2>&1
code=$?; errs=$(grep -c "error:" /work/matrix_logs/build_gen3.log)
echo "WAF_EXIT=$code COMPILE_ERRORS=$errs" >> /work/matrix_logs/build_gen3.log
if [ "$code" -eq 0 ] && [ "$errs" -eq 0 ]; then
  cd /work/simulation/experiment/scheme1_sba
  export LD_LIBRARY_PATH=/work/simulation/build
  timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
    > /work/matrix_logs/au_s3_rho090.log 2>&1
  echo "RUN_EXIT=$?" >> /work/matrix_logs/build_gen3.log
else echo "RUN_SKIPPED" >> /work/matrix_logs/build_gen3.log; fi
echo "GEN3_DONE" >> /work/matrix_logs/build_gen3.log
