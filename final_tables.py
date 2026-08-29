# Build the old-vs-new comparison and Pareto data once all 30 cells are in.
# Pure reorganisation of completed runs; no simulation, no algorithm change.
import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M

TAGS=['s1','s2','s3','s6','s4','s5']
ALGOS=['dcqcn','dctcp','timely','hpcc','cbapsba']
OUT='paper_data_pg3'
os.makedirs(OUT, exist_ok=True)

# pg0 reference values, read from the archived (invalid) report.
old={}
p='pg0_invalid/final_report/final_results.csv'
if os.path.exists(p):
    for r in csv.DictReader(open(p)):
        old[(r['scenario_tag'], r['algorithm'])]=r

def cell(a, tag):
    stem='m_%s_%s_seed2'%(a,tag); d=stem+'_out'
    if not os.path.exists(os.path.join(d,'flow_summary.csv')): return None
    cfg=M.read_cfg(stem+'.txt')
    M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    M.BASE_RTT_US=M.base_rtt_us_from_log('/work/matrix_logs/%s.log'%stem)
    se=M.cfg_float(cfg,'SIMULATOR_STOP_TIME')
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW')
    srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    if inc.get('incast_done',0)<1: return None
    row=dict(scenario_tag=tag, algorithm=a)
    row.update(inc)
    row.update(M.background_metrics(d,srcs,1.9,se,
        M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0),ids,se,inc['cct_ms']))
    row.update(M.system_metrics(d,1.9,M.link_qmax('.',cfg),
        '/work/matrix_logs/%s.log'%stem, 1.9+inc['cct_ms']/1000.0))
    return row

rows=[]
for tag in TAGS:
    for a in ALGOS:
        r=cell(a,tag)
        if r: rows.append(r)
print('collected %d cells' % len(rows))
if len(rows)<30:
    print('  (matrix still running; run again when 30/30)')

# full results
keys=['scenario_tag','algorithm']+[k for k in rows[0] if k not in ('scenario_tag','algorithm')]
with open(os.path.join(OUT,'final_results_pg3.csv'),'w') as f:
    w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore'); w.writeheader()
    for r in rows: w.writerow(r)

# old vs new
with open(os.path.join(OUT,'pg0_vs_pg3_comparison.csv'),'w') as f:
    w=csv.writer(f)
    w.writerow(['# pg0 (INVALID: background on ECN-exempt queue 0) vs pg3 (corrected)'])
    w.writerow(['# ratio = pg0/pg3 for latency-like metrics; >1 means pg3 is better'])
    w.writerow(['scenario','algorithm','metric','pg0_invalid','pg3_corrected','ratio_or_delta'])
    for r in rows:
        o=old.get((r['scenario_tag'],r['algorithm']))
        if not o: continue
        for k in ('fct_mean_ms','fct_p99_ms','cct_ms','incast_agg_gbps',
                  'bg_retention_pct','bg_min_gbps','queue_peak_bytes','ecn_marks'):
            try: ov=float(o.get(k,'') or 'nan'); nv=float(r.get(k,float('nan')))
            except ValueError: continue
            if ov!=ov or nv!=nv: continue
            rel = (ov/nv if nv else float('nan')) if 'fct' in k or 'cct' in k else (nv-ov)
            w.writerow([r['scenario_tag'],r['algorithm'],k,'%.6f'%ov,'%.6f'%nv,'%.4f'%rel])

# Pareto, using the FIXED window so it is comparable across algorithms
for name,xk,yk in (('pareto_bgretention_vs_p99fct.csv','bg_fw_retention_pct','fct_p99_ms'),
                   ('pareto_bgmin_vs_p99fct.csv','bg_fw_min_gbps','fct_p99_ms'),
                   ('pareto_queue_vs_p99fct.csv','queue_p99_bytes','fct_p99_ms')):
    with open(os.path.join(OUT,name),'w') as f:
        w=csv.writer(f)
        w.writerow(['# corrected (pg3) results; background metrics use the fixed %.0f ms window' % (M.FIXED_WINDOW_S*1000)])
        w.writerow(['scenario','algorithm',xk,yk])
        for r in rows:
            x,y=r.get(xk),r.get(yk)
            if x is None or y is None or x!=x or y!=y: continue
            w.writerow([r['scenario_tag'],r['algorithm'],'%.6f'%x,'%.6f'%y])
print('wrote final_results_pg3.csv, pg0_vs_pg3_comparison.csv, 3 pareto CSVs into %s/' % OUT)
