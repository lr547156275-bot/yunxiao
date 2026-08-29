set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== S6 per-flow background recovery (bg0_ / bg1_) ==="
python3 - <<'PY'
import csv
rows=[r for r in csv.DictReader(open('final_report/final_results.csv')) if r['scenario_tag']=='s6']
cols=[k for k in rows[0] if k.startswith('bg0_') or k.startswith('bg1_')]
want=[c for c in cols if 'recovery' in c or 'retention' in c or 'min_gbps' in c or 'never' in c]
print('   available per-flow cols: %s' % ', '.join(sorted(want)))
print()
print('   %-9s %s' % ('algorithm', '  '.join('%-28s' % w for w in sorted(want))))
for r in rows:
    print('   %-9s %s' % (r['algorithm'],
        '  '.join('%-28s' % (r.get(w,'')[:26]) for w in sorted(want))))
PY
