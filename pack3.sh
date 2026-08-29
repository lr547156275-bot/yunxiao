set -u
cd /work/simulation/experiment/scheme1_sba
D=paper_data_pg3
mkdir -p $D/manifests $D/tables
cp -f /work/matrix_logs/m_*_s[1-6]_seed2.manifest $D/manifests/ 2>/dev/null
cp -f /work/matrix_logs/matrix_baseline.manifest $D/manifests/ 2>/dev/null
cp -f pg0_invalid/INVALID_pg0_DO_NOT_USE.md $D/ 2>/dev/null
# the pg0 flow files, so the exact configuration difference is auditable
mkdir -p $D/config_diff
for t in s1 s2 s3 s4 s5 s6; do
  cp -f pg0_invalid/${t}_flow_pg0.txt $D/config_diff/ 2>/dev/null
  cp -f ${t}_flow.txt $D/config_diff/${t}_flow_pg3.txt 2>/dev/null
done
echo "=== assembled ==="
echo "  csv       : $(ls $D/*.csv | wc -l)"
echo "  md        : $(ls $D/*.md 2>/dev/null | wc -l)"
echo "  manifests : $(ls $D/manifests/ | wc -l)"
echo "  config_diff: $(ls $D/config_diff/ | wc -l)"
rm -f /work/cbap_sba_pg3_results.tar.gz
tar czf /work/cbap_sba_pg3_results.tar.gz $D/
ls -la /work/cbap_sba_pg3_results.tar.gz | awk '{printf "  archive: %s bytes\n", $5}'
echo "  sha256: $(sha256sum /work/cbap_sba_pg3_results.tar.gz | cut -d' ' -f1)"
echo "  entries: $(tar tzf /work/cbap_sba_pg3_results.tar.gz | wc -l)"
