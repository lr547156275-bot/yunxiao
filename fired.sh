set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== did the credit trace get written, and did credit fire? ==="
f=qc_s3_t025_out/delay_credit.csv
if [ ! -f "$f" ]; then echo "  MISSING $f"; exit 0; fi
echo "  rows: $(awk 'END{print NR-1}' "$f")"
head -1 "$f" | tr ',' '\n' | nl | head -21 | sed 's/^/    /'
echo
python3 - <<'PY'
import csv
rows=list(csv.DictReader(open('qc_s3_t025_out/delay_credit.csv')))
print('  replans logged: %d' % len(rows))
cred=[r for r in rows if float(r['credit_bps'])>0]
over=[r for r in rows if r['oversubscribed']=='1']
trunc=[r for r in rows if r['credit_truncated']=='1']
print('  rows with credit>0      : %d' % len(cred))
print('  rows with sum(target)>C : %d   <-- the mechanism firing' % len(over))
print('  rows credit-truncated   : %d' % len(trunc))
print()
print('  %-6s %-8s %-9s %-9s %-9s %-11s %-11s %s' % ('epoch','phase','q','q_target','q_hard','credit_G','budget/C','oversub'))
for r in rows[:8]:
    print('  %-6s %-8s %-9s %-9s %-9s %-11.3f %-11.4f %s'
          % (r['epoch'], r['phase'], r['queue_bytes'], r['q_target_bytes'],
             r['q_hard_bytes'], float(r['credit_bps'])/1e9,
             float(r['budget_over_capacity']), r['oversubscribed']))
PY
