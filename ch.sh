cd /work/simulation
echo "=== CustomHeader udp fields (seq available at the switch?) ==="
grep -nE "struct.*udp|uint32_t seq|uint16_t sport|uint16_t dport|uint8_t pg" src/point-to-point/model/custom-header.h | head -12
echo
echo "=== how does third.cc already peek a CustomHeader at the bottleneck? ==="
grep -nE "CustomHeader ch|ch.udp.seq|PeekCustomHeader|ch.getInt" scratch/third.cc | head -8
echo
echo "=== QbbEnqueue gives (packet,qIndex): can I parse a CustomHeader from the packet? ==="
grep -rn "CustomHeader ch;" src/point-to-point/model/switch-node.cc | head -3
sed -n '/void SwitchNode::SwitchReceiveFromDevice/,/+5/p' src/point-to-point/model/switch-node.cc | head -8
