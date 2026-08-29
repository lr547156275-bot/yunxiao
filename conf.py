import sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
from controller_ref import *
print("=== why is a command issued every 5us despite one-pending? ===")
ctl=Controller(); q=56592.0; t=0.0; confirm_at=None
for i in range(8):
    confirm=(confirm_at is not None and t>confirm_at)
    d=ctl.step(q,0,True,now_ns=t,confirm=confirm)
    print("  i=%d t=%7.1fus reason=%-32s pend=%s cmd=%s eff=%+.4fC confirm_in=%s"
          % (i,t/1e3,d['reason'],d['pending'],
             ("%+.4fC"%(d['commanded']/C)) if d['commanded'] is not None else "None",
             d['boost_effective']/C,
             ("%.1fus"%((confirm_at-t)/1e3)) if confirm_at else "-"))
    if d['reason'] in ('new_absolute_target','lower_target_preempts_pending'):
        confirm_at=t+H_GUARD_S*1e9
    if confirm: confirm_at=None
    t+=EPOCH_S*1e9
print()
print("  KEY: 'lower_target_preempts_pending' fires every epoch, because the")
print("  continuous law's desired target keeps drifting DOWNWARD as Q rises,")
print("  and my rule allows a pending command to be replaced by any LOWER one.")
print("  So the pending slot is refreshed every epoch -> never confirms ->")
print("  boost_effective stays 0 -> but the TARGET keeps being re-issued.")
print()
print("  That is a real design gap: 'a lower target may preempt' must not mean")
print("  'every infinitesimally lower target may preempt', or the pending slot")
print("  never settles and the actuation ETA never arrives.")
print("  The deadband belongs HERE -- on preemption -- not on the no-op test.")
