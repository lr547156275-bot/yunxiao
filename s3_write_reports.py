# -*- coding: utf-8 -*-
# Write the S3 report files.  Read-only w.r.t. experiment data.
import csv
import hashlib
import os

D = '/work/simulation/experiment/scheme1_sba/analysis/s3_full_metrics_v1'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


PROV = """# S3 PROVENANCE

## Selected inputs (chosen by config/SHA evidence, NOT directory name)

| arm | directory | why selected |
|---|---|---|
| CBAP-SBA rho=0.90 | `ckpt4_cbap_s3_out` | CC_MODE 30, CBAP_ENABLE 1, MIGRATION_ENABLE 1, CORE_INITIAL_RELEASE 1, INITIAL_RELEASE_RATIO 0.90, MIGRATION_TRACE 1; CBAP_MIG=1050; exit=0; 64/64 incast |
| DCQCN baseline | `ckpt4_dcqcn_s3_out` | CC_MODE 1, CBAP_ENABLE 0, zero CBAP keys; exit=0; 64/64 incast |

Rejected candidates:
- `rec2_s3_on_out` - same rho/migration and CBAP_MIG=1050, but from a different
  batch under binary 265fe2a1 with a duplicated MIGRATION_TRACE key; not a
  config-matched pair member.
- `ckpt3_cbap_s3_out` / `ckpt3_dcqcn_s3_out` - reallocation OFF
  (ABLATION_FULL_CAPACITY_REALLOCATION_OFF), CBAP_MIG=0.
- `ckpt4_cbap_s3_out.NOTRACE` - correct physics but MIGRATION_TRACE absent, so no
  direct migration trajectory; retained as bypass-consistency evidence.

## Pairing verification

All five inputs byte-identical across arms:

| input | sha256 (16) |
|---|---|
| topology.txt | 6091d5ec28c391c0 |
| s3_flow.txt | 6b922c67e56c04aa |
| s3_round_schedule.txt | 8a40b3d13abe225d |
| s3_cbap_link.txt | 70903775ca19226b |
| s3_cbap_path.txt | 1557487d29e7efb5 |

Non-algorithm config diff: **IDENTICAL** (only CC_MODE, CBAP_ENABLE,
CBAP_QUEUE_CONTROLLER_ENABLE and the three reallocation keys differ).
SIM_SEED=2 both arms.  pg: all 65 flows pg=3, pg0_count=0.

Parsed-value echo from the CBAP run.log (not config text):
`CBAP_REALLOC_PARSED migration_enable=1 core_initial_release=1 initial_release_ratio=0.9 migration_trace=1`

## Toolchain
binary `290cb41fec981bc848cbfd518257ce2c5df1384d52f2325d67955acaabd880b7`
libns3 `c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122`

## Windows
| window | definition | value |
|---|---|---|
| W0 FULL_RUN | whole sim | 0 - 3.0 s |
| W1 CBAP | native batch | [2.000000000, 2.059406587] s |
| W1 DCQCN | native batch | [2.000000000, 2.058372997] s |
| W2 COMMON_OVERLAP | max(start), min(finish) | [2.000000000, 2.058372997] s = **58.372997 ms** |
| W3 CBAP_TAIL | DCQCN finish -> CBAP finish | [2.058372997, 2.059406587] s = **1.033590 ms** |
| W4 MIGRATION_CONVERGENCE | first CBAP_MIG -> end=converged | see S3_FULL_METRICS.csv |
"""

GAP = """# S3 mean-FCT gap decomposition

## Arithmetic check (as specified)

```
CBAP  mean = 59.390868 ms   max = 59.406587 ms   min = 59.375150 ms   std = 0.009218 ms
DCQCN mean = 54.278454 ms   max = 58.372997 ms   min = 47.764170 ms   std = 2.509897 ms

d_mean               = 59.390868 - 54.278454 = 5.112414 ms
tail_component       = 59.406587 - 58.372997 = 1.033590 ms
dispersion_component = (58.372997-54.278454) - (59.406587-59.390868)
                     = 4.094543 - 0.015719   = 4.078824 ms
sum                  = 1.033590 + 4.078824   = 5.112414 ms   EXACT
```

The identity closes to the last digit: **20.22 % tail**, **79.78 % dispersion**.
Independent corroboration: W3_CBAP_TAIL measured from the flow records is
**1.033590 ms**, identical to tail_component.

## H1 - ~80 % of the gap is CBAP lock-step completion  ->  CONFIRMED, HIGH

Supporting:
- dispersion_component = 4.078824 ms = **79.78 %** of d_mean.
- CBAP FCT spread max-min = **0.031437 ms** over 64 flows; std 0.009218 ms;
  CV 0.000155.
- DCQCN FCT spread max-min = **10.608827 ms**; std 2.509897 ms; CV 0.046241.
- DCQCN min FCT 47.764170 ms is **11.611 ms earlier** than CBAP min 59.375150 ms.
- completion skew: CBAP 0.031437 ms vs DCQCN 10.608827 ms (**338x**).

Contradicting: none found.

Note: equal-size flows finishing together is the intended SBA behaviour, so
"dispersion" is a property of the arithmetic mean here, not evidence of DCQCN
unfairness.  No causal claim beyond the measured spread is made.

## H2 - ~20 % from service rate / utilisation / convergence  ->  CONFIRMED, HIGH

Supporting (W2 COMMON_OVERLAP, link 84:1, both arms DERIVED from tx_bytes_delta):
- served wire mean: CBAP **9.576401** vs DCQCN **9.878142** Gbps (-3.05 %).
- utilisation mean: CBAP **0.957640** vs DCQCN **0.987814**.
- samples below 95 % utilisation: CBAP **25.88 %** vs DCQCN **9.06 %** (2.86x).
- service deficit vs an ideal full link: CBAP **4.2245 %** vs DCQCN **1.2067 %**.
- served bytes in W2: CBAP 69,883,784 vs DCQCN 72,085,744 (**-2,201,960 B**).
- idle fraction **0.000000** for both arms: the shortfall is rate, not idleness.

Contradicting: in W3 the CBAP tail still runs at **0.958956** utilisation, so the
tail is not a stalled link - it is 1.03 ms of residual work at ~96 % of line rate.

## H3 - released background capacity not fully converted  ->  PARTLY, MEDIUM

Supporting:
- CBAP holds background flow 0 at MIN_RATE for **99.69 %** of W2; overlap mean
  rate **0.106291** Gbps.
- DCQCN holds it at MIN_RATE only **3.25 %** of W2; overlap mean **1.196825** Gbps.
- CBAP therefore frees ~1.09 Gbps more background capacity inside W2, yet its
  served rate is **0.301741 Gbps lower**.
- Controller state in W2: zone GREEN **100 %**, boost non-zero in **99.65 %** of
  epochs, boost mean **2.257327** Gbps, drain identically **0**.

Contradicting / limits:
- Both arms reach the same p95 served rate (**10.060800** Gbps), so the ceiling is
  identical; the difference lives in the lower tail of the rate distribution.
- The conversion loss cannot be closed from these outputs: DCQCN has no
  port_summary.csv, so arrival-vs-served accounting is unavailable for that arm.

Residual: the 0.301741 Gbps shortfall is **not fully explained**.  What is
established is that it is not idleness (idle=0) and not queue starvation
(CBAP queue mean 23,957 B).  Correlation is reported; causation is not claimed.

## Safety context (the trade-off, not part of the gap)

| metric (W2, link 84:1) | CBAP | DCQCN |
|---|---|---|
| queue mean | **23,957 B** | 960,441 B |
| queue p95 | **46,112 B** | 1,273,320 B |
| queue max | **54,496 B** | 1,279,608 B |
| queue delay max | **43.60 us** | 1023.69 us |
| queue max as % of Q_abs | **5.20 %** | **122.03 %** (over the hard bound) |
| ECN marks | **0** | 6,677 |
| PFC / drops / retx | 0 / 0 / 0 | 0 / 0 / 0 |

DCQCN buys its 5.11 ms with a queue exceeding Q_abs by 22 % and 6,677 ECN marks.
CBAP stays at 5.2 % of Q_abs with zero ECN.

## Section 7 check - UNDERUTILIZED_CONTROLLER

CBAP W2: utilisation mean 0.957640; below 95 % for 25.88 % of samples; queue mean
23,957 B, far under Q_low (524,288 B); boost already non-zero in 99.65 % of epochs
at mean 2.257 Gbps against MAX_BOOST 3.000 Gbps; drain 0.

=> **UNDERUTILIZED_CONTROLLER = TRUE for W2**: the queue sits deep in the safe
zone while the bottleneck runs ~4.2 % under line rate, and the controller is
boosting at only ~75 % of MAX_BOOST.  Headroom is real, so per the stated rule the
controller should continue to boost.
"""


def main():
    open(os.path.join(D, 'S3_PROVENANCE.md'), 'w').write(PROV)
    open(os.path.join(D, 'S3_GAP_DECOMPOSITION.md'), 'w').write(GAP)

    rows = list(csv.DictReader(open(os.path.join(D, 'S3_FULL_METRICS.csv'))))
    miss = [x for x in rows if x['availability'] == 'MISSING']
    seen = set()
    lines = []
    for x in miss:
        k = (x['metric_id'], x['algorithm'])
        if k in seen:
            continue
        seen.add(k)
        lines.append('| `%s` | %s | %s |' % (x['metric_id'], x['algorithm'],
                                             x['notes']))
    body = '\n'.join(lines)
    open(os.path.join(D, 'S3_MISSING_METRICS.md'), 'w').write(
        '# S3 MISSING METRICS\n\n%d metric rows are UNAVAILABLE/MISSING.  None is '
        'substituted, zeroed or replaced by a proxy.\n\n'
        '| metric_id | arm | why unavailable |\n|---|---|---|\n%s\n\n'
        '## Minimum instrumentation needed (NOT implemented this round)\n\n'
        '1. **DCQCN arrival / service rate, queue gradient, port state** - '
        '`port_summary.csv` is written only on the CBAP telemetry path.  Needs a '
        'CC-agnostic egress-port sampler emitting the same columns regardless of '
        'CC_MODE.  Re-run: `ckpt4_dcqcn_s3` (~17 min, ~50 MB).\n\n'
        '2. **Per-flow CNP counts** - no CNP column exists in any output.  Needs a '
        'per-QP CNP counter surfaced into flow_summary.csv.  Re-run: both S3 cells '
        '(~35 min).\n\n'
        '3. **H_obs / H_sender / H_path / H_eff actuation latency** - needs '
        'commanded -> sender-effective -> bottleneck-arrival timestamps per QP.  '
        'actuation.csv exists for CBAP only, so no cross-arm comparison is '
        'possible.\n\n'
        '4. **DCQCN controller zones / boost / drain / pending** - do not exist for '
        'DCQCN by construction.  Reported MISSING rather than 0, because 0 would '
        'falsely imply "measured and found zero".\n'
        % (len(miss), body))

    # executive summary + full metrics markdown
    def g(mid, algo, win, scope=None, stat=None):
        for x in rows:
            if (x['metric_id'] == mid and x['algorithm'] == algo
                    and x['window'] == win):
                if scope and x['scope'] != scope:
                    continue
                if stat and x['statistic'] != stat:
                    continue
                return x['value']
        return 'NA'

    L = ['# S3 EXECUTIVE SUMMARY', '',
         'CBAP-SBA rho=0.90 (migration ON) vs DCQCN baseline, scenario S3,',
         'same topology/flow/link/path/seed/PG, binary 290cb41f.', '',
         '## Headline', '',
         '| metric | CBAP rho=0.90 | DCQCN | delta |',
         '|---|---|---|---|']
    for lbl, mid in (('incast FCT mean (ms)', 'B.fct.mean'),
                     ('incast FCT p95 (ms)', 'B.fct.p95'),
                     ('incast FCT p99 (ms)', 'B.fct.p99'),
                     ('incast FCT max / CCT (ms)', 'B.fct.max'),
                     ('incast FCT std (ms)', 'B.fct.std'),
                     ('completion skew (ms)', 'B.completion_skew')):
        a, b = g(mid, 'CBAP', 'W1'), g(mid, 'DCQCN', 'W1')
        try:
            d = '%+.4f' % (float(a) - float(b))
        except Exception:
            d = ''
        L.append('| %s | %s | %s | %s |' % (lbl, a[:10], b[:10], d))
    L += ['', '## W2 COMMON_OVERLAP (58.372997 ms, link 84:1)', '',
          '| metric | CBAP | DCQCN |', '|---|---|---|']
    for lbl, mid in (('served wire mean (Gbps)', 'C.served.wire.mean'),
                     ('utilisation mean', 'C.utilization.mean'),
                     ('frac samples <95% util', 'C.util.frac_below_95'),
                     ('service deficit frac', 'C.service_deficit.frac'),
                     ('idle fraction', 'C.idle.fraction'),
                     ('queue mean (B)', 'D.queue.bytes.mean'),
                     ('queue max (B)', 'D.queue.bytes.max'),
                     ('queue max %% of Q_abs', 'D.queue.pct_Qabs.max'),
                     ('ECN marks', 'G.ecn.marks')):
        L.append('| %s | %s | %s |' % (lbl,
                                       g(mid, 'CBAP', 'W2', 'link84:1')[:12],
                                       g(mid, 'DCQCN', 'W2', 'link84:1')[:12]))
    L += ['', '## Background flow 0', '',
          '| metric | CBAP | DCQCN |', '|---|---|---|',
          '| full-run goodput (Gbps) | %s | %s |'
          % (g('F.bg.fullrun.goodput', 'CBAP', 'W0', 'flow 0')[:10],
             g('F.bg.fullrun.goodput', 'DCQCN', 'W0', 'flow 0')[:10]),
          '| overlap mean rate (Gbps) | %s | %s |'
          % (g('F.bg.overlap.rate.mean', 'CBAP', 'W2', 'flow0')[:10],
             g('F.bg.overlap.rate.mean', 'DCQCN', 'W2', 'flow0')[:10]),
          '| overlap frac at MIN_RATE | %s | %s |'
          % (g('F.bg.overlap.frac_at_min_rate', 'CBAP', 'W2', 'flow0')[:10],
             g('F.bg.overlap.frac_at_min_rate', 'DCQCN', 'W2', 'flow0')[:10]),
          '',
          'The full-run goodput differs by only 0.2 %, but inside the overlap',
          'window CBAP pins the background flow at MIN_RATE for 99.69 % of the',
          'time versus 3.25 % for DCQCN.  Reporting only the full-run average',
          'would hide that.', '',
          '## Gap', '',
          'd_mean = 5.112414 ms = 1.033590 (tail, 20.22 %) + 4.078824',
          '(dispersion, 79.78 %).  Identity closes exactly.  See',
          'S3_GAP_DECOMPOSITION.md.', '',
          '## Verdict', '',
          '- CBAP is 9.42 % slower in mean FCT but 256x tighter in spread',
          '  (0.0157 vs 4.0945 ms max-mean).',
          '- CBAP keeps the queue at 5.20 % of Q_abs with zero ECN; DCQCN',
          '  exceeds Q_abs by 22.03 % with 6,677 ECN marks.',
          '- UNDERUTILIZED_CONTROLLER = TRUE in W2: ~4.2 % service deficit',
          '  while the queue is deep in GREEN and boost is at 75 % of MAX_BOOST.',
          '- 38 metrics are MISSING, all from the CBAP/DCQCN telemetry asymmetry;',
          '  none was substituted or zeroed.']
    open(os.path.join(D, 'S3_EXECUTIVE_SUMMARY.md'), 'w').write('\n'.join(L))

    # full metrics markdown (grouped)
    M = ['# S3 FULL METRICS', '',
         'Total rows: %d (AVAILABLE %d, MISSING %d)'
         % (len(rows), sum(1 for x in rows if x['availability'] == 'AVAILABLE'),
            len(miss)), '',
         'Canonical machine-readable form: `S3_FULL_METRICS.csv`.', '']
    cats = {}
    for x in rows:
        cats.setdefault(x['category'], []).append(x)
    for c in sorted(cats):
        M += ['## %s (%d rows)' % (c, len(cats[c])), '',
              '| metric_id | arm | window | scope | stat | value | unit | evidence |',
              '|---|---|---|---|---|---|---|---|']
        for x in cats[c][:60]:
            M.append('| `%s` | %s | %s | %s | %s | %s | %s | %s |'
                     % (x['metric_id'], x['algorithm'], x['window'],
                        x['scope'], x['statistic'], str(x['value'])[:14],
                        x['unit'], x['evidence_type']))
        if len(cats[c]) > 60:
            M.append('| ... %d more rows in the CSV | | | | | | | |'
                     % (len(cats[c]) - 60))
        M.append('')
    open(os.path.join(D, 'S3_FULL_METRICS.md'), 'w').write('\n'.join(M))

    names = sorted(f for f in os.listdir(D)
                   if os.path.isfile(os.path.join(D, f)))
    with open(os.path.join(D, 'SHA256SUMS.txt'), 'w') as fh:
        for f in names:
            if f == 'SHA256SUMS.txt':
                continue
            fh.write('%s  %s\n' % (sha(os.path.join(D, f)), f))
    print('written')
    for f in names:
        if f != 'SHA256SUMS.txt':
            print('%s  %s' % (sha(os.path.join(D, f))[:16], f))


main()
