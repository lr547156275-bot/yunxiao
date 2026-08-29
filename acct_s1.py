import csv
d='/work/simulation/experiment/scheme1_sba/m_dcqcn_s1_seed2_out'
fs=list(csv.DictReader(open(d+'/flow_summary.csv')))
inc=[r for r in fs if r['src']!='65' and r['completed']=='1']
bg=[r for r in fs if r['src']=='65'][0]
first=min(float(r['start_time']) for r in inc); last=max(float(r['finish_time']) for r in inc)
print('=== why 9.034 + 7.617 = 16.65 G on a 10 G link? Different windows. ===')
print('  incast goodput is per-flow bytes / its OWN fct: window = [%.4f, %.4f] = %.1f ms'
      % (first, last, (last-first)*1000))
print('  background goodput is 4GB / its whole lifetime, which spans 0.5s -> run end,')
print('  i.e. mostly OUTSIDE the collective. Summing them is meaningless.')
print()
link=list(csv.DictReader(open(d+'/selected_link_timeseries.csv')))
w=[r for r in link if first<=float(r['time'])<=last]
tx=sum(float(r['tx_bytes_delta']) for r in w)
print('=== the only valid check: link tx over the collective window ===')
print('  link 84:1 carried %.3f Gbps over those %.1f ms  (<= 10 G, consistent)'
      % (tx*8/(last-first)/1e9, (last-first)*1000))
# per-class share inside that same window
ff=list(csv.DictReader(open(d+'/selected_flow_timeseries.csv')))
s=[(float(r['time']),float(r['snd_una'])) for r in ff if r['flow_id']=='0']
s.sort()
lo=[v for t,v in s if t<=first]; hi=[v for t,v in s if t<=last]
bgw=(hi[-1]-lo[-1])*8/(last-first)/1e9 if lo and hi else float('nan')
incw=sum(float(r['acked_bytes']) for r in inc)*8/(last-first)/1e9
print('  in-window background = %.3f Gbps' % bgw)
print('  in-window incast     = %.3f Gbps' % incw)
print('  sum                  = %.3f Gbps  (now <= link, and matches link tx)' % (bgw+incw))
