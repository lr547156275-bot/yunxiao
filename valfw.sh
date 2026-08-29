set -u
cd /work/simulation/experiment/scheme1_sba
sed -i "s|^LOGS = '/workspaces/yunxiao/matrix_logs'|LOGS = '/work/matrix_logs'|" metrics.py
python3 -c "import ast;ast.parse(open('metrics.py').read());print('  metrics.py parses OK')"
# Validate the new columns on the two pg=3 preflight cells (they have done-flag
# free dirs, so drive _background_one directly rather than via collect()).
python3 - <<'PY'
import sys, os, csv
sys.path.insert(0,'.')
import metrics as M
print('  FIXED_WINDOW_S = %.3f s' % M.FIXED_WINDOW_S)
for stem in ('pf_dcqcn_s3','pf_cbapsba_s3'):
    d=stem+'_out'
    cfg=M.read_cfg(stem+'.txt')
    M.SAMPLE_US=M.cfg_float(cfg,'CRFM_TRACE_SAMPLE_US',10.0)
    sim_end=M.cfg_float(cfg,'SIMULATOR_STOP_TIME')
    cap=M.cfg_float(cfg,'APP_RATE_CAP_BPS',0.0)
    ids=M.cfg_id_list(cfg,'APP_RATE_CAP_FLOW')
    srcs=M.bg_srcs_for(d,ids)
    inc=M.incast_metrics(d,srcs,1.9)
    bg=M.background_metrics(d,srcs,1.9,sim_end,cap,ids,sim_end,inc['cct_ms'])
    print('  --- %s ---' % stem)
    print('    cct=%.3f ms  (CCT-scoped window length)' % inc['cct_ms'])
    print('    CCT-scoped : during=%.3f G  retention=%.2f%%  min=%.3f G'
          % (bg['bg_during_gbps'], bg['bg_retention_pct'], bg['bg_min_gbps']))
    print('    FIXED 150ms: during=%.3f G  retention=%.2f%%  min=%.3f G  bytes=%.0f'
          % (bg['bg_fw_during_gbps'], bg['bg_fw_retention_pct'],
             bg['bg_fw_min_gbps'], bg['bg_fw_bytes_delivered']))
    print('    never_dipped90=%s (now populated regardless of bg flow count)'
          % bg['bg_recovery90_ms_never_dipped'])
PY
