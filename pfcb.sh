cd /work/simulation/src/point-to-point/model
echo "=== where does CBAP read queueBytes from? ==="
grep -nE "queueBytes *=|latest\.queueBytes" rdma-hw.cc | head -8
echo
echo "=== and third.cc telemetry: which queue does it sample? ==="
grep -nE "GetQueueLength|GetNBytes|queue_bytes|GetQueue\(\)" /work/simulation/scratch/third.cc | head -12
echo
echo "=== switch-node: pause/resume call sites and which port ==="
grep -nE "CheckShouldPause|CheckShouldResume|SetPause|SendPfc|UpdateIngressAdmission|UpdateEgressAdmission" switch-node.cc
echo
echo "=== pfc_a_shift default ==="
grep -rnE "pfc_a_shift" switch-mmu.cc switch-mmu.h /work/simulation/scratch/third.cc | head
