cd /work/simulation/experiment/scheme1_sba
for f in CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md CBAP_CORE_INITIAL_RELEASE_PREFLIGHT.md; do
  echo "remote $(sha256sum $f|cut -c1-12)  $f  ($(wc -l < $f) lines)"
done
echo
echo "=== audit report sections ==="
grep -n "^## " CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md
echo
echo "=== guard: MIN_RATE untouched, 50:50 not restored, no credit/lease code ==="
grep -hE "^MIN_RATE" m_cbapsba_s3_seed2.txt au_s3_rho055.txt
echo "  CBAP_DELAY_CREDIT_ENABLE in audit cells: $(grep -h CBAP_DELAY_CREDIT_ENABLE au_s3_rho*.txt | sort -u | tr '\n' ' ')"
echo "  core mode on: $(grep -h CBAP_CORE_INITIAL_RELEASE au_s3_rho055.txt)"
echo
echo "=== results preserved ==="
ls -d *_out 2>/dev/null | wc -l
echo "=== git still uncommitted ==="
cd /work && git status --porcelain -- simulation/ | head; echo "  HEAD=$(git rev-parse --short HEAD) branch=$(git rev-parse --abbrev-ref HEAD)"
