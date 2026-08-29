import sys, collections
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
from controller_ref import *
ctl=Controller(); q=56592.0; t=0.0; confirm_at=None
BATCH=40000e3
reasons=collections.Counter()
cmd_reasons=collections.Counter()
for i in range(12000):
    confirm=(confirm_at is not None and t>confirm_at)
    active=N_FLOWS if (i<5 and t<BATCH) else 0
    d=ctl.step(q,active,True,now_ns=t,confirm=confirm)
    reasons[d['reason']]+=1
    if d['reason'] in ('new_absolute_target','lower_target_preempts_pending'):
        cmd_reasons[d['reason']]+=1
        confirm_at=t+H_GUARD_S*1e9
    if confirm: confirm_at=None
    rate=(d['boost_effective']-d['drain_effective']) if t<BATCH else -MAX_DRAIN
    q=max(0.0,q+rate*EPOCH_S/8.0); t+=EPOCH_S*1e9
print("=== reason histogram over 12000 epochs (60 ms) ===")
for r,n in reasons.most_common():
    print("  %-34s %6d  (%.1f%%)" % (r,n,100.0*n/12000))
print()
print("=== which reason produced the 285 commands? ===")
for r,n in cmd_reasons.most_common():
    print("  %-34s %6d" % (r,n))
print()
print("  So the churn IS preemption: %d of %d commands replace a pending one."
      % (cmd_reasons.get('lower_target_preempts_pending',0), sum(cmd_reasons.values())))
print("  My 8-epoch probe only covered GREEN, where the target is constant at")
print("  MAX_BOOST and nothing preempts -- which is why it showed no churn.")
print("  The churn lives in YELLOW where the law drifts continuously.")
