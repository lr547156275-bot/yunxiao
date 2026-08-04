#!/usr/bin/env python3
import argparse, csv, hashlib, json, os, shutil, subprocess, time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
REPO=os.path.abspath(os.path.join(ROOT,".."))
IDENTITIES={
 "dcqcn":(1,False,0,"baseline","none"),
 "hpcc_int":(3,False,0,"baseline","none"),
 "independent_min_grant":(20,True,0,"v1","legacy_min"),
 "cbap_rateonly_v1":(22,True,0,"v1","legacy_min"),
 "cbap_full_v1":(23,True,0,"v1","legacy_min"),
 "cbap_rateonly_v11":(22,True,1,"v1.1","adaptive_max"),
 "cbap_full_v11":(23,True,1,"v1.1","adaptive_max"),
}

def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()

def rewrite(src,dst,updates):
 lines=[]; seen=set()
 for line in open(src):
  key=line.split()[0] if line.split() else ""
  if key in updates: lines.append("%s %s\n"%(key,updates[key])); seen.add(key)
  else: lines.append(line)
 for key in sorted(set(updates)-seen): lines.append("%s %s\n"%(key,updates[key]))
 with open(dst,"w") as out: out.writelines(lines)

def main():
 p=argparse.ArgumentParser(); p.add_argument("manifest"); p.add_argument("run_id")
 p.add_argument("run_dir"); p.add_argument("--victim",action="store_true")
 p.add_argument("--min-free-gb",type=float,default=5); a=p.parse_args()
 rows={x["run_id"]:x for x in csv.DictReader(open(a.manifest))}
 if a.run_id not in rows: raise SystemExit("unknown run id")
 row=rows[a.run_id]; run=os.path.abspath(a.run_dir); os.makedirs(run,exist_ok=True)
 if a.victim:
  case=os.path.join(ROOT,"victim_cases",row["subcase"])
  algorithm=row["algorithm_name"]; mode=int(row["cc_mode"]); cbap=False
  version="baseline"; policy="none"; policy_id=0
  scenario="victim_calibration"
 else:
  algorithm=row["algorithm_name"]
  if algorithm not in IDENTITIES: raise SystemExit("unknown identity")
  mode,cbap,policy_id,version,policy=IDENTITIES[algorithm]
  if mode!=int(row["cc_mode"]) or version!=row["cbap_version"] or policy!=row["increase_policy"]:
   raise SystemExit("manifest identity mismatch")
  case=os.path.join(ROOT,"cases",row["scenario"],row["subcase"])
  scenario=row["scenario"]
 for name in os.listdir(case):
  src=os.path.join(case,name)
  if os.path.isfile(src) and name!="config.txt": shutil.copy2(src,os.path.join(run,name))
 updates={"CC_MODE":mode,"SIM_SEED":row["seed"],"ALGORITHM":algorithm,
          "SCENARIO":scenario+"__"+row["subcase"],"CBAP_ENABLE":int(cbap),
          "CBAP_INCREASE_POLICY":policy_id,"CBAP_INCREASE_FRACTION":"0.10",
          "CBAP_INCREASE_ABSOLUTE_BPS":2000000000,"CBAP_VERSION":version,
          "CBAP_INCREASE_AUDIT_FILE":"increase_policy_events.csv" if cbap else "/dev/null",
          "CBAP_PACKET_TRACE_FILE":"cbap_packet_trace.csv",
          "CBAP_PACKET_TRACE_MAX_MB":128,
          "CBAP_TX_EVENT_FILE":"cbap_tx_events.csv" if cbap else "/dev/null",
          "CRFM_MIN_FREE_GB":a.min_free_gb}
 if a.victim: updates["PFC_RUNTIME_ENABLE"]=row["pfc_enabled"]
 rewrite(os.path.join(case,"config.txt"),os.path.join(run,"config.txt"),updates)
 hashes={name:digest(os.path.join(run,name)) for name in os.listdir(run)
         if name not in ("config.txt",) and os.path.isfile(os.path.join(run,name))}
 commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
 meta={"run_id":a.run_id,"scenario":scenario,"subcase":row["subcase"],
       "algorithm":algorithm,"algorithm_name":algorithm,"cbap_version":version,
       "increase_policy":policy,"increase_fraction":0.10,
       "increase_absolute_bps":2000000000,"cc_mode":mode,"seed":int(row["seed"]),
       "git_commit":commit,"input_hashes":hashes,"status":"prepared",
       "exit_status":None,"log_truncated":False,"victim_calibration":a.victim,
       "prepared_time_unix":time.time()}
 with open(os.path.join(run,"run_meta.json"),"w") as out:
  json.dump(meta,out,indent=2,sort_keys=True); out.write("\n")
 with open(os.path.join(run,"manifest.json"),"w") as out:
  json.dump(dict(row,input_hashes=hashes),out,indent=2,sort_keys=True); out.write("\n")
 with open(os.path.join(run,"command.txt"),"w") as out:
  out.write('python2 ./waf --cwd="%s" --run "scratch/third %s/config.txt"\n'%(run,run))
 open(os.path.join(run,"git_commit.txt"),"w").write(commit+"\n")

if __name__=="__main__": main()
