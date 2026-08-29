cd /work/simulation/experiment/scheme1_sba
python3 qc_correctness_audit.py 2>&1
echo "---build---"
grep -hE "QC_BUILD_DONE|WAF_EXIT|^libns3" /work/matrix_logs/build_qc.log 2>/dev/null
grep -hE "error:" /work/matrix_logs/build_qc.log 2>/dev/null | head -4
