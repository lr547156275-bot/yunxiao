set -u
L=/work/matrix_logs
echo "=== existing done flags (from the PRE-freeze build) ==="
ls $L/m_*_s*_seed2.done 2>/dev/null | wc -l | sed 's/^/  matrix cells: /'
echo "=== their recorded binary hash ==="
grep -h "^binary_sha256" $L/m_cbapsba_s3_seed2.manifest 2>/dev/null | cut -c1-40
echo "  freeze binary: binary_sha256=0156d0bacf69034f78703f..."
echo "=== do any manifests already carry p2p_lib_sha256? ==="
grep -l "p2p_lib_sha256" $L/m_*_seed2.manifest 2>/dev/null | wc -l | sed 's/^/  with p2p_lib: /'
echo
echo "=== these 30 cells were built with the OLD binary and must be re-run ==="
echo "    Moving their flags + manifests aside (NOT deleting) so the matrix reruns them."
mkdir -p $L/pre_freeze_run
moved=0
for f in $L/m_*_s[1-6]_seed2.done $L/m_*_s[1-6]_seed2.manifest; do
  [ -e "$f" ] || continue
  mv -f "$f" $L/pre_freeze_run/ && moved=$((moved+1))
done
echo "  moved $moved files to $L/pre_freeze_run/"
echo "  remaining matrix done flags: $(ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l)"
echo
echo "=== output dirs are left in place; ns-3 opens outputs with w and overwrites ==="
ls -d /work/simulation/experiment/scheme1_sba/m_*_out 2>/dev/null | wc -l | sed 's/^/  existing out dirs: /'
