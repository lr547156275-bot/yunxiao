echo "=== any simulation running? ==="
ps -eo etime,cmd | grep "[t]hird " | head -5 || echo "  none"
echo
echo "=== controller implemented? ==="
printf "  CBAP_QUEUE_CONTROLLER_ENABLE occurrences in third.cc: "
grep -c CBAP_QUEUE_CONTROLLER_ENABLE /work/simulation/scratch/third.cc
printf "  boost/drain state machine in rdma-hw.cc: "
grep -cE "queueBoostBps|drainBps|CbapZone|ZONE_GREEN" /work/simulation/src/point-to-point/model/rdma-hw.cc
echo
echo "=== the 5 audit cells: complete? ==="
cd /work/simulation/experiment/scheme1_sba
for n in au_s3_rho055 au_s3_rho075 au_s3_rho090 au_s3_rho09875 au_s4_rho090; do
  printf "  %-16s " $n
  if [ -f ${n}_out/flow_summary.csv ]; then
    awk -F, 'NR>1 && $6!=65 && $13==1{c++} END{printf "%d/64 incast", c+0}' ${n}_out/flow_summary.csv
    printf "  actuation_rows=%s" "$(wc -l < ${n}_out/actuation.csv 2>/dev/null || echo 0)"
  else printf "MISSING"; fi
  echo
done
echo
echo "=== deliverables on disk ==="
ls -l CBAP_DYNAMIC_PFC_AND_ACTUATION_AUDIT.md CBAP_CORE_INITIAL_RELEASE_PREFLIGHT.md pending_ledger.py 2>/dev/null | awk '{printf "  %8s  %s\n", $5, $NF}'
echo
echo "=== git: nothing committed/pushed ==="
cd /work && echo "  HEAD=$(git rev-parse --short HEAD)  branch=$(git rev-parse --abbrev-ref HEAD)"
echo "  unpushed commits: $(git log --oneline origin/master..HEAD 2>/dev/null | wc -l)"
