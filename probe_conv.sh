set -u
cd /work/simulation/experiment/scheme1_sba
python3 - <<'PY'
# S3 (bg cap 8G) and S4 (bg cap 9.5G) now give nearly identical incast FCT.
# If eta is being raised to the feasibility bound, per-flow target becomes
# exactly MIN_RATE and the incast rate is pinned by the floor, NOT by the
# background load -- which would explain the convergence. Test that.
import csv
for tag, cap in (('s3', 8.0), ('s4', 9.5)):
    with open('f_cbapsba_%s_seed2_out/flow_summary.csv' % tag) as f:
        rows = list(csv.DictReader(f))
    inc = [r for r in rows if r['src'] != '65' and r['completed'] == '1']
    gps = sorted(float(r['flow_goodput']) / 1e6 for r in inc)
    print('%s (bg cap %.1f G):' % (tag.upper(), cap))
    print('   per-flow goodput  min=%.3f  median=%.3f  max=%.3f Mbps'
          % (gps[0], gps[len(gps)//2], gps[-1]))
    print('   aggregate = %.3f Gbps   N*MIN_RATE = 6.400 Gbps' % (sum(gps)/1000))
    # background share during the collective
    fin = max(float(r['finish_time']) for r in inc)
    with open('f_cbapsba_%s_seed2_out/selected_link_timeseries.csv' % tag) as f:
        ts = [r for r in csv.DictReader(f)
              if 1.9 <= float(r['time']) <= fin]
    txd = sum(float(r['tx_bytes_delta']) for r in ts)
    dur = fin - 1.9
    print('   link carried %.3f Gbps over the %.1f ms collective'
          % (txd * 8 / dur / 1e9, dur * 1000))
    print('   -> incast %.3f G + background %.3f G'
          % (sum(gps)/1000, txd*8/dur/1e9 - sum(gps)/1000))
PY
