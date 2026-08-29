cd /work && python3 fixpre.py
cd /work/simulation/experiment/scheme1_sba
python3 inst_check.py 2>/dev/null || true
python3 /work/inst.py 2>&1 | head -14
echo "=== replay ==="
python3 controller_trace_replay.py 2>&1 | tail -26
