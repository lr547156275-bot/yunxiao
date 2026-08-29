set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== step 3: background DATA flows pg=0 -> pg=3 (7 flows across 6 scenarios) ==="
for f in s1_flow.txt s2_flow.txt s3_flow.txt s4_flow.txt s5_flow.txt s6_flow.txt; do
  cp -f "$f" "pg0_invalid/${f%.txt}_pg0.txt"        # keep the original for the diff table
  # Only rows whose size is the 4GB background transfer change pg; incast rows untouched.
  awk 'NR==1{print; next} { if ($5 >= 1000000000 && $3 == 0) $3 = 3; print }' "$f" > /tmp/nf && mv /tmp/nf "$f"
  n=$(awk 'NR>1 && $3==0 {c++} END{print c+0}' "$f")
  m=$(awk 'NR>1 && $5>=1000000000 {printf "%s ", $3}' "$f")
  printf "  %-14s pg0 remaining=%s   background pg now: %s\n" "$f" "$n" "$m"
done
echo
echo "=== motivation flow files too ==="
cd motivation
for f in m2_flow.txt m3_flow.txt; do
  awk 'NR==1{print; next} { if ($5 >= 1000000000 && $3 == 0) $3 = 3; print }' "$f" > /tmp/nf && mv /tmp/nf "$f"
  printf "  %-14s background pg now: %s\n" "$f" "$(awk 'NR>1 && $5>=1000000000 {print $3}' "$f")"
done
echo
echo "=== verify: incast rows unchanged, sizes unchanged, row counts unchanged ==="
cd ..
for f in s3_flow.txt s4_flow.txt; do
  old=pg0_invalid/${f%.txt}_pg0.txt
  echo "  $f vs original:"
  diff <(awk '{print NF, $1, $2, $4, $5, $6}' "$old") <(awk '{print NF, $1, $2, $4, $5, $6}' "$f") >/dev/null \
    && echo "    everything except pg is byte-identical" || echo "    OTHER FIELDS CHANGED - investigate"
  echo "    changed lines: $(diff "$old" "$f" | grep -c '^[<>]') (expect 2: the one bg row, old+new)"
done
