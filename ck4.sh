cd /work/simulation
echo "=== how third.cc parses the flow file ==="
grep -n "flow_input.idx\|>> flow_input" scratch/third.cc | head -12
echo
echo "=== pg field values in s3/s4 flow files ==="
for s in s1 s3 s4 s6; do
  printf "  %s: " $s
  awk 'NR>1{print $3}' experiment/scheme1_sba/${s}_flow.txt | sort -u | tr '\n' ' '
  echo
done
