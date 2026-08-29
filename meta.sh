set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== unified ECN/PFC + CBAP params (from a frozen cell config) ==="
grep -E "^(KMIN_MAP|KMAX_MAP|PMAX_MAP|PAUSE_TIME|BUFFER_SIZE|ENABLE_QCN|USE_DYNAMIC_PFC_THRESHOLD|CLAMP_TARGET_RATE|MIN_RATE|RATE_AI|RATE_HAI|RATE_DECREASE_INTERVAL|EWMA_GAIN|FAST_RECOVERY_TIMES|L2_.*|ERROR_RATE_PER_LINK|CRFM_TRACE_SAMPLE_US|QLEN_MON_START)" m_cbapsba_s3_seed2.txt | sed 's/^/  /'
echo
echo "=== CBAP-SBA specific ==="
grep -E "^CBAP_" m_cbapsba_s3_seed2.txt | sed 's/^/  /'
echo
echo "=== Qmax from the cbap link file (link_id node if rate qmax ...) ==="
cat s3_cbap_link.txt | sed 's/^/  /'
echo
echo "=== topology header + host/switch counts ==="
head -2 topology.txt | sed 's/^/  /'
