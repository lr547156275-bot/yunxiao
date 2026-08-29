echo "=== rho040 tail ==="
tail -25 /work/matrix_logs/cr_s3_rho040.log
echo
echo "=== rho060 tail ==="
tail -12 /work/matrix_logs/cr_s3_rho060.log
echo
echo "=== any exception/assert text ==="
grep -nE "terminate|what\(\):|assert|logic_error|invalid_argument|SBA " /work/matrix_logs/cr_s3_rho040.log | tail -20
