set -u
L=/work/matrix_logs
D=/work/simulation/experiment/scheme1_sba
echo "=== move pg0 done flags + manifests aside (NOT deleted) ==="
mkdir -p $L/pg0_invalid_run
n=0
for f in $L/m_*_s[1-6]_seed2.done $L/m_*_s[1-6]_seed2.manifest; do
  [ -e "$f" ] || continue
  mv -f "$f" $L/pg0_invalid_run/ && n=$((n+1))
done
echo "  moved $n files to $L/pg0_invalid_run/"
echo "  remaining matrix done flags: $(ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l)"
echo
echo "=== rebuild the baseline manifest with the NEW flow-file hashes ==="
cd /work/simulation
mv -f $L/matrix_baseline.manifest $L/pg0_invalid_run/matrix_baseline.manifest.pg0 2>/dev/null
{
  echo "freeze=CBAP_SBA_FINAL_FREEZE"
  echo "config_fix=background_data_flows_pg0_to_pg3"
  echo "binary_sha256=$(sha256sum build/scratch/third | cut -d' ' -f1)"
  echo "p2p_lib_sha256=$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)"
  echo "git_commit=$(git -C /work rev-parse HEAD)"
  echo "git_branch=$(git -C /work rev-parse --abbrev-ref HEAD)"
  echo "topology_sha256=$(sha256sum experiment/scheme1_sba/topology.txt | cut -d' ' -f1)"
  echo "toolchain=g++-7 7.5.0 / python2.7 (container hpcc-build, ubuntu 20.04)"
  for t in s1 s2 s3 s4 s5 s6; do
    echo "${t}_config_sha256=$(sha256sum experiment/scheme1_sba/${t}_config.txt | cut -d' ' -f1)"
    echo "${t}_flow_sha256=$(sha256sum experiment/scheme1_sba/${t}_flow.txt | cut -d' ' -f1)"
  done
} > $L/matrix_baseline.manifest
echo "  binary/lib unchanged (algorithm still frozen):"
grep -E "^(binary_sha256|p2p_lib_sha256)" $L/matrix_baseline.manifest | cut -c1-46 | sed 's/^/    /'
echo "  flow hashes CHANGED vs pg0 baseline:"
for t in s3 s4; do
  new=$(awk -F= -v k=${t}_flow_sha256 '$1==k{print substr($2,1,16)}' $L/matrix_baseline.manifest)
  old=$(awk -F= -v k=${t}_flow_sha256 '$1==k{print substr($2,1,16)}' $L/pg0_invalid_run/matrix_baseline.manifest.pg0 2>/dev/null)
  printf "    %s: pg0=%s -> pg3=%s\n" "$t" "$old" "$new"
done
