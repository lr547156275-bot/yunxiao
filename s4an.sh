cd /work/simulation/experiment/scheme1_sba
python3 core_analyse.py cr_s4_rho040 0.4 2>&1
echo
echo "=== S4 eta trace: handover row + tail ==="
head -2 cr_s4_rho040_out/eta_feasibility.csv | tail -1
echo "  (last)"; tail -1 cr_s4_rho040_out/eta_feasibility.csv
