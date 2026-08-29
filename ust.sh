cd /work/simulation/experiment/scheme1_sba
echo "=== unit tests must still pass against the NEW signed law ==="
python3 controller_state_machine_test.py 2>&1 | tail -6
