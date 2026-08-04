#!/usr/bin/env python3
import argparse,csv,hashlib,json,os,shutil,subprocess,time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
REPO=os.path.abspath(os.path.join(ROOT,"..")); SIM=os.path.join(REPO,"simulation")

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def rewrite(src,dst,updates):
 lines=[];seen=set()
 for line in open(src):
  w=line.split();key=w[0] if w else ""
  if key in updates:lines.append("%s %s\n"%(key,updates[key]));seen.add(key)
  else:lines.append(line)
 for key in sorted(set(updates)-seen):lines.append("%s %s\n"%(key,updates[key]))
 with open(dst,"w") as f:f.writelines(lines)

def main():
 p=argparse.ArgumentParser();p.add_argument("manifest");p.add_argument("run_id");p.add_argument("run_dir");p.add_argument("--min-free-gb",type=float,default=5);a=p.parse_args()
 rows={r["run_id"]:r for r in csv.DictReader(open(a.manifest))}
 if a.run_id not in rows:raise SystemExit("unknown run_id")
 r=rows[a.run_id]; scope="scope" if "scope_manifest" in os.path.basename(a.manifest) else "core"
 case=os.path.join(ROOT,"cases",scope,r["scenario"]);run=os.path.abspath(a.run_dir);os.makedirs(run,exist_ok=True)
 for name in os.listdir(case):
  src=os.path.join(case,name)
  if os.path.isfile(src) and name!="config.txt":shutil.copy2(src,os.path.join(run,name))
 mode=int(r["cc_mode"]);cbap=20<=mode<=24;scoped=mode==24
 policy=1 if scoped else 0
 updates={"CC_MODE":mode,"SIM_SEED":r["seed"],"ALGORITHM":r["algorithm_name"],
  "SCENARIO":r["scenario"],"CBAP_ENABLE":int(cbap),"CBAP_VERSION":r["cbap_version"],
  "CBAP_INCREASE_POLICY":1 if mode in (21,22,23,24) else 0,
  "CBAP_INCREASE_FRACTION":"0.10","CBAP_INCREASE_ABSOLUTE_BPS":2000000000,
  "CBAP_SCOPE_POLICY":policy,"CBAP_SCOPE_BASE_CC":1,
  "CBAP_SCOPE_SUMMARY_FILE":"scope_summary.csv" if cbap else "/dev/null",
  "CBAP_SCOPE_LINK_FILE":"scope_link_summary.csv" if cbap else "/dev/null",
  "CBAP_PACKET_TRACE_FILE":"cbap_packet_trace.csv" if cbap else "/dev/null",
  "CBAP_PACKET_TRACE_MAX_MB":128,"CBAP_TX_EVENT_FILE":"cbap_tx_events.csv" if cbap else "/dev/null",
  "CBAP_INCREASE_AUDIT_FILE":"increase_policy_events.csv" if cbap else "/dev/null",
  "CRFM_MIN_FREE_GB":a.min_free_gb}
 rewrite(os.path.join(case,"config.txt"),os.path.join(run,"config.txt"),updates)
 hashes={n:sha(os.path.join(run,n)) for n in os.listdir(run) if os.path.isfile(os.path.join(run,n)) and n!="config.txt"}
 commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
 manifest=dict(r);manifest.update({"algorithm_name":r["algorithm_name"],"scope_decision":"PENDING" if scoped else "NOT_APPLICABLE",
  "scope_reason":"PENDING" if scoped else "NOT_APPLICABLE","scope_decision_delay_ns":5000 if scoped else 0,
  "triggering_link":"PENDING" if scoped else "NOT_APPLICABLE","pending_count_on_triggering_link":"PENDING" if scoped else 0,
  "independent_aggregate_rate_bps":"PENDING" if scoped else 0,"batch_admission_capacity_bps":"PENDING" if scoped else 0,
  "oversubscription_ratio":"PENDING" if scoped else 0,"base_cc":"dcqcn","git_commit":commit,"input_hashes":hashes})
 meta={"run_id":a.run_id,"scenario":r["scenario"],"algorithm":r["algorithm_name"],"algorithm_name":r["algorithm_name"],
  "cc_mode":mode,"cbap_version":r["cbap_version"],"scope_policy":r["scope_policy"],"base_cc":"dcqcn",
  "scope_decision_delay_ns":5000 if scoped else 0,"seed":int(r["seed"]),"git_commit":commit,"input_hashes":hashes,
  "status":"prepared","exit_status":None,"prepared_time_unix":time.time(),"log_truncated":False}
 for name,obj in (("manifest.json",manifest),("run_meta.json",meta)):
  with open(os.path.join(run,name),"w") as f:json.dump(obj,f,indent=2,sort_keys=True);f.write("\n")
 with open(os.path.join(run,"command.txt"),"w") as f:f.write('python2 ./waf --cwd="%s" --run "scratch/third %s/config.txt"\n'%(run,run))

if __name__=="__main__":main()
