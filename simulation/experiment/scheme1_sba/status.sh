#!/bin/bash
# Matrix progress at a glance: a 6x5 grid of scenario x algorithm.
#   OK   = cell complete and validated
#   FAIL = cell ran but failed a done condition (see its manifest)
#   .    = not yet run
#   RUN  = currently in flight
set -u
LOGS=/work/matrix_logs
ALGOS="dcqcn dctcp timely hpcc cbapsba"
TAGS="s1 s2 s3 s6 s4 s5"
SEED=${SEED:-2}

printf "%-8s" "scen"
for a in $ALGOS; do printf " %-8s" "$a"; done
echo ""
printf "%-8s" "--------"
for a in $ALGOS; do printf " %-8s" "--------"; done
echo ""

running=$(ps -o cmd= -C third 2>/dev/null | grep -v defunct || true)
total=0
for t in $TAGS; do
  printf "%-8s" "$t"
  for a in $ALGOS; do
    name="m_${a}_${t}_seed${SEED}"
    if [ -f "$LOGS/${name}.done" ]; then
      printf " %-8s" "OK"; total=$((total + 1))
    elif echo "$running" | grep -q "${name}.txt"; then
      printf " %-8s" "RUN"
    elif [ -f "$LOGS/${name}.manifest" ]; then
      printf " %-8s" "FAIL"
    else
      printf " %-8s" "."
    fi
  done
  echo ""
done
echo ""
echo "complete: $total/30"
if [ -n "$running" ]; then
  echo "in flight: $(echo "$running" | sed 's|.*scratch/third ||' | tr '\n' ' ')"
else
  echo "in flight: none"
fi
[ -f "$LOGS/run_all.out" ] && { echo ""; echo "last driver lines:"; tail -3 "$LOGS/run_all.out" | sed 's/^/  /'; }
fails=$(ls "$LOGS"/m_*.manifest 2>/dev/null | while read -r m; do
  ec=$(awk -F= '$1=="exit_code"{print $2}' "$m")
  got=$(awk -F= '$1=="completed_incast"{print $2}' "$m")
  exp=$(awk -F= '$1=="expected_incast"{print $2}' "$m")
  tr=$(awk -F= '$1=="trace_complete"{print $2}' "$m")
  n=$(basename "$m" .manifest)
  [ -f "$LOGS/${n}.done" ] && continue
  echo "  $n exit=$ec incast=$got/$exp trace=$tr"
done)
[ -n "$fails" ] && { echo ""; echo "cells needing attention:"; echo "$fails"; }
exit 0
