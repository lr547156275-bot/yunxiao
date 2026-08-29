set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
echo "=== flag-OFF reproduction test (item 8: must reproduce old results) ==="
echo "  rerunning au_s3_rho090 with the controller build but flag=0"
grep -c "^CBAP_QUEUE_CONTROLLER_ENABLE" au_s3_rho090.txt || echo "  (key absent -> defaults to 0)"
cp -a au_s3_rho090_out/flow_summary.csv /tmp/ref_flow_summary.csv
timeout --kill-after=60 14400 /work/simulation/build/scratch/third au_s3_rho090.txt \
  > /work/matrix_logs/inert_check.log 2>&1
echo "  exit=$?"
echo "  md5 before: $(md5sum /tmp/ref_flow_summary.csv | cut -d' ' -f1)"
echo "  md5 after : $(md5sum au_s3_rho090_out/flow_summary.csv | cut -d' ' -f1)"
if [ "$(md5sum < /tmp/ref_flow_summary.csv)" = "$(md5sum < au_s3_rho090_out/flow_summary.csv)" ]; then
  echo "  RESULT: IDENTICAL -- flag-off path is inert"
else
  echo "  RESULT: DIFFERS -- flag-off is NOT inert, investigate"
  diff <(head -3 /tmp/ref_flow_summary.csv) <(head -3 au_s3_rho090_out/flow_summary.csv) | head
fi
echo "INERT_DONE"
