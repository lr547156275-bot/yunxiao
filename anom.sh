set -u
echo "=== why git_commit unknown? (git inside container vs repo root) ==="
docker() { :; }   # no docker inside
cd /work
git rev-parse HEAD 2>&1 | head -2
echo "  ls -d /work/.git : $(ls -d /work/.git 2>/dev/null || echo MISSING)"
echo
echo "=== are s3 and s4 flow files genuinely identical? ==="
cd /work/simulation/experiment/scheme1_sba
if cmp -s s3_flow.txt s4_flow.txt; then
  echo "  IDENTICAL -- expected: S3 and S4 differ only in APP_RATE_CAP_BPS (8G vs 9.5G),"
  echo "  not in the flow file. Confirm from configs:"
  grep -H "^APP_RATE_CAP_BPS" s3_config.txt s4_config.txt | sed 's/^/    /'
  grep -H "^SIMULATOR_STOP_TIME" s3_config.txt s4_config.txt | sed 's/^/    /'
else
  echo "  DIFFER (so the shared hash would be a bug)"
fi
