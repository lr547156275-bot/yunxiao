set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== biggest consumers ==="
du -sh m_*_out f_*_out g_*_out 2>/dev/null | sort -rh | head -8
echo "=== total in old output dirs ==="
du -csh m_*_out 2>/dev/null | tail -1 | sed 's/^/  m_*_out: /'
du -csh f_*_out g_*_out 2>/dev/null | tail -1 | sed 's/^/  f_/g_*_out: /'
echo "=== what dominates one cell ==="
du -sh m_cbapsba_s5_seed2_out/* 2>/dev/null | sort -rh | head -4
echo
echo "=== free space ==="
df -h /work | tail -1
