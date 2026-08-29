cd /work/simulation/experiment/scheme1_sba
python3 qc_preflight_report.py 2>&1
echo
echo "##################### OVERSHOOT LEDGER #####################"
python3 qc_overshoot_ledger.py 2>&1
