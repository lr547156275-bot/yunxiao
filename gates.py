import csv, os, collections
os.chdir('/work/simulation/experiment/scheme1_sba')
f='au_s3_rho090_out/actuation.csv'
rows=list(csv.DictReader(open(f)))
print("=== stage counts ===")
c=collections.Counter(r['stage'] for r in rows)
for s,k in c.most_common(): print("  %-32s %d" % (s,k))
print()
g1={}; g2={}; g3={}
for r in rows:
    gen=int(r['generation']); st=r['stage']
    if st=='rate_command': g1[gen]=r
    elif st=='sender_rate_effect': g2[gen]=r
    elif st=='first_affected_at_bottleneck': g3[gen]=r
print("=== generation correspondence ===")
print("  distinct generations: cmd=%d sender=%d bottleneck=%d" % (len(g1),len(g2),len(g3)))
print("  sender gens not in cmd      : %d" % len(set(g2)-set(g1)))
print("  bottleneck gens not in sender: %d" % len(set(g3)-set(g2)))
full=set(g1)&set(g2)&set(g3)
print("  FULL triples (all 3 stages) : %d" % len(full))
print("  cmd without sender          : %d" % len(set(g1)-set(g2)))
print("  sender without bottleneck   : %d" % len(set(g2)-set(g3)))
# duplicates
dup=[gen for gen,k in collections.Counter(
        int(r['generation']) for r in rows if r['stage']=='rate_command').items() if k>1]
print("  duplicate rate_command gens : %d" % len(dup))
neg=0
for gen in full:
    if int(g2[gen]['delta_prev_stage_ns'])<0 or int(g3[gen]['delta_prev_stage_ns'])<0:
        neg+=1
print("  negative-delay triples      : %d" % neg)
print()
def stats(name, vals):
    if not vals: print("  %-10s (no data)"%name); return
    vals=sorted(vals)
    n=len(vals)
    def p(q): return vals[min(n-1,int(q*(n-1)))]
    print("  %-10s n=%-6d min=%8.3f mean=%8.3f p50=%8.3f p95=%8.3f p99=%8.3f max=%9.3f"
          % (name,n,vals[0]/1e3,sum(vals)/n/1e3,p(0.50)/1e3,p(0.95)/1e3,p(0.99)/1e3,vals[-1]/1e3))
print("=== latency components (microseconds), from FULL triples only ===")
H_sender=[int(g2[g]['delta_prev_stage_ns']) for g in full]
H_path  =[int(g3[g]['delta_prev_stage_ns']) for g in full]
H_cmd2bn=[int(g3[g]['delta_from_command_ns']) for g in full]
stats("H_sender", H_sender)          # rate_command -> sender effect
stats("H_path",   H_path)            # sender effect -> bottleneck
stats("H_cmd2bn", H_cmd2bn)          # rate_command -> bottleneck
H_OBS=5000                            # measured telemetry sample->delivery lag
stats("H_obs",   [H_OBS]*len(full))
stats("H_eff",   [h+H_OBS for h in H_cmd2bn])
print()
print("  H_obs is the measured sample->delivery lag (port_summary), constant 5.0 us")
print("  H_eff = H_obs + H_sender + H_path = H_obs + H_cmd2bn")
