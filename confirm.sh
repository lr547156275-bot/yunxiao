set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== the flow files the matrix is reading right now ==="
for t in s1 s2 s3 s4 s5 s6; do
  printf "  %s: " "$t"
  awk 'NR>1 && $5>=1000000000 {printf "bg(src=%s dst=%s pg=%s) ", $1,$2,$3}
       NR>1 && $5<1000000000 {p[$3]=1}
       END{printf "| incast pg:"; for(k in p) printf " %s", k; print ""}' ${t}_flow.txt
done
echo "=== zero pg0 data flows remain? ==="
awk 'NR>1 && $3==0 {c++} END{print "  pg0 rows across all six: " c+0}' s1_flow.txt s2_flow.txt s3_flow.txt s4_flow.txt s5_flow.txt s6_flow.txt
