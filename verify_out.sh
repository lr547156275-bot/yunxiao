set -u
cd /work/simulation/experiment/scheme1_sba/paper_data_pg3
echo "=== file sizes and row counts ==="
for f in *.csv; do
  rows=$(grep -vc '^#' "$f")
  printf "  %-42s %8s B  %3s lines(excl #)\n" "$f" "$(stat -c %s "$f")" "$rows"
done
echo
echo "=== final_results_pg3.csv: scenario coverage ==="
awk -F, 'NR>1 && $1 !~ /^#/ {c[$1]++} END{for(k in c) printf "  %s: %d cells\n", k, c[k]}' final_results_pg3.csv | sort
echo
echo "=== is it complete (30) ? ==="
awk -F, 'NR>1 && $1 !~ /^#/ {n++} END{printf "  total rows: %d\n", n}' final_results_pg3.csv
