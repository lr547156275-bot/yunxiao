set -u
L=/work/matrix_logs
echo "=== 1. all 30 manifests carry the FINAL FREEZE hashes + commit? ==="
tot=$(ls $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
b=$(grep -l "^binary_sha256=0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35" $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
p=$(grep -l "^p2p_lib_sha256=0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72" $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
g=$(grep -l "^git_commit=2ece98e378c69a6d38884dd1c1a74d007618ae9c" $L/m_*_s[1-6]_seed2.manifest 2>/dev/null | wc -l)
echo "  manifests=$tot  third=$b  p2p_lib=$p  git_commit=$g   (all should be 30)"
echo
echo "=== 2. every cell: exit 0, full incast, trace ok ==="
bad=0
for f in $L/m_*_s[1-6]_seed2.manifest; do
  e=$(awk -F= '$1=="exit_code"{print $2}' $f)
  c=$(awk -F= '$1=="completed_incast"{print $2}' $f)
  x=$(awk -F= '$1=="expected_incast"{print $2}' $f)
  t=$(awk -F= '$1=="trace_complete"{print $2}' $f)
  if [ "$e" != "0" ] || [ "$c" != "$x" ] || [ "$t" != "ok" ]; then
    echo "  PROBLEM $(basename $f): exit=$e incast=$c/$x trace=$t"; bad=$((bad+1))
  fi
done
[ "$bad" -eq 0 ] && echo "  all 30 clean (exit 0, incast complete, trace ok)"
echo
echo "=== 3. safety: PFC / drops / retx across all 30 ==="
cd /work/simulation/experiment/scheme1_sba
tp=0; tr=0
for d in m_*_s[1-6]_seed2_out; do
  [ -d "$d" ] || continue
  p=$(awk -F, 'NR>1{s+=$8} END{print s+0}' $d/selected_link_timeseries.csv 2>/dev/null || echo 0)
  r=$(awk -F, 'NR>1{s+=$15} END{print s+0}' $d/flow_summary.csv 2>/dev/null || echo 0)
  tp=$((tp+p)); tr=$((tr+r))
done
echo "  total PFC events across 30 cells: $tp"
echo "  total retx bytes  across 30 cells: $tr"
echo
echo "=== 4. eta trace present for the 6 CBAP-SBA cells only? ==="
for t in s1 s2 s3 s6 s4 s5; do
  f=m_cbapsba_${t}_seed2_out/eta_feasibility.csv
  [ -f "$f" ] && printf "  %-3s rows=%s\n" "$t" "$(awk 'END{print NR-1}' $f)" || printf "  %-3s MISSING\n" "$t"
done
