import csv, os
D='/work/simulation/experiment/scheme1_sba/motivation/m2_dcqcn_out'
fsum=list(csv.DictReader(open(os.path.join(D,'flow_summary.csv'))))
link=list(csv.DictReader(open(os.path.join(D,'selected_link_timeseries.csv'))))
REL=1.9
last=max(float(r['finish_time']) for r in fsum if r['src']!='65' and r['completed']=='1')

print('=== Q5: why per-flow sum (9.047) < link tx (9.482) over [1.9, %.4f] ===' % last)
print('  a) link tx_bytes_delta counts WIRE bytes: headers + ACK/CNP traffic,')
print('     while acked_bytes / snd_una count PAYLOAD only.')
# quantify the header overhead
inc=[r for r in fsum if r['src']!='65' and r['completed']=='1']
payload=sum(float(r['acked_bytes']) for r in inc)
# packet count estimate at 1000B MTU payload
mtu=1000
pkts=payload/mtu
hdr=pkts*(14+20+16+4)   # eth + ip + udp/BTH-ish + crc, order-of-magnitude
print('     incast payload=%.3f GB -> ~%.0f pkts -> ~%.3f GB header overhead (%.1f%%)'
      % (payload/1e9, pkts, hdr/1e9, hdr/payload*100))
print('  b) the background flow does not finish, so its window-edge sampling is')
print('     bounded by the 10us trace interval, not exact byte counts.')
print()
print('=== Q6: corrected theoretical bounds for 64-way 1MiB incast on 10 Gbps ===')
msg=1048576; n=64; C=10e9
print('  single 1 MiB flow alone on the link        : %.3f ms   <-- NOT a valid 64-way reference' % (msg*8/C*1000))
print('  64-way, no background, link-limited        : %.3f ms' % (n*msg*8/C*1000))
bg=7.641e9
print('  64-way with background holding %.3f Gbps  : %.3f ms' % (bg/1e9, n*msg*8/(C-bg)*1000))
print()
obs=sum(float(r['fct']) for r in inc)/len(inc)*1000
print('  observed DCQCN mean incast FCT             : %.3f ms' % obs)
print('  vs 64-way no-background bound  : %.2fx' % (obs/(n*msg*8/C*1000)))
print('  vs residual-capacity bound     : %.2fx' % (obs/(n*msg*8/(C-bg)*1000)))
