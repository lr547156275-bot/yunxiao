set -u
cd /workspaces/yunxiao
# Stage tracked changes (modified + deleted) -- these are the frozen results
# replacing pre-freeze ones, all recoverable from HEAD if ever needed.
git add -u
echo "=== tracked changes staged ==="
git diff --cached --stat | tail -3

# Untracked: code, configs, docs and small derived data ONLY.
# Raw traces (qlen.txt / *_timeseries.csv, 4.27 GB) stay out: GitHub rejects
# >100MB files and they regenerate from config + the pinned binary.
D=simulation/experiment/scheme1_sba
for p in \
  $D/paper_data \
  $D/run_eta_sweep.sh $D/eta_metrics.py $D/eta_sweep \
  $D/a_cbapsba_s3_migoff_seed2.txt \
  $D/g_cbapsba_s3_seed2.txt $D/g_cbapsba_s4_seed2.txt \
  $D/f_cbapsba_s3_seed2.txt $D/f_cbapsba_s4_seed2.txt \
  $D/m_cbapsba_s4_eta020_seed2.txt $D/m_cbapsba_s4_eta035_seed2.txt \
  $D/m_cbapsba_s4_eta065_seed2.txt $D/m_cbapsba_s4_eta080_seed2.txt ; do
  [ -e "$p" ] && git add -f "$p" 2>/dev/null
done
# The frozen per-cell configs for all 30 matrix cells (small, define the runs).
git add -f $D/m_*_s[1-6]_seed2.txt 2>/dev/null
# Preserve the pre-freeze report/analysis as a tracked comparison set.
git add -f $D/final_report_pre_freeze $D/analysis_s*_pre_freeze 2>/dev/null

echo "=== staged totals ==="
git diff --cached --numstat | wc -l | sed 's/^/  files staged: /'
git diff --cached --name-only | xargs -r du -ch 2>/dev/null | tail -1 | sed 's/^/  size: /'
echo "=== any staged file over 50MB? (GitHub hard limit is 100MB) ==="
git diff --cached --name-only | while read -r f; do
  [ -f "$f" ] && s=$(stat -c %s "$f") && [ "$s" -gt 52428800 ] && echo "  BIG: $f ($((s/1048576))MB)"
done || true
echo "  (no output above = all staged files are small)"
echo "=== confirm no raw trace slipped in ==="
git diff --cached --name-only | grep -cE "qlen\.txt|selected_(flow|link)_timeseries\.csv" | sed 's/^/  raw trace files staged: /'
