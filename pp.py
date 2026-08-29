import sys, os
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
from controller_ref import *
ctl=Controller(); q=56592.0; t=0.0; confirm_at=None
cmds=[]
BATCH=40000e3
for i in range(12000):
    confirm=(confirm_at is not None and t>=confirm_at)
    active=N_FLOWS if (i<5 and t<BATCH) else 0
    d=ctl.step(q,active,True,now_ns=t,confirm=confirm)
    if d['reason'] in ('new_absolute_target','lower_target_preempts_pending'):
        confirm_at=t+H_GUARD_S*1e9
        cmds.append((t,d['commanded'],d['zone']))
    if confirm: confirm_at=None
    rate=(d['boost_effective']-d['drain_effective']) if t<BATCH else -MAX_DRAIN
    q=max(0.0,q+rate*EPOCH_S/8.0); t+=EPOCH_S*1e9
print("=== is it ping-pong (alternating direction) or monotone descent? ===")
print("  total commands: %d over 60 ms" % len(cmds))
gaps=[cmds[i+1][0]-cmds[i][0] for i in range(len(cmds)-1)]
print("  gap min=%.1f us  median=%.1f us  max=%.1f us"
      % (min(gaps)/1e3, sorted(gaps)[len(gaps)//2]/1e3, max(gaps)/1e3))
# direction reversals
signs=[]
for i in range(len(cmds)-1):
    d=cmds[i+1][1]-cmds[i][1]
    signs.append(1 if d>0 else (-1 if d<0 else 0))
rev=sum(1 for i in range(len(signs)-1) if signs[i]*signs[i+1]<0)
print("  direction reversals: %d of %d consecutive pairs (%.1f%%)"
      % (rev, len(signs)-1, 100.0*rev/max(1,len(signs)-1)))
print()
print("  first 12 targets:", " ".join("%+.4f" % (c[1]/C) for c in cmds[:12]))
print("  last  12 targets:", " ".join("%+.4f" % (c[1]/C) for c in cmds[-12:]))
print()
print("=== verdict ===")
if rev <= 2:
    print("  MONOTONE, not ping-pong.  %d reversals means the target walks in one" % rev)
    print("  direction as the queue rises, which is what a continuous law does.")
    print("  My test asserted 'gaps >= 300us', which measures command RATE, not")
    print("  oscillation.  The single-pending rule already bounds the rate to one")
    print("  per confirmation (~%.0f us observed median)." % (sorted(gaps)[len(gaps)//2]/1e3))
    print("  The correct test is REVERSALS, not gap width.")
else:
    print("  Genuine oscillation: %d reversals." % rev)
