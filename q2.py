# Q2: is "background CNP=0" a hardcoded H0-H63 filter, or real?
# Recompute from the raw per-flow records, keyed on actual flow/src ids.
import csv, os
D='/work/simulation/experiment/scheme1_sba/motivation/m2_dcqcn_out'
p=os.path.join(D,'round_summary.csv')
rows=list(csv.DictReader(open(p)))
print('round_summary.csv: %d rows, columns include:' % len(rows))
cols=list(rows[0].keys())
print('  ' + ', '.join(c for c in cols if any(k in c.lower() for k in ('flow','src','dst','cnp','ecn','rate')))[:200])
print()
# enumerate EVERY row, no filter at all
print('=== every row, grouped by src (no hardcoded filter) ===')
bysrc={}
for r in rows:
    s=r.get('src', r.get('flow_id','?'))
    cnp=float(r.get('cnp_count','0') or 0)
    bysrc.setdefault(s, [0,0.0])
    bysrc[s][0]+=1
    bysrc[s][1]+=cnp
tot=0.0
for s in sorted(bysrc, key=lambda x: (len(x), x)):
    n,c=bysrc[s]
    tot+=c
    if s in ('65','0','1') or c==0:
        print('  src=%-4s rows=%-3d cnp_total=%.0f' % (s,n,c))
print('  ---')
print('  sum of cnp over ALL %d rows = %.0f' % (len(rows), tot))
print()
# explicit background lookup by several possible keys
print('=== background flow (src 65) rows, all columns of interest ===')
bg=[r for r in rows if r.get('src')=='65' or r.get('flow_id')=='0']
for r in bg[:2]:
    for k in cols:
        if any(x in k.lower() for x in ('flow','src','dst','cnp','ecn','rate','byte')):
            print('    %-28s %s' % (k, r[k]))
