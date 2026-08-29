import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
C=10e9
print("=== (4) per-ingress-port PFC detail, contributors only, batch window ===")
for tag in ('055','075','090','09875'):
    f='au_s3_rho'+tag+'_out/pfc_ports.csv'
    if not os.path.exists(f):
        print("  rho=%-7s NO FILE"%tag); continue
    per={}
    n=0
    with open(f) as h:
        for r in csv.DictReader(h):
            t=int(r['time_ns'])
            if t<2000000000 or t>2090000000: continue
            n+=1
            p=int(r['ingress_port'])
            d=per.setdefault(p,dict(occ=0,th_min=None,sl_min=None,hd=0,paused=0,rx=0,cnt=0))
            d['cnt']+=1
            occ=int(r['shared_used_bytes']); th=int(r['dynamic_pfc_threshold_bytes'])
            sl=int(r['pfc_slack_bytes']);   hd=int(r['headroom_bytes'])
            d['occ']=max(d['occ'],occ)
            d['th_min']=th if d['th_min'] is None else min(d['th_min'],th)
            d['sl_min']=sl if d['sl_min'] is None else min(d['sl_min'],sl)
            d['hd']=max(d['hd'],hd)
            d['paused']+=int(r['paused'])
            d['rx']=max(d['rx'],int(r['rx_bytes_total']))
    print("  rho=%s  (%d rows in window, %d contributing ports)"%(tag,n,len(per)))
    print("    %-6s %12s %12s %12s %10s %8s %14s"%("port","occ_max_B","thresh_min_B","slack_min_B","hdrm_max","paused","rx_total_B"))
    gmin=None
    for p in sorted(per):
        d=per[p]
        if gmin is None or d['sl_min']<gmin: gmin=d['sl_min']
        print("    %-6d %12d %12d %12d %10d %8d %14d"%(p,d['occ'],d['th_min'],d['sl_min'],d['hd'],d['paused'],d['rx']))
    print("    --> MIN SLACK over real contributors = %d B (%.2f us of 10G)"%(gmin,gmin*8/C*1e6))
