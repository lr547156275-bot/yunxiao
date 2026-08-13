# Metric collection + acceptance check for the core initial-release cells.
#
# Five groups, per the spec:
#   1 capacity trajectory : R_old / R_new before, at initial sync, after migration
#   2 batch               : BCT, per-flow FCT, initial per-flow rate
#   3 background          : throughput before/during/after (fixed window), debt
#   4 queue + safety      : peak/mean queue, queue delay vs T_msg, PFC, retx
#   5 link                : utilization, sum(applied) vs C
#
# BCT is (last completion) - (first DATA launch), NOT [1.9 s, last completion].
import csv
import os
import sys

C = 10e9
N_EXPECT = 64
BG_HOST = '65'          # source host of the background flow
BG_FLOW_ID = '0'        # its flow id; the incast batch is flow ids 1..64
BG_BATCH_ID = '0'       # SBA batch 0 is the background flow, batch 1 the incast
T_MSG_US = 838.86       # 1 MiB at 10 Gbps
FW_S = 0.150            # fixed comparison window
# Timeseries CSVs carry `time` in SECONDS (verified: first row 1e-05, last
# 2.99999 for a 3.0 s run).  sba_events / eta_feasibility carry ns.
TS_TIME_SCALE = 1.0


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return list(csv.DictReader(handle))


def num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def cfg_value(cell, key, default=0.0):
    """Read a key from the cell's own config, so scenario constants are never
    hardcoded (S3 caps background at 8.0 G, S4 at 9.5 G)."""
    path = cell + '.txt'
    if not os.path.exists(path):
        return default
    with open(path) as handle:
        for line in handle:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == key:
                return num(parts[1], default)
    return default


def analyse(cell, core, rho):
    d = cell + '_out'
    out = {'cell': cell, 'core': core, 'rho_cfg': rho}
    r_old_obs = cfg_value(cell, 'APP_RATE_CAP_BPS', 8e9)
    out['r_old_observed_gbps'] = r_old_obs / 1e9
    summary = rows(os.path.join(d, 'flow_summary.csv'))
    if not summary:
        out['status'] = 'NO_OUTPUT'
        return out

    # The background flow is the one sourced at host 65 (flow_id 0); the incast
    # batch is flow ids 1..64, all sourced elsewhere.
    bg = [r for r in summary if r['src'] == BG_HOST]
    bg_ids = set(id(r) for r in bg)
    inc = [r for r in summary if id(r) not in bg_ids]
    done = [r for r in inc if r['completed'] == '1']
    out['completed'] = '%d/%d' % (len(done), len(inc))
    out['status'] = 'OK' if len(done) == N_EXPECT else 'INCOMPLETE'

    # ---- group 2: batch -------------------------------------------------
    if done:
        starts = [num(r['start_time']) for r in done]
        fins = [num(r['finish_time']) for r in done]
        fcts = sorted(num(r['fct']) for r in done)
        out['first_data_launch_s'] = min(starts)
        out['last_completion_s'] = max(fins)
        out['bct_ms'] = (max(fins) - min(starts)) * 1e3
        out['fct_mean_ms'] = sum(fcts) / len(fcts) * 1e3
        out['fct_p99_ms'] = fcts[int(0.99 * (len(fcts) - 1))] * 1e3
        out['fct_max_ms'] = fcts[-1] * 1e3
        out['fct_spread'] = (fcts[-1] / fcts[0]) if fcts[0] else 0.0

    # ---- group 1: capacity trajectory at admission ----------------------
    # SBA batch 0 is the background flow (flow_id 0, granted its own max rate of
    # 10 G, i.e. uncapped by SBA).  The incast batch is batch 1, flow ids 1..64.
    # Summing both would put sum(grants) at 15.2 G on a 10 G link and drive
    # R_old_initial negative, so the background batch must be excluded here.
    events = rows(os.path.join(d, 'sba_events.csv'))
    adm = [r for r in events
           if 'COLLECTING->STARTUP_SENDING' in r['state_transition']
           and r['batch_id'] != BG_BATCH_ID]
    out['bg_batch_grant_gbps'] = sum(
        num(r['grant_rate']) for r in events
        if 'COLLECTING->STARTUP_SENDING' in r['state_transition']
        and r['batch_id'] == BG_BATCH_ID) / 1e9
    if adm:
        grants = [num(r['grant_rate']) for r in adm]
        total = sum(grants)
        out['n_admitted'] = len(adm)
        out['init_perflow_mbps'] = total / len(grants) / 1e6
        out['new_init_gbps'] = total / 1e9
        # R_old_initial and realized_rho are inferred as C - sum(grants), which
        # is only meaningful when the split is work-conserving.  The legacy arm
        # deliberately leaves a capacity hole (grants 1.0 G while the old side
        # holds 8.0 G), so reporting them there would print 9.0 G and -0.125 as
        # if comparable.  Left as None on that path instead.
        if core == '1':
            out['old_init_gbps'] = (C - total) / 1e9
            # R_old_observed is the background app cap, read from this cell's
            # own config: 8.0 G in S3, 9.5 G in S4.
            out['realized_rho'] = ((r_old_obs - (C - total)) / r_old_obs
                                   if r_old_obs else 0.0)
    ho = [r for r in events if 'DCQCN_OWNED' in r['state_transition']]
    out['handoffs'] = len(ho)
    out['holds'] = len([r for r in events
                        if 'ADMISSION_HOLD' in r['state_transition']])
    if adm:
        release_ns = num(adm[0]['release_time'])
        out['release_s'] = release_ns / 1e9
        if ho:
            delays = [num(r['first_feedback_time']) - num(r['release_time'])
                      for r in ho if num(r['first_feedback_time']) > 0]
            if delays:
                out['handoff_delay_us'] = min(delays) / 1e3
        # How long the initial release is actually in force before the migration
        # replan overwrites it.  If this is tiny relative to BCT, rho_init cannot
        # influence the outcome and must not be presented as if it could.
        eta_rows = rows(os.path.join(d, 'eta_feasibility.csv'))
        after = [num(r['timestamp_ns']) for r in eta_rows
                 if num(r['timestamp_ns']) >= release_ns
                 and int(num(r['new_flow_count'])) == N_EXPECT]
        if after:
            out['init_authority_us'] = (min(after) - release_ns) / 1e3

    # ---- eta feasibility trace: the migration plan at HANDOVER ----------
    # The trace runs for the whole simulation, so its LAST row describes the tail
    # (t=2.0879 s, only 4 flows left, r_old already decayed to 1.37 G).  Reading
    # that row reports the tail as if it were the handover and yields a raw
    # pre-clamp eta_feasible of -6.01.  The row that describes the handover is
    # the first epoch with the full batch present (new_flow_count == N).
    eta = rows(os.path.join(d, 'eta_feasibility.csv'))
    if eta:
        full = [r for r in eta if int(num(r['new_flow_count'])) == N_EXPECT]
        plan = full[0] if full else eta[0]
        out['eta_base'] = num(plan['eta_base'])
        # Raw column value; may be negative before the max(0,.) clamp.  What the
        # algorithm uses is eta_effective.
        out['eta_feasible_raw'] = num(plan['eta_feasible'])
        out['eta_feasible'] = max(0.0, num(plan['eta_feasible']))
        out['eta_effective'] = num(plan['eta_effective'])
        out['r_old_at_plan_gbps'] = num(plan['r_old_bps']) / 1e9
        out['plan_flow_count'] = int(num(plan['new_flow_count']))
        out['old_final_gbps'] = num(plan['old_target_sum_bps']) / 1e9
        out['new_final_gbps'] = num(plan['new_target_sum_bps']) / 1e9
        out['sum_final_gbps'] = num(plan['final_sum_target_bps']) / 1e9
        out['perflow_final_mbps'] = (out['new_final_gbps'] * 1e3
                                     / out['plan_flow_count']
                                     if out['plan_flow_count'] else 0.0)
        out['epochs'] = len(eta)
        out['infeasible_epochs'] = len([r for r in eta
                                        if r['feasible'] in ('0', 'false')])
        # Monotonicity is a property of the whole trajectory, not two endpoints.
        full_rows = full if full else eta
        olds = [num(r['old_target_sum_bps']) for r in full_rows]
        news = [num(r['new_target_sum_bps']) for r in full_rows]
        out['old_target_nonincreasing'] = all(
            olds[i + 1] <= olds[i] + 1e3 for i in range(len(olds) - 1))
        out['new_target_nondecreasing'] = all(
            news[i + 1] >= news[i] - 1e3 for i in range(len(news) - 1))
        out['full_batch_epochs'] = len(full)

    # ---- group 3: background -------------------------------------------
    if bg:
        first = bg[0]
        out['bg_acked_gb'] = num(first['acked_bytes']) * 8 / 1e9
        out['bg_completed'] = first['completed']
        out['bg_retx_bytes'] = num(first['retx_bytes'])
    # Background flow is flow_id 0 (host 65 is its SOURCE, not its flow id).
    flow_ts = rows(os.path.join(d, 'selected_flow_timeseries.csv'))
    bg_ts = [r for r in flow_ts if r.get('flow_id') == BG_FLOW_ID]
    if done and bg_ts:
        def rate(lo, hi):
            # `time` is in seconds here, not ns.
            sel = [r for r in bg_ts
                   if lo <= num(r['time']) * TS_TIME_SCALE <= hi]
            if len(sel) < 2:
                return 0.0
            # snd_una is cumulative acknowledged bytes; differencing it over the
            # window is robust to whether a per-sample delta column exists.
            span = (num(sel[-1]['time']) - num(sel[0]['time'])) * TS_TIME_SCALE
            byts = num(sel[-1]['snd_una']) - num(sel[0]['snd_una'])
            return byts * 8 / span / 1e9 if span > 0 else 0.0
        t0 = out['first_data_launch_s']
        t1 = out['last_completion_s']
        out['bg_before_gbps'] = rate(t0 - FW_S, t0)
        out['bg_during_gbps'] = rate(t0, t1)
        out['bg_fw_after_gbps'] = rate(t1, t1 + FW_S)

    # ---- group 4/5: queue, safety, link --------------------------------
    link_ts = rows(os.path.join(d, 'selected_link_timeseries.csv'))
    if link_ts:
        queue = [num(r['queue_bytes']) for r in link_ts]
        util = [num(r['utilization']) for r in link_ts]
        out['q_peak_bytes'] = max(queue)
        out['q_mean_bytes'] = sum(queue) / len(queue)
        out['q_peak_delay_us'] = max(queue) * 8 / 10e9 * 1e6
        out['q_peak_vs_tmsg'] = out['q_peak_delay_us'] / T_MSG_US
        out['pfc_pause_ns'] = sum(num(r.get('pfc_pause_ns_delta', 0))
                                  for r in link_ts)
        out['pfc_events'] = sum(num(r.get('pfc_event_delta', 0))
                                for r in link_ts)
        out['util_mean'] = sum(util) / len(util)
        if done:
            win = [r for r in link_ts
                   if out['first_data_launch_s']
                   <= num(r['time']) * TS_TIME_SCALE
                   <= out['last_completion_s']]
            if win:
                out['util_during_batch'] = (
                    sum(num(r['utilization']) for r in win) / len(win))
                out['q_peak_during_bytes'] = max(num(r['queue_bytes'])
                                                 for r in win)
    out['retx_total'] = sum(num(r['retx_bytes']) for r in summary)
    if out.get('init_authority_us') and out.get('bct_ms'):
        out['init_authority_frac'] = (out['init_authority_us'] / 1e3
                                      / out['bct_ms'])
    return out


CELLS = [('cr_s3_legacy5050', '0', '-'),
         ('cr_s3_rho000', '1', '0.0'),
         ('cr_s3_rho040', '1', '0.4'),
         ('cr_s3_rho060', '1', '0.6')]
if len(sys.argv) > 1:
    CELLS = [(sys.argv[1], '1', sys.argv[2] if len(sys.argv) > 2 else '?')]

res = [analyse(cell, core, rho) for cell, core, rho in CELLS]
LABELS = [r['cell'].replace('cr_s3_', '').replace('cr_s4_', '') for r in res]


def table(title, keys, fmt='%.4f'):
    print('')
    print('=== %s ===' % title)
    header = '  %-26s' % 'metric'
    for label in LABELS:
        header += '%18s' % label
    print(header)
    for key, label in keys:
        line = '  %-26s' % label
        for r in res:
            value = r.get(key)
            if isinstance(value, float):
                line += '%18s' % (fmt % value)
            else:
                line += '%18s' % ('-' if value is None else str(value))
        print(line)


table('status', [('status', 'status'), ('completed', 'incast completed'),
                 ('n_admitted', 'admitted flows'),
                 ('holds', 'admission holds'), ('handoffs', 'handoffs')])
table('1. capacity trajectory (Gbps)', [
    ('r_old_observed_gbps', 'R_old observed (cfg)'),
    ('old_init_gbps', 'R_old initial'), ('new_init_gbps', 'R_new initial'),
    ('realized_rho', 'realized rho_init'),
    ('r_old_at_plan_gbps', 'r_old at plan row'),
    ('plan_flow_count', 'flows at plan row'),
    ('eta_base', 'eta_base'),
    ('eta_feasible', 'eta_feasible (clamped)'),
    ('eta_feasible_raw', 'eta_feasible (raw)'),
    ('eta_effective', 'eta_final'),
    ('old_final_gbps', 'R_old final'), ('new_final_gbps', 'R_new final'),
    ('perflow_final_mbps', 'final per-flow Mbps'),
    ('sum_final_gbps', 'sum final (C=10)'),
    ('epochs', 'replan epochs total'),
    ('full_batch_epochs', 'full-batch epochs'),
    ('old_target_nonincreasing', 'R_old non-increasing'),
    ('new_target_nondecreasing', 'R_new non-decreasing'),
    ('infeasible_epochs', 'infeasible epochs'),
    ('bg_batch_grant_gbps', 'bg batch grant (excl.)')])
table('2. batch', [
    ('init_perflow_mbps', 'initial per-flow Mbps'),
    ('first_data_launch_s', 'first DATA launch s'),
    ('last_completion_s', 'last completion s'),
    ('bct_ms', 'BCT ms (last - launch)'),
    ('fct_mean_ms', 'FCT mean ms'), ('fct_p99_ms', 'FCT p99 ms'),
    ('fct_max_ms', 'FCT max ms'), ('fct_spread', 'FCT max/min'),
    ('init_authority_us', 'rho_init authority us'),
    ('handoff_delay_us', 'handoff delay us'),
    ('init_authority_frac', 'authority / BCT')])
table('3. background', [
    ('bg_before_gbps', 'bg before Gbps'),
    ('bg_during_gbps', 'bg during Gbps'),
    ('bg_fw_after_gbps', 'bg after Gbps (fw)'),
    ('bg_acked_gb', 'bg acked Gb'), ('bg_retx_bytes', 'bg retx bytes')])
table('4. queue + safety', [
    ('q_peak_bytes', 'queue peak B'),
    ('q_peak_during_bytes', 'queue peak in batch B'),
    ('q_mean_bytes', 'queue mean B'),
    ('q_peak_delay_us', 'peak queue delay us'),
    ('q_peak_vs_tmsg', 'peak delay / T_msg'),
    ('pfc_pause_ns', 'PFC pause ns'), ('pfc_events', 'PFC events'),
    ('retx_total', 'retx bytes total')])
table('5. link', [('util_mean', 'util mean'),
                  ('util_during_batch', 'util in batch')])

print('')
print('=== acceptance: core rho_init = 0.4 ===')
target = next((x for x in res if x['rho_cfg'] == '0.4'), None)
legacy = next((x for x in res if x['core'] == '0'), None)
if target is None:
    print('  rho=0.4 cell absent from this run')
    sys.exit(0)

checks = []


def check(name, ok, detail):
    checks.append((name, ok, detail))


RHO = float(target['rho_cfg'])
R_OLD = target.get('r_old_observed_gbps', 8.0)
EXP_OLD_INIT = R_OLD * (1.0 - RHO)
EXP_NEW_INIT = 10.0 - EXP_OLD_INIT
print('  reference: R_old_observed = %.2f G, rho = %.2f  ->  expect initial '
      'old %.2f G / new %.2f G' % (R_OLD, RHO, EXP_OLD_INIT, EXP_NEW_INIT))

check('initial old ~= %.2f G' % EXP_OLD_INIT,
      abs(target.get('old_init_gbps', 0) - EXP_OLD_INIT) < 0.3,
      'got %.3f G' % target.get('old_init_gbps', 0))
check('initial new ~= %.2f G' % EXP_NEW_INIT,
      abs(target.get('new_init_gbps', 0) - EXP_NEW_INIT) < 0.3,
      'got %.3f G' % target.get('new_init_gbps', 0))
check('realized rho ~= %.2f' % RHO,
      abs(target.get('realized_rho', 0) - RHO) < 0.05,
      'requested %.4f, realized %.4f' % (RHO, target.get('realized_rho', 0)))
check('no 50:50 on the core path',
      abs(target.get('init_perflow_mbps', 0) - 15.625) > 1.0,
      'core %.3f Mbps vs legacy %.3f Mbps'
      % (target.get('init_perflow_mbps', 0),
         legacy.get('init_perflow_mbps', -1) if legacy else -1))
# Final targets are checked against eta_final as the trace itself reports it,
# rather than a memorized 3.6/6.4, so this verifies internal consistency of
# (eta_base, eta_feasible, rho) -> (R_old_final, R_new_final) in any scenario.
ETA_F = target.get('eta_effective', 0.0)
EXP_OLD_FIN = R_OLD * (1.0 - ETA_F)
EXP_NEW_FIN = 10.0 - EXP_OLD_FIN
check('eta_final == max(rho, eta_base, eta_feasible)',
      abs(ETA_F - max(RHO, target.get('eta_base', 0),
                      target.get('eta_feasible', 0))) < 1e-6,
      'eta_final=%.4f vs max(rho=%.2f, base=%.4f, feas=%.4f)'
      % (ETA_F, RHO, target.get('eta_base', 0), target.get('eta_feasible', 0)))
check('final old ~= %.2f G ((1-eta_final)*R_old)' % EXP_OLD_FIN,
      abs(target.get('old_final_gbps', 0) - EXP_OLD_FIN) < 0.4,
      'got %.3f G' % target.get('old_final_gbps', 0))
check('final new ~= %.2f G' % EXP_NEW_FIN,
      abs(target.get('new_final_gbps', 0) - EXP_NEW_FIN) < 0.4,
      'got %.3f G' % target.get('new_final_gbps', 0))
check('R_old monotone non-increasing (init -> final)',
      target.get('old_final_gbps', 99) <= target.get('old_init_gbps', 0) + 0.05,
      '%.3f -> %.3f G' % (target.get('old_init_gbps', 0),
                          target.get('old_final_gbps', 0)))
check('R_new monotone non-decreasing (init -> final)',
      target.get('new_final_gbps', 0) >= target.get('new_init_gbps', 99) - 0.05,
      '%.3f -> %.3f G' % (target.get('new_init_gbps', 0),
                          target.get('new_final_gbps', 0)))
check('R_old target non-increasing across all full-batch epochs',
      target.get('old_target_nonincreasing') is True,
      '%d full-batch epochs' % target.get('full_batch_epochs', -1))
check('R_new target non-decreasing across all full-batch epochs',
      target.get('new_target_nondecreasing') is True,
      '%d full-batch epochs' % target.get('full_batch_epochs', -1))
check('plan row is the handover, not the tail',
      target.get('plan_flow_count') == N_EXPECT
      and abs(target.get('r_old_at_plan_gbps', 0) - R_OLD) < 0.2,
      'new_flow_count=%s, r_old_at_plan=%.3f G (expect %d and %.2f G)'
      % (target.get('plan_flow_count'), target.get('r_old_at_plan_gbps', -1),
         N_EXPECT, R_OLD))
check('background flow excluded from the batch',
      target.get('n_admitted') == N_EXPECT,
      'batch=%s flows, background batch granted %.2f G separately'
      % (target.get('n_admitted'), target.get('bg_batch_grant_gbps', -1)))
check('sum(target) ~= C', abs(target.get('sum_final_gbps', 0) - 10.0) < 0.3,
      'got %.3f G' % target.get('sum_final_gbps', 0))
check('64/64 incast completed', target.get('completed') == '64/64',
      str(target.get('completed')))
check('PFC = 0',
      target.get('pfc_pause_ns', 1) == 0 and target.get('pfc_events', 1) == 0,
      'pause=%.0f ns events=%.0f' % (target.get('pfc_pause_ns', -1),
                                     target.get('pfc_events', -1)))
check('retx = 0', target.get('retx_total', 1) == 0,
      '%.0f B' % target.get('retx_total', -1))
check('peak queue delay <= T_msg (838.86 us)',
      target.get('q_peak_delay_us', 1e9) <= T_MSG_US,
      '%.2f us (%.3f x T_msg)' % (target.get('q_peak_delay_us', -1),
                                  target.get('q_peak_vs_tmsg', -1)))

failed = 0
for name, ok, detail in checks:
    print('  [%s] %-38s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failed += 1
print('')
print('  %d/%d passed' % (len(checks) - failed, len(checks)))
sys.exit(1 if failed else 0)
