#!/bin/bash
# Per-algorithm smoke verification for the multi-algorithm S1 matrix.
#
# Runs all five algorithms on the SAME S1 scenario, SAME seed, and the SAME
# stop time, then prints one verification row per algorithm so the comparison
# can be audited before any full matrix is launched.
#
# Usage:  bash smoke_verify.sh [STOP_TIME] [SEED]
# Default: STOP_TIME=6.0  SEED=2
#
# Creates only smoke_<algo>_out directories.  Never deletes anything.
set -u

STOP=${1:-6.0}
SEED=${2:-2}
SIM=/work/simulation
D=experiment/scheme1_sba
LOGS=/work/smoke_logs

cd "$SIM"
mkdir -p "$LOGS"

# Expected scenario parameters, read from the scenario inputs rather than
# assumed, so the table reports what the run actually used.
FLOW_FILE=$D/s1_flow.txt
TOPO=$D/topology.txt
EXPECTED_INCAST=$(awk 'NR>1 && $1!=65 {n++} END{print n+0}' "$FLOW_FILE")
INCAST_START=$(awk 'NR>1 && $1!=65 {print $6; exit}' "$FLOW_FILE")
MSG_BYTES=$(awk 'NR>1 && $1!=65 {print $5; exit}' "$FLOW_FILE")
BG_BYTES=$(awk 'NR>1 && $1==65 {print $5; exit}' "$FLOW_FILE")
BG_CAP=$(awk '/^APP_RATE_CAP_BPS/{print $2}' $D/s1_config.txt)
QMAX=$(awk 'NR==2{print $5}' $D/s1_cbap_link.txt)

# algo tag -> CC_MODE, CBAP_ENABLE, MIGRATION
declare -A CCMODE=( [dcqcn]=1 [hpcc]=3 [timely]=7 [dctcp]=8 [cbapsba]=30 )
declare -A CBAPEN=( [dcqcn]=0 [hpcc]=0 [timely]=0 [dctcp]=0 [cbapsba]=1 )
declare -A MIGEN=(  [dcqcn]=0 [hpcc]=0 [timely]=0 [dctcp]=0 [cbapsba]=1 )
ORDER="dcqcn hpcc timely dctcp cbapsba"

make_config() {
  local tag=$1 out=$2 cfg=$3
  local stopns
  stopns=$(python2 -c "print int(float('$STOP')*1e9)")
  {
    while read -r line; do
      [ -z "$line" ] && continue
      set -- $line
      local key=$1
      case "$key" in
        CC_MODE)              echo "CC_MODE ${CCMODE[$tag]}" ;;
        CBAP_ENABLE)          echo "CBAP_ENABLE ${CBAPEN[$tag]}" ;;
        SIM_SEED)             echo "SIM_SEED $SEED" ;;
        ALGORITHM)            echo "ALGORITHM $tag" ;;
        SIMULATOR_STOP_TIME)  echo "SIMULATOR_STOP_TIME $STOP" ;;
        QLEN_MON_END)         echo "QLEN_MON_END $stopns" ;;
        # Background flow (id 0) must occupy a rate-trace slot so its
        # throughput, minimum rate and recovery time are measurable.
        ROUND_TRACE_SELECTED_FLOWS) echo "ROUND_TRACE_SELECTED_FLOWS 0,1,2,3" ;;
        *)
          # Redirect every output path into this run's own directory.
          echo "$line" | sed "s|s1_out/|${out}/|g"
          ;;
      esac
    done < $D/s1_config.txt
    [ "${MIGEN[$tag]}" = "1" ] && echo "CBAP_MIGRATION_ENABLE 1"
    [ "${MIGEN[$tag]}" = "1" ] && echo "CBAP_MIGRATION_TRACE 0"
  } > "$cfg"
}

echo "smoke verification: STOP_TIME=${STOP}s SEED=${SEED}"
echo "scenario inputs: expected_incast=${EXPECTED_INCAST} msg=${MSG_BYTES}B" \
     "bg=${BG_BYTES}B bg_cap=${BG_CAP}bps incast_start=${INCAST_START}s qmax=${QMAX}B"
echo ""

for tag in $ORDER; do
  out=smoke_${tag}_out
  cfg=$D/smoke_${tag}.txt
  mkdir -p "$D/$out"
  make_config "$tag" "$out" "$cfg"
  python2 waf --cwd=$D --run "scratch/third smoke_${tag}.txt" \
      > "$LOGS/${tag}.log" 2>&1
  echo "$? " > "$LOGS/${tag}.exit"
done

# ---- verification table ----
python2 - "$STOP" "$SEED" "$EXPECTED_INCAST" "$INCAST_START" "$MSG_BYTES" \
          "$BG_BYTES" "$BG_CAP" "$QMAX" <<'PYEOF'
import csv, os, sys, hashlib

stop, seed, expected, start, msg, bgb, bgcap, qmax = sys.argv[1:9]
expected = int(expected)
D = '/work/simulation/experiment/scheme1_sba'
LOGS = '/work/smoke_logs'
ORDER = ['dcqcn', 'hpcc', 'timely', 'dctcp', 'cbapsba']
BG_SRC = '65'


def sha(p):
    if not os.path.exists(p):
        return 'MISSING'
    h = hashlib.sha256()
    f = open(p, 'rb')
    try:
        h.update(f.read())
    finally:
        f.close()
    return h.hexdigest()[:12]


def rows(p):
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return []
    f = open(p)
    try:
        return list(csv.DictReader(f))
    finally:
        f.close()


print('=' * 118)
print('%-9s %-7s %-6s %-6s %-7s %-9s %-9s %-10s %-9s %-8s %s' % (
    'algo', 'CC', 'exit', 'rows', 'done/exp', 'first(ms)', 'last(ms)',
    'bg_gp(Gbps)', 'q@cut(B)', 'cfghash', 'outdir'))
print('=' * 118)

for tag in ORDER:
    out = os.path.join(D, 'smoke_%s_out' % tag)
    cfg = os.path.join(D, 'smoke_%s.txt' % tag)
    ep = os.path.join(LOGS, '%s.exit' % tag)
    code = open(ep).read().strip() if os.path.exists(ep) else '?'

    # algorithm + CC_MODE as actually loaded
    ccmode = '?'
    if os.path.exists(cfg):
        for line in open(cfg):
            if line.startswith('CC_MODE '):
                ccmode = line.split()[1]
                break

    fs = rows(os.path.join(out, 'flow_summary.csv'))
    inc = [r for r in fs if r['src'] != BG_SRC]
    bg = [r for r in fs if r['src'] == BG_SRC]
    fin = sorted(float(r['finish_time']) for r in inc)
    st = float(start)
    first = (fin[0] - st) * 1000 if fin else float('nan')
    last = (fin[-1] - st) * 1000 if fin else float('nan')

    # recorded algorithm name from the data itself
    recorded = fs[0]['algorithm'] if fs else '-'

    # background goodput: prefer the completed-flow figure, else integrate the
    # rate trace (background flow is 4GB and usually does not finish).
    bggp = float('nan')
    if bg:
        bggp = float(bg[0]['flow_goodput']) / 1e9
    else:
        tr = rows(os.path.join(out, 'selected_flow_timeseries.csv'))
        vals = [float(r['current_rate']) for r in tr
                if r.get('flow_id') == '0' and float(r['time']) >= st]
        if vals:
            bggp = sum(vals) / len(vals) / 1e9

    # queue at cutoff
    qcut = float('nan')
    lt = rows(os.path.join(out, 'selected_link_timeseries.csv'))
    if lt:
        qcut = int(lt[-1]['queue_bytes'])

    ok = 'OK' if len(inc) == expected else 'SHORT'
    print('%-9s %-7s %-6s %-6d %-9s %9.3f %9.3f %10.3f %9.0f %-8s %s' % (
        tag, ccmode, code, len(fs),
        '%d/%d %s' % (len(inc), expected, ok),
        first, last, bggp, qcut, sha(cfg), 'smoke_%s_out' % tag))
    if recorded != tag:
        print('    ! recorded algorithm in CSV = %r (expected %r)' % (
            recorded, tag))

print('=' * 118)
print('scenario: fan-in=%d msg=%sB bg=%sB bg_cap=%sbps incast_start=%ss '
      'stop=%ss seed=%s qmax=%sB' % (
          expected, msg, bgb, bgcap, start, stop, seed, qmax))
print('')
print('done criterion for the real matrix: completed incast flows == %d' %
      expected)
PYEOF
