cd /work/simulation/experiment/scheme1_sba
echo "remote $(sha256sum CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md|cut -c1-12)  $(wc -l < CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md) lines"
echo "=== sections ==="; grep -n "^## " CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md
echo
echo "=== constraint re-check ==="
echo "  MIN_RATE: $(grep -h '^MIN_RATE' au_s3_rho090.txt)"
echo "  switch files modified? $(cd /work && git diff --stat 3050a84 -- simulation/src/point-to-point/model/switch-mmu.cc simulation/src/point-to-point/model/switch-mmu.h simulation/src/point-to-point/model/switch-node.cc | wc -l) lines of diffstat"
echo "  results dirs: $(ls -d *_out 2>/dev/null | wc -l)"
cd /work && echo "  HEAD=$(git rev-parse --short HEAD)  branch=$(git rev-parse --abbrev-ref HEAD)  (uncommitted: $(git status --porcelain -- simulation/ | wc -l) paths)"
