set -u
cd /work/simulation/experiment/scheme1_sba/motivation
echo "=== Q1a: does the background flow get an app rate cap (would make it CBR-like)? ==="
grep -E "^APP_RATE_CAP_FLOW|^APP_RATE_CAP_BPS|^ENABLE_QCN|^CC_MODE|^CBAP_ENABLE" m2_dcqcn.txt | sed 's/^/  /'
echo
echo "=== Q1b: flow table -- priority group of each class ==="
awk 'NR>1{printf "  src=%-3s dst=%-3s pg=%s size=%-11s start=%s%s\n", $1,$2,$3,$5,$6,($1==65?"   <-- BACKGROUND":"")}' m2_flow.txt | head -3
echo "  ... incast rows all pg=3"
awk 'NR>1 && $1!=65 {p[$3]=1} END{printf "  distinct incast pg: "; for(k in p) printf "%s ", k; print ""}' m2_flow.txt
echo
echo "=== Q1c: is the background pg=0 lane ECN-eligible? KMIN/KMAX map is per (pg? rate?) ==="
grep -E "^KMIN_MAP|^KMAX_MAP|^PMAX_MAP" m2_dcqcn.txt | sed 's/^/  /'
echo "  (format: <count> <rate_bps> <value> -- keyed by LINK RATE, not by pg)"
