import csv, os, collections
os.chdir('/work/simulation/experiment/scheme1_sba')
rows=list(csv.DictReader(open('au_s3_rho090_out/actuation.csv')))
cmd={}; snd=set()
for r in rows:
    g=int(r['generation'])
    if r['stage']=='rate_command': cmd[g]=r
    elif r['stage']=='sender_rate_effect': snd.add(g)
missing=[g for g in cmd if g not in snd]
print("=== why 417 commands have no stage 2? ===")
print("  total cmd=%d, missing stage2=%d" % (len(cmd),len(missing)))
# per-flow: is a later command superseding an earlier one for the SAME flow?
byflow=collections.defaultdict(list)
for g,r in sorted(cmd.items()):
    byflow[r['flow_id']].append((g,int(r['time_ns'])))
sup=0; only=0
for fl,lst in byflow.items():
    for i,(g,t) in enumerate(lst):
        if g in snd: continue
        # was there a LATER command for the same flow? then it was superseded
        if i+1 < len(lst): sup+=1
        else: only+=1
print("  missing because a LATER command superseded it : %d" % sup)
print("  missing and was the flow's LAST command       : %d" % only)
print("  -> supersession explains %.1f%% of the gap" % (100.0*sup/max(1,len(missing))))
print()
print("  NOTE my 'duplicate' counter reported 0 because it counted duplicate")
print("  GENERATIONS (never possible: generation is a ++counter), not superseded")
print("  pending entries.  The real supersession count is the %d above." % sup)
print()
print("=== flows per stage ===")
print("  distinct flows with cmd    : %d" % len(byflow))
print("  distinct flows with stage2 : %d" % len(set(cmd[g]['flow_id'] for g in snd)))
print()
print("=== H_path: why ~92us p50 and not ~15us? ===")
print("  H_path = sender QP dequeue -> that packet's EgressDequeue at bottleneck.")
print("  EgressDequeue fires when the packet LEAVES the egress queue, so H_path")
print("  includes propagation AND the time the packet waited in the egress queue.")
print("  Observed egress queue at rho=0.90 peaks 56592 B = 45.27 us, and the")
print("  15.0 us figure was release -> queue FIRST NONZERO (arrival), not dequeue.")
print("  So the two measure different points; they are not in conflict.")
