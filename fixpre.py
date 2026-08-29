import io
p='/work/simulation/experiment/scheme1_sba/controller_ref.py'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# Add the preemption deadband, derived from the per-flow actuation quantum.
old='''REARM_MARGIN = N_FLOWS * ON_WIRE + MAX_BOOST * H_GUARD_S / 8.0
REARM_BYTES = SOFT_BYTES - REARM_MARGIN'''
assert s.count(old)==1
s=s.replace(old, old+'''

# Preemption deadband. A pending command may only be replaced by a MEANINGFULLY
# lower target, not by an infinitesimally lower one -- otherwise the continuous
# law refreshes the pending slot every epoch, the actuation ETA is pushed back
# forever, and boost_effective never catches up to the target. Measured: 281 of
# 285 commands were such preemptions, with pending_inflight holding 95.8% of
# epochs.
#
# The quantum is per-flow, because a command re-rates each flow by u/N: the
# smallest change worth actuating moves one on-wire packet per guard window.
# Derived from existing quantities (ON_WIRE, H_GUARD_S); no new ratio.
PREEMPT_DEADBAND = ON_WIRE * 8.0 / H_GUARD_S      # ~47.9 Mbps''')

old2='''            if desired < self.commanded - 1.0:
                self._issue(desired, now_ns)
                self.reason = 'lower_target_preempts_pending\''''
assert s.count(old2)==1
s=s.replace(old2,'''            if desired < self.commanded - PREEMPT_DEADBAND:
                self._issue(desired, now_ns)
                self.reason = 'lower_target_preempts_pending\'''')

# The no-op test should use the same quantum, for the same reason.
old3='''        elif abs(desired - cur) < 1.0:
            self.reason = 'noop_target_unchanged\''''
assert s.count(old3)==1
s=s.replace(old3,'''        elif abs(desired - cur) < PREEMPT_DEADBAND:
            self.reason = 'noop_target_unchanged\'''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("preemption deadband added: %.3f Mbps" % (1048*8.0/175e-6/1e6))
