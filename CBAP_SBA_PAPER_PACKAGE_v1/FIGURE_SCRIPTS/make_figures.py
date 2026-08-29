# -*- coding: utf-8 -*-
# CBAP_SBA_PAPER_PACKAGE_v1 figures: reads FIGURE_DATA/*.csv, writes
# FIGURES/figN_*.{pdf,svg,png}.  Pure matplotlib, no seaborn.
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P = os.path.dirname(os.path.abspath(__file__)) + '/..'
FD = P + '/FIGURE_DATA'
FG = P + '/FIGURES'
os.path.isdir(FG) or os.makedirs(FG)
AL = ['dcqcn', 'dctcp', 'timely', 'hpcc', 'cbapsba']
LBL = {'dcqcn': 'DCQCN', 'dctcp': 'DCTCP', 'timely': 'TIMELY',
       'hpcc': 'HPCC', 'cbapsba': 'CBAP-SBA'}
CLR = {'dcqcn': '#888888', 'dctcp': '#7f9fc4', 'timely': '#c4a97f',
       'hpcc': '#a97fc4', 'cbapsba': '#c0392b'}
SC = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']


def rd(name):
    return list(csv.DictReader(open(FD + '/' + name)))


def save(fig, name):
    for ext in ('pdf', 'svg', 'png'):
        fig.savefig('%s/%s.%s' % (FG, name, ext), bbox_inches='tight',
                    dpi=150 if ext == 'png' else None)
    plt.close(fig)
    print('FIGURES/' + name)


def grouped_bars(rows, value, ylabel, name, logy=False, div=1.0):
    fig, ax = plt.subplots(figsize=(8, 3.2))
    w = 0.16
    for i, a in enumerate(AL):
        xs, ys = [], []
        for j, s in enumerate(SC):
            v = next((r[value] for r in rows
                      if r['scenario'] == s and r['algorithm'] == a), None)
            if v not in (None, 'NA', ''):
                xs.append(j + (i - 2) * w)
                ys.append(float(v) / div)
        ax.bar(xs, ys, width=w, label=LBL[a], color=CLR[a])
    ax.set_xticks(range(len(SC)))
    ax.set_xticklabels(SC)
    ax.set_ylabel(ylabel)
    if logy:
        ax.set_yscale('log')
    ax.legend(ncol=5, fontsize=8, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    save(fig, name)


r1 = rd('fig1_completion.csv')
grouped_bars(r1, 'CCT_ms', 'CCT (ms)', 'fig1_cct', logy=True)
r2 = rd('fig2_fct_tails.csv')
grouped_bars(r2, 'FCT_p99_us', 'FCT p99 (us)', 'fig2_fct_p99', logy=True)
r3 = rd('fig3_queue.csv')
grouped_bars(r3, 'queue_p99_B', 'worst-link queue p99 (KB)',
             'fig3_queue_p99', logy=True, div=1024.0)
grouped_bars(r3, 'queue_delay_max_us', 'max queuing delay (us)',
             'fig3b_qdelay_max', logy=True)
r4 = rd('fig4_goodput.csv')
grouped_bars(r4, 'batch_goodput_gbps', 'batch goodput (Gbps)',
             'fig4_goodput')

# fig5: S3 control timeline (handoff + batch windows)
ev = rd('fig5_s3_timeline.csv')
mig = [(float(r['time_ns']) / 1e9, float(r['applied_bps']) / 1e9)
       for r in ev if r['event'] == 'migration_dispatch'
       and r['role_or_zone_or_state'] == 'bg' and r['applied_bps']]
ep = [(float(r['time_ns']) / 1e9, float(r['queue_B_or_phase'] or 0) / 1024,
       float(r['applied_bps'] or 0) / 1e9)
      for r in ev if r['event'] == 'epoch']
fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
if mig:
    axes[0].step([t for t, v in mig], [v for t, v in mig], where='post',
                 color=CLR['cbapsba'], lw=1.5, label='background applied rate')
if ep:
    axes[0].plot([t for t, q, ag in ep], [ag for t, q, ag in ep],
                 color='#2c3e50', lw=0.8, alpha=0.7,
                 label='aggregate applied (incast+bg)')
axes[0].set_ylabel('rate (Gbps)')
axes[0].legend(fontsize=8)
axes[0].grid(alpha=0.3)
if ep:
    axes[1].plot([t for t, q, ag in ep], [q for t, q, ag in ep],
                 color='#16a085', lw=0.8, label='bottleneck queue (KB)')
axes[1].set_ylabel('queue (KB)')
axes[1].set_xlabel('time (s)')
axes[1].set_xlim(1.998, 2.075)
axes[1].legend(fontsize=8)
axes[1].grid(alpha=0.3)
axes[0].set_title('S3: capacity migration 8G->0.1G->8G and queue '
                  '(CBAP-SBA, mx_s3_cbapsba)', fontsize=9)
save(fig, 'fig5_s3_timeline')

# fig6: pareto frontier
fr = rd('fig6_pareto_frontier.csv')
fig, ax = plt.subplots(figsize=(6, 4.2))
for a in ('dcqcn', 'dctcp', 'timely', 'hpcc'):
    pts = [(float(r['q_p99_B']) / 1024, float(r['CCT_ms'])) for r in fr
           if r['algo'] == a]
    pts.sort()
    ax.plot([x for x, y in pts], [y for x, y in pts], 'o--', ms=5,
            color=CLR[a], label=LBL[a], alpha=0.85)
cb = [(float(r['q_p99_B']) / 1024, float(r['CCT_ms'])) for r in fr
      if r['algo'] == 'cbapsba']
ax.scatter([x for x, y in cb], [y for x, y in cb], marker='*', s=260,
           color=CLR['cbapsba'], zorder=5, label='CBAP-SBA (fixed)')
ax.set_xscale('log')
ax.set_xlabel('worst-link queue p99 (KB, log)')
ax.set_ylabel('CCT (ms)')
ax.set_title('S3 baseline parameter frontier (21 points) vs CBAP-SBA',
             fontsize=9)
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
save(fig, 'fig6_pareto')

# fig7: BMAX sensitivity
r7 = rd('fig7_cbap_sensitivity.csv')
fig, ax1 = plt.subplots(figsize=(6, 3.4))
xs = [float(r['BMAX_ratio']) for r in r7]
ax1.plot(xs, [float(r['CCT_ms']) for r in r7], 'o-',
         color=CLR['cbapsba'], label='CCT (ms)')
ax1.set_xlabel('BMAX (fraction of C)')
ax1.set_ylabel('CCT (ms)', color=CLR['cbapsba'])
ax2 = ax1.twinx()
ax2.plot(xs, [float(r['queue_max_B']) / 1024 for r in r7], 's--',
         color='#16a085', label='queue max (KB)')
ax2.set_yscale('log')
ax2.set_ylabel('queue max (KB, log)', color='#16a085')
sel = [r for r in r7 if r['note'] == 'SELECTED'][0]
ax1.axvline(float(sel['BMAX_ratio']), color='k', ls=':', alpha=0.5)
ax1.grid(alpha=0.3)
ax1.set_title('CBAP-SBA BMAX sensitivity (S3)', fontsize=9)
save(fig, 'fig7_bmax_sensitivity')

# fig8: ablation
r8 = rd('fig8_ablation.csv')
fig, ax1 = plt.subplots(figsize=(7, 3.4))
arms = [r['arm'] for r in r8]
cs = ['#888888' if 'INVALID' in r['status'] else CLR['cbapsba'] for r in r8]
ax1.bar(range(len(arms)), [float(r['CCT_ms']) for r in r8], color=cs)
ax1.set_xticks(range(len(arms)))
ax1.set_xticklabels([a.replace(' ', '\n') for a in arms], fontsize=8)
ax1.set_ylabel('CCT (ms)')
for i, r in enumerate(r8):
    ax1.text(i, float(r['CCT_ms']) + 1,
             'qmax\n%.0fKB' % (float(r['queue_max_B']) / 1024),
             ha='center', fontsize=7)
    if 'INVALID' in r['status']:
        ax1.text(i, float(r['CCT_ms']) / 2, 'INVALID\nPOLICY', ha='center',
                 fontsize=7, color='white')
ax1.grid(axis='y', alpha=0.3)
ax1.set_title('Ablation (S3): admission/cap -> migration -> leased boost',
              fontsize=9)
save(fig, 'fig8_ablation')

# fig9: buffer/ECN robustness
r9 = rd('fig9_robustness.csv')
fig, ax = plt.subplots(figsize=(8, 3.4))
buf = [r for r in r9 if r['variant'].startswith('buffer')]
labels, pfc, cct = [], [], []
for a in AL:
    for r in buf:
        if r['algorithm'] == a and '2MB' in r['variant']:
            labels.append(LBL[a])
            pfc.append(int(r['PFC_count']))
ax.bar(range(len(labels)), pfc,
       color=[CLR[a] for a in AL])
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel('PFC pause events (2 MB buffer, S3)')
for i, v in enumerate(pfc):
    ax.text(i, v + 150, str(v), ha='center', fontsize=8)
ax.set_title('Shallow-buffer annex: PFC exposure (8 MB run had 0 for all)',
              fontsize=9)
ax.grid(axis='y', alpha=0.3)
save(fig, 'fig9_pfc_shallow_buffer')

# fig10: S6 per-link queues + completion
r10a = rd('fig10_s6_per_link.csv')
r10b = rd('fig10_s6_completion.csv')
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
w = 0.35
for li, lk in enumerate(sorted(set(r['link_id'] for r in r10a))):
    ys = []
    for a in AL:
        v = next(r['queue_max_B'] for r in r10a
                 if r['algorithm'] == a and r['link_id'] == lk)
        ys.append(float(v) / 1024)
    axes[0].bar([i + (li - 0.5) * w for i in range(len(AL))], ys, width=w,
                label='link %s' % lk, alpha=0.85)
axes[0].set_yscale('log')
axes[0].set_xticks(range(len(AL)))
axes[0].set_xticklabels([LBL[a] for a in AL], fontsize=7)
axes[0].set_ylabel('queue max (KB, log)')
axes[0].legend(fontsize=8)
axes[0].set_title('S6: per-bottleneck queue max', fontsize=9)
axes[0].grid(axis='y', alpha=0.3)
axes[1].bar(range(len(AL)), [float(r['CCT_ms']) for r in r10b],
            color=[CLR[a] for a in AL])
axes[1].set_xticks(range(len(AL)))
axes[1].set_xticklabels([LBL[a] for a in AL], fontsize=7)
axes[1].set_ylabel('CCT (ms)')
axes[1].set_title('S6: completion (CBAP-SBA = TIE with DCQCN)', fontsize=9)
axes[1].grid(axis='y', alpha=0.3)
save(fig, 'fig10_s6')
print('ALL FIGURES DONE')
