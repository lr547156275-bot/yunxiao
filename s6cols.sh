set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== any bg0_/bg1_ columns in final_results.csv? ==="
head -1 final_report/final_results.csv | tr ',' '\n' | grep -c "^bg0_\|^bg1_" | sed 's/^/  count: /'
head -1 final_report/final_results.csv | tr ',' '\n' | grep "^bg0_\|^bg1_" | sed 's/^/  /'
echo "=== and in the per-scenario analysis_s6/per_run.csv? ==="
head -1 analysis_s6/per_run.csv | tr ',' '\n' | grep "^bg0_\|^bg1_" | sed 's/^/  /' || echo "  none"
echo "=== so for S6 the two bg flows are rolled up how? ==="
python3 - <<'PY'
import csv
r=[x for x in csv.DictReader(open('analysis_s6/per_run.csv')) if x['algorithm']=='cbapsba'][0]
for k in ('bg_n_flows','bg_retention_pct','bg_min_gbps','bg_recovery90_ms',
          'bg_recovery90_ms_never_dipped','bg_recovery95_ms','bg_service_debt_bytes'):
    print('   %-32s %s' % (k, r.get(k,'<absent>')))
PY
