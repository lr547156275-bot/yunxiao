cd /work/simulation
echo "=== how delayCreditEnable is pushed into config ==="
grep -n "delayCreditEnable\|delay_credit_enable" scratch/third.cc
echo
echo "=== did the globals/keys from the last patch land? ==="
grep -c "cbap_queue_controller_enable" scratch/third.cc
grep -n "CBAP_QUEUE_CONTROLLER_ENABLE" scratch/third.cc
