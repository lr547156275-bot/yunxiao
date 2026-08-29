cd /work/simulation/experiment/scheme1_sba
echo "remote $(sha256sum CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md|cut -c1-12)  $(wc -l < CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md) lines"
echo "=== is 160us still claimed anywhere? ==="
grep -n "160 µs\|160us\|160 us" CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md || echo "  (only as the superseded candidate)"
echo "=== H_guard value stated ==="
grep -n "H_guard.*175\|175.0 µs\|175 µs" CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md | head -5
echo
echo "=== constraints ==="
echo "  MIN_RATE: $(grep -h '^MIN_RATE' au_s3_rho090.txt)"
echo "  controller flag present in source? $(grep -c CBAP_QUEUE_CONTROLLER_ENABLE /work/simulation/scratch/third.cc) (0 expected, not implemented)"
echo "  results dirs: $(ls -d *_out 2>/dev/null | wc -l)"
cd /work && echo "  HEAD=$(git rev-parse --short HEAD) branch=$(git rev-parse --abbrev-ref HEAD)"
