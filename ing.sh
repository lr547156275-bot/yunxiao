cd /work/simulation
echo "=== which ingress ports actually feed the bottleneck egress? ==="
echo "  bottleneck = link 0 = node 84 if 1 -> faces node 64"
echo "  topology at 84: hosts 64,65,66,67 on ifs 1..4 ; uplinks 85,86,87,88 on ifs 5..8"
echo
echo "=== incast sources: which hosts? ==="
awk 'NR>1 && $3==3 {print $1}' experiment/scheme1_sba/s3_flow.txt | sort -n | uniq -c | head -5
echo "  distinct srcs: $(awk 'NR>1{print $1}' experiment/scheme1_sba/s3_flow.txt | sort -un | tr '\n' ' ' | head -c 200)"
echo
echo "=== so traffic enters 84 via which ports? check the path file ==="
f=$(grep -h "^CBAP_PATH_FILE" experiment/scheme1_sba/au_s3_rho055.txt | awk '{print $2}'); echo "  path file: $f"
head -3 experiment/scheme1_sba/$f
echo
echo "=== does SwitchNode expose an ingress->egress mapping? ==="
grep -nE "GetRxBytes|m_devices|GetNDevices" src/point-to-point/model/switch-node.h | head
