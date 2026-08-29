set -u
cd /work/simulation/experiment/scheme1_sba
M=motivation
# Derive every motivation config from the FINAL frozen scenario configs so the
# ECN/PFC parameters, delays and telemetry settings are provably identical.
# CBAP is disabled throughout: these experiments characterise existing CC only.
gen() {
  local base=$1 exp=$2 algo=$3 stop=$4 flow=$5 bgcap=$6 bgflow=$7
  local cc; case $algo in dcqcn) cc=1;; dctcp) cc=8;; timely) cc=7;; hpcc) cc=3;; esac
  local name=${exp}_${algo}
  local out=${name}_out
  mkdir -p $M/$out
  awk -v cc="$cc" -v algo="$algo" -v stop="$stop" \
      -v stopns="$(awk -v s=$stop 'BEGIN{printf "%d", s*1e9}')" \
      -v out="$out" -v flow="$flow" -v bgcap="$bgcap" -v bgflow="$bgflow" -v tag="$base" '
    NF==0 { next }
    $1=="CC_MODE"                    { print "CC_MODE " cc; next }
    $1=="CBAP_ENABLE"                { print "CBAP_ENABLE 0"; next }
    $1=="SIM_SEED"                   { print "SIM_SEED 2"; next }
    $1=="ALGORITHM"                  { print "ALGORITHM " algo; next }
    $1=="SCENARIO"                   { print "SCENARIO " out; next }
    $1=="SIMULATOR_STOP_TIME"        { print "SIMULATOR_STOP_TIME " stop; next }
    $1=="QLEN_MON_END"               { print "QLEN_MON_END " stopns; next }
    $1=="FLOW_FILE"                  { print "FLOW_FILE " flow; next }
    $1=="APP_RATE_CAP_BPS"           { if (bgcap!="none") print "APP_RATE_CAP_BPS " bgcap; next }
    $1=="APP_RATE_CAP_FLOW"          { if (bgflow!="none") print "APP_RATE_CAP_FLOW " bgflow; next }
    $1=="ROUND_TRACE_SELECTED_FLOWS" { print "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3"; next }
    $1=="CBAP_MIGRATION_ENABLE"      { next }
    $1=="CBAP_MIGRATION_TRACE"       { next }
    $1=="CBAP_ETA_FEASIBILITY_TRACE" { next }
    $1=="CBAP_ETA_FEASIBILITY_FILE"  { next }
    $1=="APP_CAP_TRACE"              { next }
    { gsub(tag "_out/", out "/"); print }
  ' ${base}_config.txt > $M/${name}.txt
  # outputs live under motivation/, and inputs are one level up
  sed -i "s|^TOPOLOGY_FILE .*|TOPOLOGY_FILE topology.txt|" $M/${name}.txt
  sed -i "s|^FLOW_FILE .*|FLOW_FILE ${flow}|" $M/${name}.txt
  echo "  wrote $M/${name}.txt (cc_mode=$cc stop=$stop flow=$flow bgcap=$bgcap)"
}
# M1: 16-way, no background -> derive from s1, drop the rate cap entirely
for a in dcqcn dctcp timely; do gen s1 m1 $a 2.4 m1_flow.txt none none; done
# M2: 64-way 1MiB + background 8G  -> derive from s3
for a in dcqcn hpcc; do gen s3 m2 $a 3.2 m2_flow.txt 8000000000 0; done
# M3: 64-way 1MiB + background 9.5G -> derive from s4
for a in dcqcn hpcc; do gen s4 m3 $a 5.5 m3_flow.txt 9500000000 0; done
echo "=== M1 must have NO background cap keys ==="
grep -c "APP_RATE_CAP" $M/m1_dcqcn.txt | sed 's/^/  m1 cap keys: /'
grep -E "^APP_RATE_CAP" $M/m2_dcqcn.txt | sed 's/^/  m2: /'
grep -E "^APP_RATE_CAP" $M/m3_dcqcn.txt | sed 's/^/  m3: /'
echo "=== ECN/PFC inherited unchanged? (compare against the frozen s3 config) ==="
for k in KMIN_MAP KMAX_MAP PMAX_MAP PAUSE_TIME BUFFER_SIZE MIN_RATE RATE_AI EWMA_GAIN ENABLE_QCN; do
  a=$(grep "^$k " s3_config.txt | head -1); b=$(grep "^$k " $M/m2_dcqcn.txt | head -1)
  [ "$a" = "$b" ] && echo "  OK   $k" || echo "  DIFF $k: final[$a] vs m2[$b]"
done
