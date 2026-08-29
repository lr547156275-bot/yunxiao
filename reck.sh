cd /work/simulation/experiment/scheme1_sba
python3 core_analyse.py 2>&1 | grep -E "authority|handoff delay|R_old initial|realized rho|BCT|per-flow|^  \[|passed|R_old final|R_new final|eta_final"
