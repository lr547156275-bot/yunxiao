import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
print("=== (5) three-stage actuation, measured ===")
for tag in ('055','075','090','09875'):
    n='au_s3_rho'+tag
    f=n+'_out/actuation.csv'
    if not os.path.exists(f):
        print("  %-8s NO FILE"%tag); continue
    rows=list(csv.DictReader(open(f)))
    print("  rho=%-7s rows=%d" % (tag,len(rows)))
    if not rows: continue
    # group into triples by stage order
    cmds=[r for r in rows if r['stage']=='rate_command']
    eff =[r for r in rows if r['stage']=='sender_rate_effect']
    bot =[r for r in rows if r['stage']=='first_affected_at_bottleneck']
    print("    rate_command=%d sender_effect=%d at_bottleneck=%d" % (len(cmds),len(eff),len(bot)))
    if eff:
        d=[int(r['delta_prev_stage_ns']) for r in eff]
        d.sort()
        print("    cmd->sender_effect  : min=%d med=%d max=%d ns  (%.2f/%.2f/%.2f us)"
              % (d[0],d[len(d)//2],d[-1],d[0]/1e3,d[len(d)//2]/1e3,d[-1]/1e3))
    if bot:
        d=[int(r['delta_prev_stage_ns']) for r in bot]; d.sort()
        t=[int(r['delta_from_command_ns']) for r in bot]; t.sort()
        print("    sender->bottleneck  : min=%d med=%d max=%d ns  (%.2f/%.2f/%.2f us)"
              % (d[0],d[len(d)//2],d[-1],d[0]/1e3,d[len(d)//2]/1e3,d[-1]/1e3))
        print("    cmd->bottleneck     : min=%d med=%d max=%d ns  (%.2f/%.2f/%.2f us)"
              % (t[0],t[len(t)//2],t[-1],t[0]/1e3,t[len(t)//2]/1e3,t[-1]/1e3))
        print("    H_eff = +5.0us sample lag -> min=%.2f med=%.2f max=%.2f us"
              % (t[0]/1e3+5,t[len(t)//2]/1e3+5,t[-1]/1e3+5))
    print("    first 4 rows:")
    for r in rows[:4]:
        print("      t=%s flow=%s stage=%-28s dprev=%s dcmd=%s"
              % (r['time_ns'],r['flow_id'],r['stage'],
                 r['delta_prev_stage_ns'],r['delta_from_command_ns']))
