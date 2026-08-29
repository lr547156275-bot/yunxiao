set -u
cd /work/simulation/experiment/scheme1_sba/paper_data
echo "=== speedup vs baselines (ratio >1 = CBAP-SBA faster) ==="
awk -F, 'NR>3{printf "  %-3s %-7s ratio=%-8s faster=%s\n", $1,$2,$5,$6}' p6_speedup_vs_baselines.csv
echo
echo "=== before/after: the metrics that moved most ==="
awk -F, 'NR>4 && ($2=="queue_p99_bytes"||$2=="ecn_marks"||$2=="fct_p99_ms"||$2=="bg_retention_pct"){printf "  %-3s %-20s %14s -> %14s  %8s%%\n",$1,$2,$3,$4,$5}' p5_capacity_feasibility_before_after.csv
