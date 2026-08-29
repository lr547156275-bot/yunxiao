cd /work/simulation/experiment/scheme1_sba
echo "remote replay sha: $(sha256sum controller_trace_replay.py|cut -c1-12)"
python3 controller_trace_replay.py 2>&1
