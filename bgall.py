import csv, os, sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
os.chdir('/work/simulation/experiment/scheme1_sba')
import metrics as M

print('=== BACKGROUND flow, fixed 150 ms window from release (comparable across algos) ===')
print('  %-4s %-9s %-9s %-9s %-9s %-9s %-11s %s'
      % ('scen','algo','before','fw_during','fw_reten','fw_min','fw_bytes','cct_window'))
for tag, stop in (('s1',2.1), ('s2',2.5), ('s3',3.0)):
    for a in ('dcqcn','dctcp','timely','hpcc','cbapsba'):
        stem='m_%s_%s_seed2' % (a, tag)
        d=stem+'_out'
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
        def g(k):
            v=bg.get(k,float('nan'))
            return v if v==v else float('nan')
        print('  %-4s %-9s %-9.3f %-9.3f %-9.2f %-9.3f %-11.0f %.1f ms'
              % (tag, a, g('bg_before_gbps'), g('bg_fw_during_gbps'),
                 g('bg_fw_retention_pct'), g('bg_fw_min_gbps'),
                 g('bg_fw_bytes_delivered'), inc['cct_ms']))
    print()
