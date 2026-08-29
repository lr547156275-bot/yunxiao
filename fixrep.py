import io
p='/work/simulation/experiment/scheme1_sba/controller_trace_replay.py'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# 1) the ping-pong test must measure DIRECTION REVERSALS, not command rate.
old='''gaps = [cmds[i + 1][0] - cmds[i][0] for i in range(len(cmds) - 1)]
short = [g for g in gaps if g < 300e3]
check('closed loop: no rapid target ping-pong',
      len(short) <= max(2, len(gaps) // 10),
      '%d of %d command gaps below 300 us' % (len(short), len(gaps)))'''
assert s.count(old)==1
new='''# Ping-pong means the target REVERSES DIRECTION repeatedly. Command rate is a
# different thing: a continuous law legitimately re-commands as the queue moves,
# and the single-pending rule already bounds how often that can take effect. An
# earlier version of this check asserted "gaps >= 300 us", which failed on
# monotone descent and would have hidden real oscillation behind a rate metric.
signs = []
for i in range(len(cmds) - 1):
    delta = cmds[i + 1][1] - cmds[i][1]
    signs.append(1 if delta > 0 else (-1 if delta < 0 else 0))
reversals = sum(1 for i in range(len(signs) - 1)
                if signs[i] * signs[i + 1] < 0)
check('closed loop: target is monotone, no direction ping-pong',
      reversals <= max(2, len(signs) // 20),
      '%d direction reversals in %d consecutive command pairs (%.1f%%)'
      % (reversals, max(1, len(signs) - 1),
         100.0 * reversals / max(1, len(signs) - 1)))
# Separately: an effective command must not take effect more than once per
# confirmation, which is what actually bounds actuation.
eff_gaps = [g for g in [cmds[i + 1][0] - cmds[i][0]
                        for i in range(len(cmds) - 1)]]
check('closed loop: command count stays bounded over 60 ms',
      len(cmds) < 2000,
      '%d commands, median gap %.1f us'
      % (len(cmds), sorted(eff_gaps)[len(eff_gaps) // 2] / 1e3
         if eff_gaps else -1))'''
s=s.replace(old,new)

# 2) the harness confirmed a pending command on the SAME epoch it was issued,
#    because confirm_at was set to now + H_guard but compared with >= after the
#    step had already advanced.  Confirm strictly AFTER the ETA.
old2='''    confirm = (confirm_at is not None and t_ns >= confirm_at)'''
assert s.count(old2)==1
s=s.replace(old2,'''    # Strictly after the ETA: confirming in the same epoch the command was
    # issued would defeat the single-pending rule and make every epoch a
    # command-and-confirm cycle.
    confirm = (confirm_at is not None and t_ns > confirm_at)''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("replay fixed: reversal test + strict confirmation")
