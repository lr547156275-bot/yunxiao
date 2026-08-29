cd /work/simulation/experiment/scheme1_sba
for s in s3 s4; do
  f=$(grep -h "^FLOW_FILE" m_cbapsba_${s}_seed2.txt | awk '{print $2}')
  echo "=== $s flow file: $f"
  head -3 "$f"
  echo "  distinct sizes (field 5):"
  awk 'NR>1{print $5}' "$f" | sort -un | head -5
  echo "  line count: $(wc -l < "$f")"
done
