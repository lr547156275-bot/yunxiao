cd /work
echo "=== why 2641 lines? check for CRLF/whitespace-only churn ==="
git diff --numstat 3050a84 -- simulation/scratch/third.cc
git diff --ignore-all-space --numstat 3050a84 -- simulation/scratch/third.cc
echo "  ^ second line = same diff ignoring whitespace"
echo
echo "############ CLEAN DIFF: audit changes only ############"
echo "baseline = /work/matrix_logs/third.cc.bak_preaudit (snapshot taken before ANY audit edit)"
if [ -f /work/matrix_logs/third.cc.bak_preaudit ]; then
  diff -u /work/matrix_logs/third.cc.bak_preaudit simulation/scratch/third.cc > /tmp/clean.diff
  echo "  added lines:   $(grep -c '^+' /tmp/clean.diff)"
  echo "  removed lines: $(grep -c '^-' /tmp/clean.diff)"
  echo
  echo "--- ALL removed lines (excluding diff headers) ---"
  grep -E "^-" /tmp/clean.diff | grep -vE "^---" || echo "  (none removed)"
  echo
  echo "--- do the ADDED lines touch rate/pacing/CC/migration/replan/DCQCN? ---"
  grep -E "^\+" /tmp/clean.diff | grep -vE "^\+\+\+" \
    | grep -E "m_rate|m_nextAvail|ChangeRate|MinRate|RateAI|targetRate|migration|Replan|mlx\.|hp\.|dctcp|tmly" \
    || echo "  (NONE -- no added line touches any of those)"
  echo
  echo "--- what the added lines DO touch (top identifiers) ---"
  grep -E "^\+" /tmp/clean.diff | grep -vE "^\+\+\+" \
    | grep -oE "cbap_[a-z_]+|CbapActuation[A-Za-z]*|GetCbapQpForAudit|SampleCbapPfcAudit" \
    | sort | uniq -c | sort -rn | head -14
fi
