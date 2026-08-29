cd /work && python3 fixhys.py
cd /work/simulation/experiment/scheme1_sba && python3 controller_trace_replay.py 2>&1 | tail -32
