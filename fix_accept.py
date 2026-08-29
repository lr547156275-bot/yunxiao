import io
p = '/work/accept_cell.sh'
s = io.open(p, encoding='utf-8').read()
old = '''FF=$(grep -m1 '^FLOW_FILE ' "$CFG" | awk '{print $2}')
TOT=$(awk 'NR>1' "$FF" | wc -l)
P3=$(awk 'NR>1 && $3==3' "$FF" | wc -l)
P0=$(awk 'NR>1 && $3==0' "$FF" | wc -l)'''
assert s.count(old) == 1, ('pg anchor', s.count(old))
new = '''FF=$(grep -m1 '^FLOW_FILE ' "$CFG" | awk '{print $2}')
TOT=$(awk 'NR>1' "$FF" | wc -l)
P3=$(awk 'NR>1 && $3==3' "$FF" | wc -l)
P0=$(awk 'NR>1 && $3==0' "$FF" | wc -l)
# Expected incast/background counts come from the flow SIZE class in the flow
# file, not from "total minus one".  S1-S5 have ONE background flow but S6 has
# TWO (one per bottleneck: 65->64 and 61->60), so TOT-1 miscounted a background
# flow as incast and failed cbap_s6 at "60 of 61" when all 60 incast had in fact
# completed.  Threshold unchanged: every incast flow must complete; background
# flows are long-lived and are NOT required to finish inside the window.
EXP_INC=$(awk 'NR>1 && $5<1000000000' "$FF" | wc -l)
EXP_BG=$(awk 'NR>1 && $5>=1000000000' "$FF" | wc -l)'''
s = s.replace(old, new)

old2 = '''LINES=$(wc -l < "$OUT/flow_summary.csv" 2>/dev/null || echo 0)
DONE=$(awk -F, 'NR>1 && $13==1' "$OUT/flow_summary.csv" 2>/dev/null | wc -l)
EXP=$((TOT-1))
if [ "$DONE" -ge "$EXP" ]; then
  pass "incast flows complete: $DONE/$EXP"
else
  fail "incast flows complete" "$DONE of $EXP"
fi'''
assert s.count(old2) == 1, ('flows anchor', s.count(old2))
new2 = '''LINES=$(wc -l < "$OUT/flow_summary.csv" 2>/dev/null || echo 0)
# Classify by size, matching the metrics extractor in this same script.
INC_DONE=$(awk -F, 'NR>1 && $8<1000000000 && $13==1' "$OUT/flow_summary.csv" 2>/dev/null | wc -l)
BG_DONE=$(awk -F, 'NR>1 && $8>=1000000000 && $13==1' "$OUT/flow_summary.csv" 2>/dev/null | wc -l)
if [ "$INC_DONE" -ge "$EXP_INC" ]; then
  pass "incast flows complete: $INC_DONE/$EXP_INC (background $BG_DONE/$EXP_BG, not required)"
else
  fail "incast flows complete" "$INC_DONE of $EXP_INC"
fi'''
s = s.replace(old2, new2)
io.open(p, 'w', encoding='utf-8').write(s)
print('patched accept_cell.sh')
print('  EXP_INC/EXP_BG present :', s.count('EXP_INC'), s.count('EXP_BG'))
print('  TOT-1 removed          :', s.count('$((TOT-1))'))
