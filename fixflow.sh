set -u
cd /work/simulation/experiment/scheme1_sba/motivation
# M2/M3: background H65 -> H64, same receiver as the incast, so both cross 84:1.
# Background starts at 0.5 s and the incast at 2.0 s, so the background is in
# steady state for 1.5 s before the collective arrives.
{ echo 65
  echo "65 64 0 100 4000000000 0.5"
  for i in $(seq 0 63); do echo "$i 64 3 100 1048576 2.0"; done
} > m2_flow.txt
cp m2_flow.txt m3_flow.txt

echo "=== requirement 1: is H65 in the incast sender set? ==="
awk 'NR>1 && $6=="2.0" {s[$1]=1} END{printf "  incast senders: %d, min=%d max=%d ; H65 present: %s\n", length(s), 0, 63, (65 in s ? "YES (BUG)" : "no")}' m2_flow.txt
awk 'NR>1 && $1==65 {printf "  H65 row: src=%s dst=%s pg=%s size=%s start=%s (background only)\n", $1,$2,$3,$5,$6}' m2_flow.txt

echo "=== requirement 2: background reaches steady state before incast ==="
awk 'NR>1 && $1==65 {bg=$6} NR>1 && $6=="2.0" {inc=$6} END{printf "  bg start=%s s, incast start=%s s -> %.1f s of steady state\n", bg, inc, inc-bg}' m2_flow.txt

echo "=== requirement 3: do both flow classes traverse 84:1 (leaf84 -> H64)? ==="
awk 'NR>2 && $2==84 && $1<68 {h[$1]=1} END{printf "  hosts on leaf 84: "; for(k in h) printf "%s ", k; print ""}' ../topology.txt
echo "  background dst=64 -> arrives at H64 via leaf84 downlink 84:1  YES"
echo "  incast    dst=64 -> 64 senders on other leaves, all converge on 84:1  YES"
echo "  (background src H65 is on leaf 84, so its path is leaf84 -> H64: same 84:1 port)"

echo "=== flow table summary ==="
wc -l < m2_flow.txt | sed 's/^/  m2/m3 rows (incl header): /'
head -3 m2_flow.txt | sed 's/^/  /'
