set -u
cd /work/simulation/experiment/scheme1_sba
export LD_LIBRARY_PATH=/work/simulation/build
name=a_cbapsba_s3_migoff_seed2
out=${name}_out
mkdir -p "$out"
# Identical to the frozen S3 CBAP-SBA cell except CBAP_MIGRATION_ENABLE 0.
sed "s|m_cbapsba_s3_seed2_out/|${out}/|g" m_cbapsba_s3_seed2.txt \
  | sed "s|^CBAP_MIGRATION_ENABLE 1$|CBAP_MIGRATION_ENABLE 0|" \
  | grep -v "^CBAP_ETA_FEASIBILITY_FILE" > ${name}.txt
echo "CBAP_ETA_FEASIBILITY_FILE ${out}/eta_feasibility.csv" >> ${name}.txt
echo "=== proof that ONLY the migration flag differs ==="
diff <(sed "s|${out}/|m_cbapsba_s3_seed2_out/|g" ${name}.txt | sort) \
     <(sort m_cbapsba_s3_seed2.txt) | grep '^[<>]' | sed 's/^/  /'
n=$(diff <(sed "s|${out}/|m_cbapsba_s3_seed2_out/|g" ${name}.txt | sort) <(sort m_cbapsba_s3_seed2.txt) | grep -c '^[<>]')
echo "  differing lines: $n (expect 2: the flag value old/new)"
echo
echo "=== run ==="
t0=$(date +%s)
timeout --kill-after=60 14400 /work/simulation/build/scratch/third "${name}.txt" > /work/matrix_logs/${name}.log 2>&1
code=$?
t1=$(date +%s)
got=$(awk -F, 'NR>1 && $6!=65 && $13==1 {c++} END{print c+0}' ${out}/flow_summary.csv 2>/dev/null || echo 0)
last=$(awk -F, 'NR>1{t=$1} END{printf "%.4f", t+0}' ${out}/selected_link_timeseries.csv 2>/dev/null || echo 0)
echo "  exit=$code incast=$got/64 last_trace_t=$last wall=$((t1-t0))s"
echo "  eta trace rows: $(awk 'END{print NR-1}' ${out}/eta_feasibility.csv 2>/dev/null || echo 'file absent')"
