import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
NL=chr(92)+'n'

# 1) open the two extra files alongside the existing pfc audit open
a='''	if (!cbap_pfc_audit_file.empty()){'''
assert src.count(a)==1
ins='''	if (!cbap_pfc_ports_file.empty()){
		cbap_pfc_ports_csv = fopen(cbap_pfc_ports_file.c_str(), "w");
		if (cbap_pfc_ports_csv)
			fprintf(cbap_pfc_ports_csv,
				"time_ns,link_id,ingress_port,ingress_bytes,shared_used_bytes,"
				"dynamic_pfc_threshold_bytes,pfc_slack_bytes,headroom_bytes,"
				"paused,egress_bytes,rx_bytes_total''' + NL + '''");
	}
	if (!cbap_actuation_file.empty()){
		cbap_actuation_csv = fopen(cbap_actuation_file.c_str(), "w");
		if (cbap_actuation_csv)
			fprintf(cbap_actuation_csv,
				"time_ns,flow_id,rate_bps,bytes,stage,"
				"delta_prev_stage_ns,delta_from_command_ns''' + NL + '''");
	}
'''
src=src.replace(a, ins+a)

# 2) connect the observers where the actuation hook is installed
b='''	if (!cbap_actuation_file.empty())
		RdmaHw::s_cbapActuationHook = &CbapActuationOnRateCommand;'''
assert src.count(b)==1
src=src.replace(b, b+'''
	if (cbap_actuation_csv && !cbap_links.empty()){
		// Bottleneck egress: the first CBAP-priority enqueue after a commanded
		// packet departs.  Uses the first configured CBAP link.
		map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator bl =
			cbap_link_by_id.begin();
		if (bl != cbap_link_by_id.end() &&
				bl->second.nodeId < n.GetN()){
			Ptr<QbbNetDevice> bdev = DynamicCast<QbbNetDevice>(
				n.Get(bl->second.nodeId)->GetDevice(bl->second.ifIndex));
			if (bdev)
				bdev->TraceConnectWithoutContext("QbbEnqueue",
					MakeBoundCallback(&CbapActuationOnBottleneckEnqueue,
						bdev));
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
	}''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("files opened:", src.count("cbap_pfc_ports_csv = fopen"),
      src.count("cbap_actuation_csv = fopen"),
      "| observers connected:", src.count("&CbapActuationOnBottleneckEnqueue"),
      src.count("&CbapActuationOnQpDequeue"))
