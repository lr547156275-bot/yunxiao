import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M
print('=== S6 (dual bottleneck, TWO background flows) ===')
print('  checks: per-flow bg0/bg1 present, and never_dipped now populated')
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    stem='m_%s_s6_seed2' % a; d=stem+'_out'
    if not os.path.exists(os.path.join(d,'flow_summary.csv')): continue
    cfg=M.read_cfg(stem+'.txt')
    M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    sim_end=M.cfg_float(cfg,'SIMULATOR_STOP_TIME')
    cap=M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0)
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW')
    srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    if inc.get('incast_done',0)<1: continue
    bg=M.background_metrics(d,srcs,1.9,sim_end,cap,ids,sim_end,inc['cct_ms'])
    def g(k,dflt=float('nan')):
        v=bg.get(k,dflt); return v if v==v else dflt
    print('  %-9s n_flows=%d  fw_reten(worst)=%6.2f%%  fw_min(worst)=%6.3f  never90=%s'
          % (a, bg['bg_n_flows'], g('bg_fw_retention_pct'), g('bg_fw_min_gbps'),
             bg.get('bg_recovery90_ms_never_dipped')))
    for i in (0,1):
        print('      bg%d: reten=%6.2f%%  min=%6.3f  before=%6.3f'
              % (i, bg.get('bg%d_fw_retention_pct'%i,float('nan')),
                 bg.get('bg%d_fw_min_gbps'%i,float('nan')),
                 bg.get('bg%d_before_gbps'%i,float('nan'))))
