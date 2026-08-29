set -u
L=/work/matrix_logs
grep -E "^(FAIL|HASH|##########|MATRIX_COMPLETE)" $L/matrix_pg3_driver.log 2>/dev/null
echo "PROGRESS=$(ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l)/30"
if ! pgrep -f matrix_par >/dev/null 2>&1 && ! grep -q MATRIX_COMPLETE $L/matrix_pg3_driver.log 2>/dev/null; then echo DRIVER_STOPPED; fi
df -h /work | awk 'NR==2 && $5+0>92 {print "DISK_CRITICAL " $5}'
