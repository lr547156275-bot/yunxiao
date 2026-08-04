#!/usr/bin/env python3
"""Package analysis plus selected raw evidence without duplicate packet traces."""
import csv,hashlib,os,tarfile,time
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
REPO=os.path.abspath(os.path.join(ROOT,'..'))

def add_file(files,path):
 path=os.path.abspath(path)
 if os.path.isfile(path) and not path.endswith(('.pyc','.core')):files.add(path)
def add_tree(files,path):
 if not os.path.isdir(path):return
 for base,dirs,names in os.walk(path):
  dirs[:]=[x for x in dirs if x!='__pycache__']
  for n in names:add_file(files,os.path.join(base,n))
def rows(name):
 with open(os.path.join(ROOT,'configs',name)) as f:return list(csv.DictReader(f))
def run(kind,r):return os.path.join(ROOT,'runs_'+kind,r['scenario'],r['algorithm_name'],'seed_'+r['seed'])

files=set()
for name in ('reports','processed','figures','configs','scripts','preflight','codex_logs'):add_tree(files,os.path.join(ROOT,name))
light=('manifest.json','result.json','run_meta.json','config.txt','command.txt','stdout.log','exit_status.txt','completed.flag','flow_summary.csv','round_summary.csv','feedback_summary.csv','controller_summary.csv','group_round_summary.csv','flow_plan.csv','queue_summary.csv','rate_summary.csv','scope_summary.csv','scope_link_summary.csv','control_summary.csv','pfc_events.csv','applied_rate_audit.csv','cbap_flow_state.csv','cbap_admission.csv','cbap_control_overhead.csv')
for r in rows('semantic_manifest.csv'):
 d=run('semantic',r)
 for n in light:add_file(files,os.path.join(d,n))
# Complete representative v1.2/v1.3 sender/rate/queue evidence and the zero-grant case.
representatives=[('fan64_msg1m_load80','cbap_full_v12_scoped'),('fan64_msg1m_load80','cbap_full_v13_ratefloor_fix'),('zero_grant_pause_resume','cbap_full_v13_ratefloor_fix')]
for scenario,algorithm in representatives:
 d=os.path.join(ROOT,'runs_semantic',scenario,algorithm,'seed_1')
 for n in ('sender_tx_trace.csv','cbap_rate_transitions.csv','cbap_port_summary.csv','selected_flow_timeseries.csv','selected_flow_timeseries.csv.gz','selected_link_timeseries.csv','selected_link_timeseries.csv.gz'):add_file(files,os.path.join(d,n))
# Reduced matrix: identity, logs, results, and summaries only. Aggregated detailed audits are in processed/.
reduced=('manifest.json','result.json','run_meta.json','config.txt','command.txt','stdout.log','exit_status.txt','completed.flag','flow_summary.csv','round_summary.csv','feedback_summary.csv','controller_summary.csv','group_round_summary.csv','flow_plan.csv','queue_summary.csv','rate_summary.csv','scope_summary.csv','scope_link_summary.csv','control_summary.csv','pfc_events.csv','cbap_flow_state.csv','cbap_control_overhead.csv')
for r in rows('reduced_manifest.csv'):
 d=run('reduced',r)
 for n in reduced:add_file(files,os.path.join(d,n))

manifest_path=os.path.join(ROOT,'reports','package_manifest.txt')
with open(manifest_path,'w') as f:
 for p in sorted(files):f.write(os.path.relpath(p,REPO)+'\n')
files.add(manifest_path)
stamp=time.strftime('%Y%m%d_%H%M%S')
archive=os.path.join(REPO,'cbap_v13_ratefloor_fix_results_'+stamp+'.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for p in sorted(files):tar.add(p,arcname=os.path.relpath(p,REPO),recursive=False)
h=hashlib.sha256()
with open(archive,'rb') as f:
 for b in iter(lambda:f.read(1<<20),b''):h.update(b)
sha_path=archive+'.sha256'
with open(sha_path,'w') as f:f.write(h.hexdigest()+'  '+os.path.basename(archive)+'\n')
print(archive);print(sha_path);print(os.path.getsize(archive));print(len(files))
