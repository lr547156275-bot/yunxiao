import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M
ref={'dcqcn':33.034,'dctcp':33.034,'timely':33.207,'hpcc':7.293,'cbapsba':11.097}
print('=== S6 complete: incast + background ===')
print('  %-9s %-10s %-10s %-7s %-9s %-8s %-9s %s'
      % ('algo','p99 pg3','p99 pg0','ratio','qpeak','ecn','bg_reten','bg_min'))
res={}
for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
    stem='m_%s_s6_seed2' % a; d=stem+'_out'
    fs=list(csv.DictReader(open(os.path.join(d,'flow_summary.csv'))))
    cfg=M.read_cfg(stem+'.txt')
    M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW')
    srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    bg=M.background_metrics(d,srcs,1.9,M.cfg_float(cfg,'SIMULATOR_STOP_TIME'),
                            M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0),ids,
                            M.cfg_float(cfg,'SIMULATOR_STOP_TIME'),inc['cct_ms'])
    sysm=M.system_metrics(d,1.9,400000,'/work/matrix_logs/m_%s_s6_seed2.log'%a,
                          1.9+inc['cct_ms']/1000.0)
    res[a]=inc['fct_p99_ms']
    print('  %-9s %-10.3f %-10.3f %-7.2f %-9.0f %-8.0f %-9.2f %.3f'
          % (a, inc['fct_p99_ms'], ref[a], ref[a]/inc['fct_p99_ms'],
             sysm['queue_peak_bytes'], sysm['ecn_marks'],
             bg['bg_fw_retention_pct'], bg['bg_fw_min_gbps']))
c=res['cbapsba']
print()
print('  CBAP-SBA vs fastest baseline: %.2fx slower' % (c/min(res[a] for a in res if a!='cbapsba')))
