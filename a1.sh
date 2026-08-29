set -u
cd /work/simulation/src/point-to-point/model
echo "=== what is qEcn (the base for budgetQMin/Max)? ==="
grep -n "qEcn" rdma-hw.cc | head -6 | sed 's/^/  /'
echo
echo "=== is decayFraction ever negative (which would give C_eff > C)? ==="
echo "  maxDrainRatio default = 0.20, budgetQLow=0.5, budgetQHigh=1.0 (rdma-hw.h:258-261)"
echo "  decayFraction in [0, maxDrainRatio] = [0, 0.20]  -> C_eff = C*(1-d) <= C  ALWAYS"
echo
echo "=== does ANY code path allow target sum > capacity? search for allowances ==="
grep -nE "capacity \* [0-9.]|capacity \+|> capacity|oversubscribe|allowOver|credit" rdma-hw.cc | grep -viE "record\.|row\.|audit|assert|NS_" | head -8 | sed 's/^/  /'
echo
echo "=== the hard conservation checks ==="
grep -n "NS_ASSERT_MSG" rdma-hw.cc | sed -n '1,3p' | sed 's/^/  /'
sed -n '1259,1266p' rdma-hw.cc | sed 's/^/  /'
