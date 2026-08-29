cd /work/simulation/experiment/scheme1_sba
echo "remote $(sha256sum core_analyse.py|cut -c1-12)"
python3 -m py_compile core_analyse.py && echo SYNTAX_OK
echo "=== flow sizes: is S4 also 1 MiB per flow? ==="
awk '{print $3}' s3_flow.txt 2>/dev/null | sort -u | head -5
echo "--- s4 ---"
awk '{print $3}' s4_flow.txt 2>/dev/null | sort -u | head -5
echo "=== v2 driver progress ==="
cat /work/matrix_logs/core_driver_v2.log 2>/dev/null
