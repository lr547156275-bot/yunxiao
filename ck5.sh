echo "=== elapsed ==="
ps -eo etime,cmd | grep "third cr_s" | grep -v grep | grep -v timeout
echo "=== driver ==="
cat /work/matrix_logs/core_driver_v2.log
echo "=== did rho040 get past admission this time? ==="
grep -cE "logic_error|violates" /work/matrix_logs/cr_s3_rho040.log 2>/dev/null
tail -2 /work/matrix_logs/cr_s3_rho040.log 2>/dev/null
