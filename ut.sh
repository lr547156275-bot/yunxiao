cd /work/simulation
echo "remote $(sha256sum src/point-to-point/model/cbap-sba.cc | cut -c1-12)  cbap-sba.cc"
echo "remote $(sha256sum experiment/scheme1_sba/core_initial_release_unit_check.py | cut -c1-12)  unit_check.py"
echo "=== new invariant present in source? ==="
grep -c "planned capacity" src/point-to-point/model/cbap-sba.cc
grep -n "CheckConservation(batchId" src/point-to-point/model/cbap-sba.cc
echo "=== unit checks ==="
cd experiment/scheme1_sba && python3 core_initial_release_unit_check.py; echo "EXIT=$?"
