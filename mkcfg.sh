set -u
cd /work/simulation/experiment/scheme1_sba
# Build S3 and S4 configs for the feasibility build: identical to the main-matrix
# cbapsba cells except the output dir, so the ONLY difference from the frozen
# results is the algorithm change itself.
for tag in s3 s4; do
  case $tag in
    s3) STOP=3.0; STOPNS=3000000000 ;;
    s4) STOP=5.5; STOPNS=5500000000 ;;
  esac
  name=f_cbapsba_${tag}_seed2
  out=${name}_out
  mkdir -p "$out"
  awk -v stop="$STOP" -v stopns="$STOPNS" -v out="$out" -v tag="$tag" '
    NF==0 { next }
    $1=="CC_MODE"                    { print "CC_MODE 30"; next }
    $1=="CBAP_ENABLE"                { print "CBAP_ENABLE 1"; next }
    $1=="SIM_SEED"                   { print "SIM_SEED 2"; next }
    $1=="ALGORITHM"                  { print "ALGORITHM cbapsba"; next }
    $1=="SIMULATOR_STOP_TIME"        { print "SIMULATOR_STOP_TIME " stop; next }
    $1=="QLEN_MON_END"               { print "QLEN_MON_END " stopns; next }
    $1=="ROUND_TRACE_SELECTED_FLOWS" { print "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3"; next }
    $1=="CBAP_MIGRATION_ENABLE"      { next }
    $1=="CBAP_MIGRATION_TRACE"       { next }
    $1=="CBAP_MIGRATION_RELEASE_RATIO" { next }
    $1=="APP_CAP_TRACE"              { next }
    { gsub(tag "_out/", out "/"); print }
  ' ${tag}_config.txt > ${name}.txt
  echo "CBAP_MIGRATION_ENABLE 1" >> ${name}.txt
  echo "CBAP_MIGRATION_TRACE 0"  >> ${name}.txt
  # eta_base stays at the compiled default 0.5 -- deliberately NOT set, so the
  # only thing that can raise eta is the feasibility floor.
  echo "  wrote ${name}.txt (eta_base = default 0.5)"
  # Prove it differs from the frozen matrix config only in the output dir.
  diff <(sed "s|${out}/|m_cbapsba_${tag}_seed2_out/|g" ${name}.txt) m_cbapsba_${tag}_seed2.txt > /tmp/d_${tag}.txt 2>&1
  n=$(grep -c '^[<>]' /tmp/d_${tag}.txt || true)
  echo "    lines differing from the frozen matrix config: $n (0 = identical parameters)"
done
