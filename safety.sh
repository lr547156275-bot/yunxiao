set -u
cd /work/simulation/experiment/scheme1_sba/paper_data_pg3
python3 - <<'PY'
import csv
rows=[r for r in csv.DictReader(open('final_results_pg3.csv'))]
print('=== safety across all 30 cells ===')
for k in ('pfc_events','drops','retx_bytes_total','retx_events_total'):
    tot=0
    for r in rows:
        try: tot+=float(r[k])
        except: pass
    print('  %-22s total = %.0f' % (k, tot))
print()
print('=== ECN for S4/S5 (cut off earlier) ===')
for t in ('s4','s5'):
    line='  %-4s' % t.upper()
    for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
        v=[r for r in rows if r['scenario_tag']==t and r['algorithm']==a]
        line += '%11.0f' % float(v[0]['ecn_marks']) if v else '%11s'%'-'
    print(line)
print()
print('=== CBAP-SBA: FCT penalty vs the FASTEST baseline, per scenario ===')
for t in ('s1','s2','s3','s6','s4','s5'):
    c=[r for r in rows if r['scenario_tag']==t and r['algorithm']=='cbapsba'][0]
    bl=[float(r['fct_p99_ms']) for r in rows if r['scenario_tag']==t and r['algorithm']!='cbapsba']
    print('  %-4s CBAP %8.3f ms vs best baseline %8.3f ms  -> %.2fx slower'
          % (t.upper(), float(c['fct_p99_ms']), min(bl), float(c['fct_p99_ms'])/min(bl)))
PY
