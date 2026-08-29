set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== how the FROZEN matrix aligns flow start vs release hint ==="
awk 'NR==3{printf "  frozen s3 incast start   = %s s\n", $6}' s3_flow.txt
awk 'NR==3{printf "  frozen s3 release hint   = %s ns = %.1f s\n", $9, $9/1e9}' s3_round_schedule.txt
echo "  -> flows start at 1.9 s, hint is 2.0 s: registration precedes the hint."
echo
cd motivation
echo "=== realign M1/M2/M3 incast start 2.0 -> 1.9 s to satisfy the assertion ==="
for f in m1_flow.txt m2_flow.txt m3_flow.txt; do
  sed -i 's/ 2\.0$/ 1.9/' $f
  n=$(awk 'NR>1 && $6=="1.9"{c++} END{print c+0}' $f)
  echo "  $f: $n incast rows now start at 1.9 s"
done
echo "=== M1 needs its own schedule: 16 flows, no background ==="
{ echo 16
  for i in $(seq 0 15); do echo "$i 0 1 16 262144 0 0 0 2000000000"; done
} > m1_round_schedule.txt
head -2 m1_round_schedule.txt | sed 's/^/  /'
for a in dcqcn dctcp timely; do
  sed -i "s|^ROUND_SCHEDULE_FILE .*|ROUND_SCHEDULE_FILE m1_round_schedule.txt|" m1_${a}.txt
done
echo "  m1 configs now point at m1_round_schedule.txt"
echo "=== M2/M3 keep the frozen 64-flow schedules (s3/s4) which match their shape ==="
grep -h "^ROUND_SCHEDULE_FILE" m2_dcqcn.txt m3_dcqcn.txt | sed 's/^/  /'
