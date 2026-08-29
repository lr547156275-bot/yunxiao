set -u
cd /work/simulation
D=experiment/scheme1_sba
L=/work/matrix_logs
export LD_LIBRARY_PATH=/work/simulation/build
# Order: cheap and dual-bottleneck first, S4/S5 last (they dominate runtime, so
# a late platform failure costs the least-informative scenarios).
for spec in "s1 2.1" "s2 2.5" "s3 3.0" "s6 2.5" "s4 5.5" "s5 6.0"; do
  set -- $spec
  tag=$1; stop=$2
  echo "########## $tag (stop=${stop}s) ##########"
  MAX_JOBS=1 bash $D/run_matrix.sh "$tag" "$stop" 2 2>&1 | grep -E "^(OK|FAIL|SKIP|HASH|=====|matrix:)"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -ne 0 ]; then
    echo "########## $tag ABORTED (rc=$rc); stopping the matrix ##########"
    exit 1
  fi
done
echo "MATRIX_COMPLETE done_flags=$(ls $L/m_*_s[1-6]_seed2.done 2>/dev/null | wc -l)/30"
