cd /work/simulation
echo "=== parse idiom + neighbours (2890-2905) ==="
sed -n '2890,2905p' scratch/third.cc
echo
echo "=== collision check for the new key ==="
grep -c "CBAP_PFC_AUDIT_FILE" scratch/third.cc
echo
echo "=== where port_summary csv is opened/closed ==="
grep -nE "cbap_port_summary_file|port_summary_csv" scratch/third.cc | head
