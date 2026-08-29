cd /work/simulation/experiment/scheme1_sba
echo "remote $(sha256sum qc_preflight_analyse.py|cut -c1-12)"
python3 -m py_compile qc_preflight_analyse.py && echo SYNTAX_OK
echo "--- progress ---"
cat /work/matrix_logs/preflight_driver.log 2>/dev/null
ps -eo etime,cmd | grep "[t]hird qc_s3" | head -3
