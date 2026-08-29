cd /work/simulation
python2 ./waf build > /work/matrix_logs/build_qc.log 2>&1
code=$?; errs=$(grep -c "error:" /work/matrix_logs/build_qc.log)
echo "WAF_EXIT=$code COMPILE_ERRORS=$errs" >> /work/matrix_logs/build_qc.log
if [ "$code" -eq 0 ] && [ "$errs" -eq 0 ]; then
  echo "third  : $(sha256sum /work/simulation/build/scratch/third | cut -c1-16)" >> /work/matrix_logs/build_qc.log
  echo "libns3 : $(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -c1-16)" >> /work/matrix_logs/build_qc.log
fi
echo "QC_BUILD_DONE" >> /work/matrix_logs/build_qc.log
