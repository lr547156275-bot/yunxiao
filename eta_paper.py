# eta sweep sensitivity for the paper.  IMPORTANT: this sweep was run on the
# PRE-FREEZE binary (084da1fc), before the capacity-feasibility floor existed.
# It is still the valid evidence for the eta knob, because eta_base is the
# parameter being swept and the floor only raises eta when the base value would
# be infeasible -- but the provenance must be stated, not blurred.
import csv, os
BASE = '/work/simulation/experiment/scheme1_sba'
SRC  = os.path.join(BASE, 'eta_sweep', 'eta_sweep_s4.csv')
OUT  = os.path.join(BASE, 'paper_data')

if not os.path.exists(SRC):
    print('eta_sweep_s4.csv missing'); raise SystemExit(1)

rows = list(csv.DictReader(open(SRC)))
def f(r, k):
    v = r.get(k, '')
    if v in (None, ''): return ''
    try:
        x = float(v)
    except ValueError:
        return v
    return '' if x != x else '%.6f' % x

COLS = [('fct_mean_ms','fct_mean_ms'), ('fct_p95_ms','fct_p95_ms'),
        ('fct_p99_ms','fct_p99_ms'), ('cct_ms','cct_ms'),
        ('incast_agg_gbps','incast_agg_gbps'),
        ('bg_during_gbps','bg_during_gbps'), ('bg_min_gbps','bg_min_gbps'),
        ('bg_retention_pct','bg_retention_pct'),
        ('bg_service_debt_bytes','bg_service_debt_bytes'),
        ('queue_mean_bytes','queue_mean_bytes'),
        ('queue_p99_bytes','queue_p99_bytes'),
        ('queue_peak_bytes','queue_peak_bytes'),
        ('over_qmax_pct','over_qmax_pct'),
        ('oversub_duration_ms','oversub_duration_ms'),
        ('util_mean','util_mean'), ('ecn_marks','ecn_marks'),
        ('pfc_events','pfc_events'), ('drops','drops'),
        ('retx_bytes_total','retx_bytes_total')]

p = os.path.join(OUT, 'p3_eta_sweep_sensitivity.csv')
with open(p, 'w') as fh:
    w = csv.writer(fh)
    w.writerow(['# eta = CBAP_MIGRATION_RELEASE_RATIO swept on S4 (64x1MiB, 95% background), seed 2.'])
    w.writerow(['# PROVENANCE: run on the PRE-FREEZE binary 084da1fc, before the capacity-feasibility'])
    w.writerow(['# floor existed. eta=0.50 is the compiled default and reuses the pre-freeze S4 matrix cell.'])
    w.writerow(['# kind=cbapsba_eta are swept points; kind=reference_* are fixed baselines, not re-run.'])
    w.writerow(['eta', 'kind', 'label'] + [c[0] for c in COLS])
    for r in rows:
        kind = r.get('kind', '')
        lab = ('eta=' + r['eta']) if kind == 'cbapsba_eta' else kind.replace('reference_', '').upper()
        w.writerow([r.get('eta', ''), kind, lab] + [f(r, c[1]) for c in COLS])

# Pareto view of the knob
p2 = os.path.join(OUT, 'p4_eta_pareto_retention_vs_p99fct.csv')
with open(p2, 'w') as fh:
    w = csv.writer(fh)
    w.writerow(['# The eta knob traces a controllable frontier; HPCC and DCQCN are fixed points on it.'])
    w.writerow(['label','kind','eta','bg_retention_pct','fct_p99_ms','queue_p99_bytes','incast_agg_gbps','ecn_marks'])
    for r in rows:
        kind = r.get('kind','')
        lab = ('eta=' + r['eta']) if kind=='cbapsba_eta' else kind.replace('reference_','').upper()
        w.writerow([lab, kind, r.get('eta',''), f(r,'bg_retention_pct'), f(r,'fct_p99_ms'),
                    f(r,'queue_p99_bytes'), f(r,'incast_agg_gbps'), f(r,'ecn_marks')])

print('wrote p3_eta_sweep_sensitivity.csv (%d rows)' % len(rows))
print('wrote p4_eta_pareto_retention_vs_p99fct.csv')
