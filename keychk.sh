set -u
cd /work/simulation/scratch
echo "=== duplicate-key audit: any of my 8 keys parsed more than once? ==="
for k in CBAP_DELAY_CREDIT_ENABLE CBAP_QUEUE_DELAY_TARGET_US \
         CBAP_QUEUE_DELAY_HARD_LIMIT_US CBAP_CREDIT_HORIZON_US \
         CBAP_MAX_OVERSUB_RATIO CBAP_CREDIT_DRAIN_RATIO \
         CBAP_QUEUE_SAFETY_MARGIN_BYTES CBAP_DELAY_CREDIT_FILE; do
  n=$(grep -c "key.compare(\"$k\")" third.cc)
  printf "  %-34s parsed %s time(s) %s\n" "$k" "$n" "$([ "$n" = "1" ] && echo OK || echo COLLISION)"
done
echo "=== and the pre-existing keys I must not disturb ==="
for k in CBAP_MAX_DRAIN_RATIO CBAP_QUEUE_TARGET_FRACTION; do
  n=$(grep -c "key.compare(\"$k\")" third.cc)
  printf "  %-34s parsed %s time(s)\n" "$k" "$n"
done
