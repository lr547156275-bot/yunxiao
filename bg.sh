cd /work/simulation
python2 ./waf build > /work/matrix_logs/build_gen2.log 2>&1
code=$?
# waf can report success for cached targets while a compile failed; gate on
# BOTH the exit code and the absence of "error:" in the log.
errs=$(grep -c "error:" /work/matrix_logs/build_gen2.log)
echo "WAF_EXIT=$code COMPILE_ERRORS=$errs" >> /work/matrix_logs/build_gen2.log
if [ "$code" -eq 0 ] && [ "$errs" -eq 0 ]; then
  cd /work/simulation/experiment/scheme1_sba
  export LD_LIBRARY_PATH=/work/simulation/build
  timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
    > /work/matrix_logs/au_s3_rho090.log 2>&1
  echo "RUN_EXIT=$?" >> /work/matrix_logs/build_gen2.log
else
  echo "RUN_SKIPPED" >> /work/matrix_logs/build_gen2.log
fi
echo "GEN2_DONE" >> /work/matrix_logs/build_gen2.log
