cd /work/simulation/experiment/scheme1_sba
echo "remote $(sha256sum qstop_formula_audit.py|cut -c1-12)"
python3 qstop_formula_audit.py 2>&1
