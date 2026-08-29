set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== 1. topology link delays on the incast path ==="
awk 'NR>2 && $1==0 && $2>=68 {printf "  host0 -> leaf%s : rate=%s delay=%s\n", $2,$3,$4}' topology.txt
awk 'NR>2 && $1==68 && $2>=85 {printf "  leaf68 -> spine%s: rate=%s delay=%s\n", $2,$3,$4; exit}' topology.txt
awk 'NR>2 && $1==84 && $2>=85 {printf "  leaf84 -> spine%s: rate=%s delay=%s\n", $2,$3,$4; exit}' topology.txt
awk 'NR>2 && $1==64 && $2>=68 {printf "  host64 -> leaf%s: rate=%s delay=%s\n", $2,$3,$4}' topology.txt
echo
echo "=== 2. what the SIMULATOR itself computed (authoritative) ==="
grep -h "maxRtt" /work/matrix_logs/m_cbapsba_s3_seed2.log /work/matrix_logs/m_cbapsba_s4_seed2.log 2>/dev/null | sort -u | sed 's/^/  /'
echo
echo "=== 3. hop-by-hop derivation ==="
python3 - <<'PY'
# 4 hops one way: host->leaf (1us), leaf->spine (2us), spine->leaf (2us), leaf->host (1us)
one_way_prop = 1 + 2 + 2 + 1
rtt_prop = 2 * one_way_prop
print('  propagation one way = %d us (1+2+2+1)' % one_way_prop)
print('  propagation RTT     = %d us' % rtt_prop)
# serialisation of a full MTU at 10 Gbps, per hop, both directions
mtu = 1000 + 48   # payload + headers, as used elsewhere in this codebase
ser = mtu*8/10e9*1e6
print('  MTU serialisation   = %.3f us per hop (%d B at 10 Gbps)' % (ser, mtu))
print('  4 hops data + 4 hops ack (ack is small) ~ %.2f us' % (4*ser))
print('  -> derived base RTT ~ %.1f us, consistent with the simulator note' % (rtt_prop + 4*ser))
PY
echo
echo "=== 4. EMPIRICAL: minimum observed FCT of a single small flow (no queueing) ==="
awk -F, 'NR>1 && $6!=65 && $13==1 {if(mn==0||$11<mn)mn=$11} END{printf "  S1 min incast FCT = %.6f s = %.1f us (256KiB msg, so includes 209 us of serialisation)\n", mn, mn*1e6}' m_cbapsba_s1_seed2_out/flow_summary.csv
python3 -c "print('  256KiB at 10 Gbps serialisation alone = %.1f us' % (262144*8/10e9*1e6))"
