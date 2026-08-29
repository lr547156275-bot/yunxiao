import csv, os
os.chdir('/work/simulation/experiment/scheme1_sba')
rows=list(csv.DictReader(open('qc_s3_rho090_out/qc_trace.csv')))
def n(v,x=0.0):
    try: return float(v)
    except: return x
print("=== item 6: locate 65->64 and 65->66 independently ===")
seq=[(i,int(n(r['protected_count'])),n(r['floor_wire_bps']),n(r['floor_payload_bps']),
      n(r['time_ns']),n(r['owns_rates']),n(r['duplicate_qp_count'])) for i,r in enumerate(rows)]
owned=[s for s in seq if s[5]==1]
print("  epochs with owns_rates=1: %d" % len(owned))
cnts={}
for s in owned: cnts[s[1]]=cnts.get(s[1],0)+1
print("  protected_count histogram (owning epochs): %s" % dict(sorted(cnts.items())))
fl={}
for s in owned: fl[round(s[2]/1e6)]=fl.get(round(s[2]/1e6),0)+1
print("  floor_wire (Mbps) histogram: %s" % dict(sorted(fl.items())))
print()
first_down=None; first_up=None; prev=None
for s in owned:
    c=s[1]
    if prev is not None:
        if prev==65 and c==64 and first_down is None: first_down=s
        if prev==65 and c==66 and first_up is None: first_up=s
        if c==66 and first_up is None: first_up=s
    prev=c
print("=== A. first 65 -> 64 ===")
if first_down:
    i=first_down[0]
    print("  epoch idx=%d t=%.3f us count=%d floor_wire=%.4f G floor_payload=%.4f G"
          % (i, first_down[4]/1e3, first_down[1], first_down[2]/1e9, first_down[3]/1e9))
    for j in range(max(0,i-3), min(len(rows), i+3)):
        r=rows[j]
        print("    idx=%d t=%.3f cnt=%s floor_w=%.4fG owns=%s dup=%s epoch_id=%s"
              % (j, n(r['time_ns'])/1e3, r['protected_count'],
                 n(r['floor_wire_bps'])/1e9, r['owns_rates'],
                 r['duplicate_qp_count'], r['epoch_id']))
else:
    print("  no 65->64 transition found among owning epochs")
print()
print("=== B. first occurrence of 66 ===")
if first_up:
    i=first_up[0]
    print("  epoch idx=%d t=%.3f us count=%d floor_wire=%.4f G floor_payload=%.4f G"
          % (i, first_up[4]/1e3, first_up[1], first_up[2]/1e9, first_up[3]/1e9))
    for j in range(max(0,i-3), min(len(rows), i+3)):
        r=rows[j]
        print("    idx=%d t=%.3f cnt=%s floor_w=%.4fG floor_p=%.4fG dup=%s"
              % (j, n(r['time_ns'])/1e3, r['protected_count'],
                 n(r['floor_wire_bps'])/1e9, n(r['floor_payload_bps'])/1e9,
                 r['duplicate_qp_count']))
else:
    print("  NO epoch ever had protected_count = 66")
print()
print("=== does floor 6.916 G actually correspond to count 66? ===")
for s in owned:
    if abs(s[2]-6.916e9)<3e6:
        print("  floor=6.916G seen at idx=%d with protected_count=%d payload_floor=%.4fG"
              % (s[0], s[1], s[3]/1e9))
        break
else:
    print("  floor 6.916 G never occurs in owning epochs")
print()
print("  KEY: floor_wire = sum over ledger of pay*ratio, but protected_count is")
print("  qcProtectedQps.size(). If they disagree, the two sets are NOT the same")
print("  set -- which is itself the bug, independent of operator[].")
mismatch=[s for s in owned if abs(s[2] - s[1]*100e6*1.048) > 3e6]
print("  epochs where floor_wire != count * 100M * 1.048 : %d of %d"
      % (len(mismatch), len(owned)))
if mismatch:
    s=mismatch[0]
    print("    first: idx=%d count=%d floor_wire=%.4fG expected=%.4fG"
          % (s[0], s[1], s[2]/1e9, s[1]*100e6*1.048/1e9))
