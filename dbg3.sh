cd /work/simulation
echo "=== where is crfm.flowId ASSIGNED? ==="
grep -rnE "crfm\.flowId *=" src/point-to-point/model/*.cc scratch/third.cc | head
echo
echo "=== default value of crfm.flowId ==="
grep -rn -B2 -A2 "flowId" src/point-to-point/model/rdma-queue-pair.h | grep -A3 -B3 "crfm\|Crfm" | head -20
echo
echo "=== is flow 0 (bg) registered as a CBAP flow at all? ==="
awk -F, 'NR>1 && $2==0 {print "  sba_events flow 0: batch="$1" transition="$8; exit}' experiment/scheme1_sba/au_s3_rho055_out/sba_events.csv
echo
echo "=== HOW MANY rate commands went to non-zero flows? (all four cells) ==="
for t in 055 075 090 09875; do
  printf "  rho=%-7s " $t
  awk -F, 'NR>1{c[$2]++} END{n=0; for(f in c) if(f!=0) n+=c[f]; printf "flow0=%d others=%d distinct=%d\n", c[0]+0, n, length(c)}' experiment/scheme1_sba/au_s3_rho${t}_out/actuation.csv
done
