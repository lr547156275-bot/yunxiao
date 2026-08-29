import io
p='/work/simulation/experiment/scheme1_sba/controller_ref.py'
s=io.open(p,encoding='utf-8',errors='surrogateescape').read()
old='''        # Direction hysteresis: no re-acceleration while a descent is pending,
        # and none after it lands until Q_stop is below the rearm line.
        if desired > 0.0 and (self.descending or self.rearm_required):
            desired = min(0.0, self._current_u())'''
assert s.count(old)==1
new='''        # Direction hysteresis: no RE-ACCELERATION while a descent is pending,
        # and none after it lands until Q_stop falls below the rearm line.
        #
        # The lock must HOLD the current target, not force u to zero. An earlier
        # version used min(0, current_u), which clamped u to exactly 0 and
        # created a NEW fixed point (dQ/dt = 0) at whatever queue the descent
        # landed on -- observed frozen at 527,217 B instead of converging to the
        # intended u=0 equilibrium at 766,266 B. Clamping to the current value
        # forbids increases while still allowing the law to command drain when
        # the queue keeps rising.
        if self.descending or self.rearm_required:
            cur_u = self._current_u()
            if desired > cur_u:
                desired = cur_u'''
s=s.replace(old,new)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(s)
print("hysteresis fixed: holds current target instead of zeroing")
