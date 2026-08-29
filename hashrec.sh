set -u
cd /work/simulation
D=experiment/scheme1_sba
echo "=== FINAL FREEZE candidate hashes ==="
printf "  third_sha256    = %s\n" "$(sha256sum build/scratch/third | cut -d' ' -f1)"
printf "  p2p_lib_sha256  = %s\n" "$(sha256sum build/libns3.18-point-to-point-debug.so | cut -d' ' -f1)"
printf "  git_commit      = %s\n" "$(git -C /work rev-parse HEAD 2>/dev/null || echo unknown)"
printf "  git_dirty_files = %s\n" "$(git -C /work status --porcelain 2>/dev/null | wc -l)"
printf "  topology_sha256 = %s\n" "$(sha256sum $D/topology.txt | cut -d' ' -f1)"
for t in s3 s4; do
  printf "  %s_flow_sha256  = %s\n" "$t" "$(sha256sum $D/${t}_flow.txt | cut -d' ' -f1)"
done
echo
echo "=== sanity-cell config hashes ==="
for t in s3 s4; do
  printf "  g_cbapsba_%s_seed2.txt = %s\n" "$t" "$(sha256sum $D/g_cbapsba_${t}_seed2.txt | cut -d' ' -f1)"
done
echo
echo "=== does run_matrix.sh now gate on BOTH binaries? ==="
grep -c "p2p_lib_sha256" $D/run_matrix.sh | sed 's/^/  p2p_lib_sha256 references in runner: /'
grep -n "HASH MISMATCH: libns3" $D/run_matrix.sh | head -1 | sed 's/^/  /'
