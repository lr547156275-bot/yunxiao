import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# 1) CSV header for the new schema
old_hdr='''				"time_ns,flow_id,rate_bps,bytes,stage,"
				"delta_prev_stage_ns,delta_from_command_ns''' + NL + '''");'''
assert src.count(old_hdr)==1, src.count(old_hdr)
src=src.replace(old_hdr,'''				"time_ns,generation,flow_id,old_rate_bps,rate_bps,stage,"
				"delta_prev_stage_ns,delta_from_command_ns,seq''' + NL + '''");''')

# 2) connect block: bottleneck is a SWITCH trace (EgressDequeue), not QbbEnqueue
old_bl=src[src.index('''	if (!cbap_actuation_file.empty() && !cbap_links.empty()){'''):
           src.index('''		RdmaHw::StartCbapCoordinator();''')]
new_bl = '''	if (!cbap_actuation_file.empty() && !cbap_links.empty()){
		// Bottleneck egress identity, so stage 3 only matches the controlled
		// port.  Taken from the first configured CBAP link.
		map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator bl =
			cbap_link_by_id.begin();
		if (bl != cbap_link_by_id.end() && bl->second.nodeId < n.GetN()){
			Ptr<SwitchNode> bsw = DynamicCast<SwitchNode>(
				n.Get(bl->second.nodeId));
			if (bsw){
				cbap_actuation_egress_valid = true;
				cbap_actuation_egress_if = bl->second.ifIndex;
				bsw->TraceConnectWithoutContext("EgressDequeue",
					MakeCallback(&CbapActuationAtBottleneck));
			}
		}
		// Every host QP dequeue, so the commanded flow's departure is seen
		// wherever it lives.
		for (uint32_t nodeId = 0; nodeId < n.GetN(); ++nodeId){
			if (n.Get(nodeId)->GetNodeType() != 0)
				continue;
			for (uint32_t deviceId = 1;
					deviceId < n.Get(nodeId)->GetNDevices(); ++deviceId){
				Ptr<QbbNetDevice> hdev = DynamicCast<QbbNetDevice>(
					n.Get(nodeId)->GetDevice(deviceId));
				if (hdev)
					hdev->TraceConnectWithoutContext("RdmaQpDequeue",
						MakeBoundCallback(&CbapActuationOnQpDequeue, hdev));
			}
		}
	}
'''
src=src.replace(old_bl, new_bl)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("connect block updated; EgressDequeue connects:",
      src.count("&CbapActuationAtBottleneck"),
      "| QpDequeue:", src.count("&CbapActuationOnQpDequeue"))
