cd /work/simulation/experiment/scheme1_sba
for f in CBAP_CORE_INITIAL_RELEASE_PREFLIGHT.md core_analyse.py core_initial_release_unit_check.py; do
  echo "remote $(sha256sum $f|cut -c1-12)  $f  ($(wc -l < $f) lines)"
done
echo
echo "=== report sections ==="
grep -n "^## " CBAP_CORE_INITIAL_RELEASE_PREFLIGHT.md
echo
echo "=== final re-verify: both acceptance runs ==="
python3 core_analyse.py 2>&1 | grep -E "passed"
python3 core_analyse.py cr_s4_rho040 0.4 2>&1 | grep -E "passed"
python3 core_initial_release_unit_check.py 2>&1 | grep -E "passed"
echo
echo "=== nothing deleted: results dirs intact ==="
ls -d *_out 2>/dev/null | wc -l
ls -d paper_data_pg3 pg0_invalid 2>/dev/null
echo
echo "=== git: uncommitted, as required ==="
cd /work && git status --porcelain | head -20
echo "  branch: $(git rev-parse --abbrev-ref HEAD)  HEAD: $(git rev-parse --short HEAD)"
