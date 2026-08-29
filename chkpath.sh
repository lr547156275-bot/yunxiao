set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== hosts on leaf 84 ==="
awk 'NR>2 && $2==84 && $1<68 {printf "  host %s\n", $1}' topology.txt
echo
echo "=== the bottleneck link 84:1 is leaf84 -> which node? ==="
awk 'NR>2 && $1==84 {print "  84 -- " $2}' topology.txt | head -5
echo
echo "=== H65->H66 path: both on leaf 84 => leaf-local, never crosses 84:1 into H64 ==="
echo "=== how did the FINAL matrix create background contention? (S3 flow file) ==="
awk 'NR==2{printf "  final S3 background: src=%s dst=%s  (dst is the SAME receiver as the incast)\n", $1, $2}' s3_flow.txt
awk 'NR==3{printf "  final S3 incast   : src=%s dst=%s\n", $1, $2}' s3_flow.txt
echo
echo "=== so contention requires the background to target H64 as well ==="
