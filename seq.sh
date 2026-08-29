set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
echo "libns3 : $(sha256sum /work/simulation/build/libns3.18-point-to-point-debug.so | cut -c1-16)"
echo "=== STEP 1: flag=0 bit-identical ==="
cp -a au_s3_rho090_out/flow_summary.csv /tmp/ref_fs.csv
timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
  > /work/matrix_logs/inert3.log 2>&1
echo "  exit=$?"
A=$(md5sum < /tmp/ref_fs.csv | cut -d' ' -f1)
B=$(md5sum < au_s3_rho090_out/flow_summary.csv | cut -d' ' -f1)
echo "  before=$A"
echo "  after =$B"
if [ "$A" = "$B" ]; then
  echo "  FLAG0_IDENTICAL"
else
  echo "  FLAG0_DIFFERS -- STOPPING, not running preflight"
  echo "SEQ_DONE"; exit 1
fi
echo "=== STEP 2: S3 rho=0.90 ONLY (serial, per instruction) ==="
timeout --kill-after=60 21600 /work/simulation/build/scratch/third qc_s3_rho090.txt \
  > /work/matrix_logs/qc_s3_rho090.log 2>&1
code=$?
got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' qc_s3_rho090_out/flow_summary.csv 2>/dev/null || echo 0)
echo "  exit=$code  incast=$got/64"
echo "SEQ_DONE"
