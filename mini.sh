#!/bin/bash
# S3-mini: same 64-way fan-in, same topology, same background flow, same seed 2,
# only the per-flow size shrinks 1 MiB -> 256 KiB.  Four arms, run in order.
#
#   1 DCQCN                (CC_MODE 1)
#   2 CBAP baseline        (phase=0, steady-cap=0)
#   3 phase only           (phase=1, steady-cap=0)
#   4 phase + steady-cap   (phase=1, steady-cap=1)
#
# The discredited direct-fill path (CBAP_SBA_STEADY_FILL) is NOT used.
set -u
export LD_LIBRARY_PATH=/work/simulation/build:${LD_LIBRARY_PATH:-}
LOG=/work/mini.log
cd /work/simulation/experiment/scheme1_sba || exit 1
sha256sum /work/simulation/build/scratch/third \
          /work/simulation/build/libns3.18-point-to-point-debug.so >> "$LOG"

# ---- mini flow file: 64 x 256 KiB incast + the unchanged background flow ----
python3 - <<'PY' >> "$LOG" 2>&1
src = 's3_flow.txt'
dst = 'mini_flow.txt'
lines = open(src).read().split('\n')
n = int(lines[0].split()[0])
out, kept = [], 0
for ln in lines[1:]:
    p = ln.split()
    if len(p) < 6:
        continue
    size = int(p[4])
    if size >= (1 << 30):
        out.append(ln)              # background flow untouched
    else:
        p[4] = str(256 * 1024)      # 1 MiB -> 256 KiB
        out.append(' '.join(p))
    kept += 1
open(dst, 'w').write('%d\n%s\n' % (kept, '\n'.join(out)))
print('mini_flow.txt: %d flows (declared %d in source)' % (kept, n))
sizes = {}
for ln in out:
    sizes[int(ln.split()[4])] = sizes.get(int(ln.split()[4]), 0) + 1
print('  size histogram: %s' % sorted(sizes.items()))
PY

mk () {   # $1 name  $2 cc_mode  $3 cbap_enable  $4 phase  $5 steadycap
  local out="mn_$1_out" cfg="mn_$1.txt"
  sed -e "s|ct_cbap_off_out|${out}|g" \
      -e "s|^FLOW_FILE .*|FLOW_FILE mini_flow.txt|" \
      -e "s|^CC_MODE .*|CC_MODE $2|" \
      -e "s|^CBAP_ENABLE .*|CBAP_ENABLE $3|" \
      -e "s|^SIMULATOR_STOP_TIME .*|SIMULATOR_STOP_TIME 2.6|" \
      -e "s|^QLEN_MON_END .*|QLEN_MON_END 2600000000|" \
      ct_cbap_off.txt > "$cfg"
  {
    echo "CBAP_PHASE_SPREAD_ENABLE $4"
    echo "CBAP_STEADY_CAP_ENABLE $5"
    echo "CBAP_SBA_STEADY_FILL 0"
    echo "CBAP_HOLD_TRACK_TARGET 0"
  } >> "$cfg"
  mkdir -p "$out"
}

run () {
  local cfg="$1" out="$2"
  for att in 1 2; do
    [ -f "$out/DONE" ] && return 0
    free=$(df --output=avail -BG /work | tail -1 | tr -dc '0-9')
    if [ "${free:-0}" -lt 1 ]; then
      echo "INVALID_LOW_DISK free=${free}G" >> "$LOG"; return 1
    fi
    echo "$out attempt $att start $(date -u +%H:%M:%S) free=${free}G" >> "$LOG"
    /work/simulation/build/scratch/third "$cfg" > "/tmp/${out}.txt" 2>&1
    rc=$?
    echo "$out attempt $att exit=$rc $(date -u +%H:%M:%S)" >> "$LOG"
    if [ "$rc" -eq 0 ] && [ -s "$out/flow_summary.csv" ]; then
      touch "$out/DONE"; echo "$out DONE" >> "$LOG"; return 0
    fi
    grep -m1 -E "INVALID_|CONFIG_ERROR|assert" "/tmp/${out}.txt" >> "$LOG"
    sleep 5
  done
  echo "$out EXHAUSTED" >> "$LOG"; return 1
}

mk dcqcn 1  0 0 0
mk base  30 1 0 0
mk phase 30 1 1 0
mk both  30 1 1 1

for a in dcqcn base phase both; do
  run "mn_$a.txt" "mn_${a}_out" || { echo "STOP at $a" >> "$LOG"; exit 1; }
done
echo "MINI_ALL_DONE" >> "$LOG"
df -h /work | tail -1 >> "$LOG"
