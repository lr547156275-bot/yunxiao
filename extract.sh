set -u
cd /work/simulation/experiment/scheme1_sba
# Preserve the pre-freeze report so the paper can show before/after.
if [ -d final_report ] && [ ! -d final_report_pre_freeze ]; then
  mv final_report final_report_pre_freeze
  echo "  preserved old report -> final_report_pre_freeze/"
fi
for t in analysis_s1 analysis_s2 analysis_s3 analysis_s4 analysis_s5 analysis_s6; do
  [ -d "$t" ] && [ ! -d "${t}_pre_freeze" ] && mv "$t" "${t}_pre_freeze"
done
echo "  preserved old analysis_s* dirs"
echo "=== metrics.py per scenario (LOGS points at /work/matrix_logs) ==="
sed -i "s|^LOGS = '/workspaces/yunxiao/matrix_logs'|LOGS = '/work/matrix_logs'|" metrics.py 2>/dev/null
grep -n "^LOGS = " metrics.py | sed 's/^/  /'
for t in s1 s2 s3 s6 s4 s5; do
  python3 metrics.py $t 2 > /work/matrix_logs/extract_${t}.txt 2>&1
  printf "  %s exit=%d rows=%s\n" "$t" "$?" "$(awk 'END{print NR-1}' analysis_${t}/per_run.csv 2>/dev/null || echo 0)"
done
