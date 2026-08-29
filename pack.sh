set -u
cd /work/simulation/experiment/scheme1_sba
D=paper_data
# Gather the frozen report artifacts alongside the paper CSVs.
cp -f final_report/final_results.csv $D/
mkdir -p $D/tables $D/manifests
cp -f final_report/tables/*.md $D/tables/ 2>/dev/null
cp -f final_report/anomalies.md $D/ 2>/dev/null
cp -f final_report/manifests/*.manifest $D/manifests/ 2>/dev/null
cp -f /work/matrix_logs/matrix_baseline.manifest $D/manifests/ 2>/dev/null
# the ablation cell's own manifest-equivalent: record its identity explicitly
{
  echo "cell=a_cbapsba_s3_migoff_seed2"
  echo "ablation=migration_off"
  echo "scenario=s3"
  echo "seed=2"
  echo "stop_time=3.0"
  echo "cbap_migration_enable=0"
  echo "config_sha256=$(sha256sum a_cbapsba_s3_migoff_seed2.txt | cut -d' ' -f1)"
  echo "binary_sha256=$(sha256sum /work/simulation/build/scratch/third | cut -d' ' -f1)"
  echo "p2p_lib_sha256=$(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)"
  echo "git_commit=$(git -C /work rev-parse HEAD)"
  echo "note=config-only change from m_cbapsba_s3_seed2.txt; verified to differ in exactly one key"
} > $D/manifests/a_cbapsba_s3_migoff_seed2.manifest
echo "=== assembled ==="
echo "  csv           : $(ls $D/*.csv | wc -l)"
echo "  md            : $(ls $D/*.md | wc -l)"
echo "  tables/       : $(ls $D/tables/ | wc -l)"
echo "  manifests/    : $(ls $D/manifests/ | wc -l)"
echo "=== package ==="
rm -f /work/cbap_sba_paper_delivery.tar.gz
tar czf /work/cbap_sba_paper_delivery.tar.gz paper_data/
ls -la /work/cbap_sba_paper_delivery.tar.gz | awk '{printf "  %s bytes\n", $5}'
echo "  sha256: $(sha256sum /work/cbap_sba_paper_delivery.tar.gz | cut -d' ' -f1)"
echo "  entries: $(tar tzf /work/cbap_sba_paper_delivery.tar.gz | wc -l)"
