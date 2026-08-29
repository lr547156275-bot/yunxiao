cd /work/simulation
sed -n '735,745p' scratch/third.cc
echo "---- globals near cbap_priority / file vars ----"
grep -nE "^uint32_t cbap_priority|^string cbap_port_summary_file|^static .*cbap_.*_file" scratch/third.cc | head -6
