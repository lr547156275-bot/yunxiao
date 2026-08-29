set -u
cd /work/simulation
D=experiment/scheme1_sba
L=/work/matrix_logs
echo "=== binaries after the merge (must be the frozen pair) ==="
T=$(sha256sum build/scratch/third | cut -d' ' -f1)
P=$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)
printf "  third   %s\n" "$T"
printf "  p2p lib %s\n" "$P"
[ "$T" = "0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35" ] && echo "  third   MATCHES freeze" || echo "  third   MISMATCH"
[ "$P" = "0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72" ] && echo "  p2p lib MATCHES freeze" || echo "  p2p lib MISMATCH"

echo
echo "=== archive the frozen pair ==="
mkdir -p $L/binary_archive
cp -f build/scratch/third $L/binary_archive/third_FINAL_FREEZE_0156d0ba
cp -f build/libns3.18-point-to-point-debug.so $L/binary_archive/libp2p_FINAL_FREEZE_0bacef18
ls -la $L/binary_archive/ | tail -3

echo
echo "=== write the FINAL FREEZE baseline manifest (gates all 30 cells) ==="
# Move the old baseline aside rather than overwrite: it described the previous
# build and the earlier results were gated against it.
[ -f $L/matrix_baseline.manifest ] && mv -f $L/matrix_baseline.manifest $L/matrix_baseline.manifest.pre_freeze
{
  echo "freeze=CBAP_SBA_FINAL_FREEZE"
  echo "binary_sha256=$T"
  echo "p2p_lib_sha256=$P"
  echo "git_commit=$(git -C /work rev-parse HEAD)"
  echo "git_branch=$(git -C /work rev-parse --abbrev-ref HEAD)"
  echo "topology_sha256=$(sha256sum $D/topology.txt | cut -d' ' -f1)"
  echo "toolchain=g++-7 7.5.0 / python2.7 (container hpcc-build, ubuntu 20.04)"
  for t in s1 s2 s3 s4 s5 s6; do
    echo "${t}_config_sha256=$(sha256sum $D/${t}_config.txt | cut -d' ' -f1)"
    echo "${t}_flow_sha256=$(sha256sum $D/${t}_flow.txt | cut -d' ' -f1)"
  done
} > $L/matrix_baseline.manifest
cat $L/matrix_baseline.manifest
