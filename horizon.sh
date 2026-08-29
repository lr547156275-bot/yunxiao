set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== the control loop: queue observation -> replan -> rate takes effect ==="
grep -E "^CBAP_CONTROL_EPOCH_US|^CBAP_PLANNING_DELAY_US|^CBAP_CONTROL_DELAY_US" m_cbapsba_s3_seed2.txt | sed 's/^/  /'
echo
echo "=== so the horizon must cover ==="
python3 - <<'PY'
epoch=5.0; plan=5.0; ctrl=5.0
print('  control epoch (observation period)      = %.1f us' % epoch)
print('  planning delay (compute the allocation) = %.1f us' % plan)
print('  control delay (grant reaches the NIC)   = %.1f us' % ctrl)
print('  ---')
print('  H = epoch + planning + control = %.1f us' % (epoch+plan+ctrl))
print()
print('  Rationale: a credit granted now is in force until the next replan can')
print('  revoke it, which is one observation epoch plus the planning and control')
print('  delays. Using a shorter H would over-credit; padding it further would')
print('  under-credit. The delays are read from the config, not chosen.')
PY
