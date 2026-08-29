set -u
cd /work/simulation/experiment/scheme1_sba
sed -i "s|^LOGS = '/workspaces/yunxiao/matrix_logs'|LOGS = '/work/matrix_logs'|" build_report.py 2>/dev/null
python3 build_report.py 2 > /work/matrix_logs/report_build.txt 2>&1
echo "exit=$?"
tail -12 /work/matrix_logs/report_build.txt
echo "=== final_report contents ==="
ls final_report/ 2>/dev/null | sed 's/^/  /'
echo "=== rows in final_results.csv ==="
awk -F, 'NR>1{n++} END{print "  " n " rows"}' final_report/final_results.csv 2>/dev/null
