import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M
TAGS=['s1','s2','s3','s6','s4','s5']; ALGOS=['dcqcn','dctcp','timely','hpcc','cbapsba']
def cell(a,tag):
    stem='m_%s_%s_seed2'%(a,tag); d=stem+'_out'
    if not os.path.exists(os.path.join(d,'flow_summary.csv')): return None
    cfg=M.read_cfg(stem+'.txt'); M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW'); srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    if inc.get('incast_done',0)<1: return None
    se=M.cfg_float(cfg,'SIMULATOR_STOP_TIME')
    bg=M.background_metrics(d,srcs,1.9,se,M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0),ids,se,inc['cct_ms'])
    sy=M.system_metrics(d,1.9,M.link_qmax('.',cfg),'/work/matrix_logs/%s.log'%stem,1.9+inc['cct_ms']/1000.0)
    return inc,bg,sy
R={}
for t in TAGS:
    for a in ALGOS:
        c=cell(a,t)
        if c: R[(t,a)]=c
print('cells available: %d/30' % len(R))
print()
print('=== p99 FCT (ms) ===')
print('  %-5s' % 'scen' + ''.join('%11s'%a.upper()[:9] for a in ALGOS))
for t in TAGS:
    line='  %-5s'%t.upper()
    for a in ALGOS:
        line += ('%11.3f'%R[(t,a)][0]['fct_p99_ms']) if (t,a) in R else '%11s'%'-'
    print(line)
print()
print('=== background retention, fixed 150ms window (%) ===')
print('  %-5s' % 'scen' + ''.join('%11s'%a.upper()[:9] for a in ALGOS))
for t in TAGS:
    line='  %-5s'%t.upper()
    for a in ALGOS:
        line += ('%11.2f'%R[(t,a)][1]['bg_fw_retention_pct']) if (t,a) in R else '%11s'%'-'
    print(line)
print()
print('=== background minimum throughput, same window (Gbps) ===')
print('  %-5s' % 'scen' + ''.join('%11s'%a.upper()[:9] for a in ALGOS))
for t in TAGS:
    line='  %-5s'%t.upper()
    for a in ALGOS:
        line += ('%11.3f'%R[(t,a)][1]['bg_fw_min_gbps']) if (t,a) in R else '%11s'%'-'
    print(line)
print()
print('=== queue peak (bytes) / ECN marks ===')
for t in TAGS:
    line='  %-5s'%t.upper()
    for a in ALGOS:
        line += ('%9.0f/%-5.0f'%(R[(t,a)][2]['queue_peak_bytes'],R[(t,a)][2]['ecn_marks'])) if (t,a) in R else '%15s'%'-'
    print(line)
