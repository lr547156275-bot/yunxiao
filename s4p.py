import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M
ref={'dcqcn':1127.321,'dctcp':1127.321,'timely':1118.975,'hpcc':60.242,'cbapsba':88.275}
print('=== S4 (64x1MiB, bg 95%) -- source of the original 12.77x claim ===')
print('  %-9s %-11s %-11s %-7s %-9s %-8s %-9s %-8s %s'
      % ('algo','p99 pg3','p99 pg0','ratio','inc_gbps','qpeak','ecn','bg_reten','bg_min'))
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    stem='m_%s_s4_seed2' % a; d=stem+'_out'
    if not os.path.exists(os.path.join(d,'flow_summary.csv')): continue
    cfg=M.read_cfg(stem+'.txt')
    M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW')
    srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    if inc.get('incast_done',0)<64: continue
    se=M.cfg_float(cfg,'SIMULATOR_STOP_TIME')
    bg=M.background_metrics(d,srcs,1.9,se,M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0),ids,se,inc['cct_ms'])
    sysm=M.system_metrics(d,1.9,400000,'/work/matrix_logs/%s.log'%stem,1.9+inc['cct_ms']/1000.0)
    print('  %-9s %-11.3f %-11.3f %-7.2f %-9.3f %-8.0f %-8.0f %-9.2f %.3f'
          % (a, inc['fct_p99_ms'], ref[a], ref[a]/inc['fct_p99_ms'],
             inc['incast_agg_gbps'], sysm['queue_peak_bytes'], sysm['ecn_marks'],
             bg['bg_fw_retention_pct'], bg['bg_fw_min_gbps']))
