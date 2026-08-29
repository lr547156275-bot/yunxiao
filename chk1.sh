set -u
L=/work/matrix_logs
f=$L/m_dcqcn_s1_seed2.manifest
echo "=== does the new manifest carry BOTH hashes + git commit? ==="
grep -E "^(binary_sha256|p2p_lib_sha256|git_commit|git_dirty|completed_incast|expected_incast|trace_complete|exit_code|wall_seconds)" "$f" 2>/dev/null | sed 's/^/  /'
echo
echo "=== do they match the FINAL FREEZE baseline? ==="
for k in binary_sha256 p2p_lib_sha256; do
  a=$(awk -F= -v k=$k '$1==k{print $2}' "$f")
  b=$(awk -F= -v k=$k '$1==k{print $2}' $L/matrix_baseline.manifest)
  [ "$a" = "$b" ] && echo "  $k MATCHES" || echo "  $k MISMATCH ($a vs $b)"
done
echo
echo "=== data sanity: does S1/DCQCN reproduce the known determinism check? ==="
D=/work/simulation/experiment/scheme1_sba/m_dcqcn_s1_seed2_out
awk -F, 'NR>1 && $6!=65 && $13==1 {n++; s+=$11} END{printf "  incast=%d/16  mean_fct=%.3f ms  (pre-freeze reference: 17.399 ms)\n", n, s/n*1000}' $D/flow_summary.csv
echo "=== eta trace absent for a non-CBAP algorithm (as expected)? ==="
ls $D/eta_feasibility.csv 2>/dev/null && echo "  present (unexpected)" || echo "  absent - correct, DCQCN has no eta"
