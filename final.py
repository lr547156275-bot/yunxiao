import csv, os, collections
os.chdir('/work/simulation/experiment/scheme1_sba')
rows=list(csv.DictReader(open('au_s3_rho090_out/actuation.csv')))
print("=== counters emitted by the run itself ===")
for r in rows:
    if r['stage'].startswith('counters_'): print("  "+r['stage'])
print()
c=collections.Counter(r['stage'] for r in rows if not r['stage'].startswith('counters_'))
print("=== stage counts ===")
for s,k in sorted(c.items(), key=lambda x:-x[1]): print("  %-32s %d" % (s,k))
g={}
for r in rows:
    st=r['stage']
    if st.startswith('counters_'): continue
    gen=int(r['generation'])
    g.setdefault(gen,{})[st]=r
S1='rate_command'; S2='sender_rate_effect'; S3a='arrival_at_bottleneck'; S3='first_affected_at_bottleneck'
full=[k for k,v in g.items() if S1 in v and S2 in v and S3a in v and S3 in v]
print()
print("=== gates ===")
print("  generations with all FOUR stages : %d" % len(full))
print("  S2 gens missing S1               : %d" % len([k for k,v in g.items() if S2 in v and S1 not in v]))
print("  S3a gens missing S2              : %d" % len([k for k,v in g.items() if S3a in v and S2 not in v]))
print("  S3 gens missing S3a              : %d" % len([k for k,v in g.items() if S3 in v and S3a not in v]))
neg=0
for k in full:
    v=g[k]
    t1=int(v[S1]['time_ns']); t2=int(v[S2]['time_ns'])
    t3a=int(v[S3a]['time_ns']); t3=int(v[S3]['time_ns'])
    if not (t1<=t2<=t3a<=t3): neg+=1
print("  ordering violations (t1<=t2<=t3a<=t3): %d" % neg)
print()
def stats(name,vals,note=""):
    if not vals: print("  %-22s (no data) %s"%(name,note)); return
    v=sorted(vals); n=len(v)
    def p(q): return v[min(n-1,int(round(q*(n-1))))]
    print("  %-22s n=%-5d min=%8.3f mean=%8.3f p50=%8.3f p95=%8.3f p99=%8.3f max=%9.3f  %s"
          % (name,n,v[0]/1e3,sum(v)/n/1e3,p(.5)/1e3,p(.95)/1e3,p(.99)/1e3,v[-1]/1e3,note))
H_OBS=5000
t=lambda k,s: int(g[k][s]['time_ns'])
print("=== latency components (us), FULL four-stage triples only ===")
stats("H_obs",     [H_OBS]*len(full), "measured telemetry sample->delivery")
stats("H_sender",  [t(k,S2)-t(k,S1) for k in full], "rate_command -> sender effect")
stats("H_path",    [t(k,S3a)-t(k,S2) for k in full], "sender -> bottleneck ARRIVAL")
stats("H_egressq", [t(k,S3)-t(k,S3a) for k in full], "arrival -> dequeue (queueing)")
print()
stats("H_eff (arrival)",[H_OBS+t(k,S3a)-t(k,S1) for k in full], "<== USE THIS for the horizon")
stats("H_eff (dequeue)",[H_OBS+t(k,S3)-t(k,S1) for k in full], "double-counts the queue")
