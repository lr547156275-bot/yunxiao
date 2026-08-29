import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# connect the arrival observer to the bottleneck DEVICE's QbbEnqueue
a='''				bsw->TraceConnectWithoutContext("EgressDequeue",
					MakeCallback(&CbapActuationAtBottleneck));'''
assert src.count(a)==1
src=src.replace(a, a+'''
				// Arrival side: QbbEnqueue on the bottleneck egress device
				// fires when the packet joins that queue.
				Ptr<QbbNetDevice> bdev = DynamicCast<QbbNetDevice>(
					bsw->GetDevice(bl->second.ifIndex));
				if (bdev)
					bdev->TraceConnectWithoutContext("QbbEnqueue",
						MakeCallback(&CbapActuationAtBottleneckArrival));''')

# emit the counters at the end so the gates are auditable from the trace itself
b='''void WriteCbapSummaries(){'''
assert src.count(b)==1
src=src.replace(b,'''void WriteCbapActuationCounters(){
	if (!cbap_actuation_csv)
		return;
	// Counters as a final row, so the gate values live with the data.
	fprintf(cbap_actuation_csv,
		"0,0,0,0,0,counters_unmatched_%lu_superseded_%lu_negative_%lu,0,0,0\n",
		(unsigned long)cbap_act_unmatched,
		(unsigned long)cbap_act_superseded,
		(unsigned long)cbap_act_negative);
	// Anything still in flight at the end never reached the bottleneck.
	fprintf(cbap_actuation_csv,
		"0,0,0,0,0,counters_pending_%lu_inflight_%lu,0,0,0\n",
		(unsigned long)cbap_actuation_pending.size(),
		(unsigned long)cbap_actuation_inflight.size());
	fflush(cbap_actuation_csv);
}

''' + b)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("arrival connected:", src.count("&CbapActuationAtBottleneckArrival"),
      "| counters fn:", src.count("WriteCbapActuationCounters"))
