cd /work/simulation
python2 ./waf build > /work/matrix_logs/build_gen4.log 2>&1
code=$?; errs=$(grep -c "error:" /work/matrix_logs/build_gen4.log)
echo "WAF_EXIT=$code COMPILE_ERRORS=$errs" >> /work/matrix_logs/build_gen4.log
if [ "$code" -eq 0 ] && [ "$errs" -eq 0 ]; then
  echo "third  : $(sha256sum /work/simulation/build/scratch/third | cut -c1-16)" >> /work/matrix_logs/build_gen4.log
  echo "libns3 : $(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -c1-16)" >> /work/matrix_logs/build_gen4.log
  cd /work/simulation/experiment/scheme1_sba
  export LD_LIBRARY_PATH=/work/simulation/build
  timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
    > /work/matrix_logs/au_s3_rho090.log 2>&1
  echo "RUN_EXIT=$?" >> /work/matrix_logs/build_gen4.log
else echo "RUN_SKIPPED" >> /work/matrix_logs/build_gen4.log; fi
echo "GEN4_DONE" >> /work/matrix_logs/build_gen4.log
