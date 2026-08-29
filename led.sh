cd /work/simulation/experiment/scheme1_sba
python3 pending_ledger.py 2>&1 | awk '/pending-action ledger/,0'
