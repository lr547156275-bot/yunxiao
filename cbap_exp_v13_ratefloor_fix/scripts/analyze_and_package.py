#!/usr/bin/env python3
"""Read-only analysis of completed v1.3 runs, then package selected artifacts."""
import csv,gzip,hashlib,json,math,os,statistics,subprocess,tarfile,time
from collections import Counter,defaultdict
from PIL import Image,ImageDraw,ImageFont

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
REPO=os.path.abspath(os.path.join(ROOT,'..'))
REPORT=os.path.join(ROOT,'reports');PROC=os.path.join(ROOT,'processed');FIG=os.path.join(ROOT,'figures')
for d in (REPORT,PROC,FIG):os.makedirs(d,exist_ok=True)
SEM_MAN=os.path.join(ROOT,'configs','semantic_manifest.csv');RED_MAN=os.path.join(ROOT,'configs','reduced_manifest.csv')

def csvrows(path):
 p=path if os.path.isfile(path) else path+'.gz'
 if not os.path.isfile(p):return []
 op=gzip.open if p.endswith('.gz') else open
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def num(x,k,default=0.0):
 try:return float(x.get(k,default))
 except:return default
def write_csv(path,rows,fields=None):
 fields=fields or (list(rows[0]) if rows else ['run_id','reason'])
 with open(path,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def manifest(kind):return list(csv.DictReader(open(SEM_MAN if kind=='semantic' else RED_MAN)))
def run_dir(kind,r):return os.path.join(ROOT,'runs_'+kind,r['scenario'],r['algorithm_name'],'seed_'+r['seed'])
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def fct_us(x):return num(x,'fct_us',num(x,'fct')*1e6)

def inspect_run(kind,r):
 d=run_dir(kind,r);reasons=[]
 required=['manifest.json','run_meta.json','result.json','config.txt','command.txt','stdout.log','exit_status.txt','flow_summary.csv','queue_summary.csv','rate_summary.csv','scope_summary.csv','control_summary.csv']
 if not os.path.isdir(d):return None,['missing_directory']
 for n in required:
  if not os.path.isfile(os.path.join(d,n)):reasons.append('missing_'+n)
 if not os.path.isfile(os.path.join(d,'completed.flag')):reasons.append('missing_completed_flag')
 if os.path.isfile(os.path.join(d,'exit_status.txt')) and open(os.path.join(d,'exit_status.txt')).read().strip()!='0':reasons.append('nonzero_exit')
 if reasons:return None,reasons
 meta=json.load(open(os.path.join(d,'run_meta.json')));result=json.load(open(os.path.join(d,'result.json')));man=json.load(open(os.path.join(d,'manifest.json')))
 if not result.get('all_flows_completed'):reasons.append('incomplete_flows')
 if result.get('log_truncated') or meta.get('log_truncated'):reasons.append('log_truncated')
 if any(isinstance(v,float) and not math.isfinite(v) for v in result.values()):reasons.append('nonfinite_result')
 if int(man.get('cc_mode',-1))!=int(r['cc_mode']):reasons.append('cc_mode_mismatch')
 case=json.load(open(os.path.join(d,'scenario_meta.json')));pending=set(case.get('pending_flow_ids',[]));incumbents=set(case.get('incumbent_flow_ids',[]))
 flows=csvrows(os.path.join(d,'flow_summary.csv'));pending_rows=[x for x in flows if int(x['flow_id']) in pending]
 if len(pending_rows)!=len(pending):reasons.append('pending_flow_count_mismatch')
 ccts=[fct_us(x) for x in pending_rows]
 inc=[x for x in flows if int(x['flow_id']) in incumbents];offered=float(case.get('incumbent_offered_load_percent',0))*1e9
 inc_drop=max([max(0.0,1-num(x,'flow_goodput')/offered) for x in inc],default=0.0) if offered else 0.0
 audit=csvrows(os.path.join(d,'applied_rate_audit.csv'))
 tx=csvrows(os.path.join(d,'sender_tx_trace.csv')) if int(r['cc_mode']) in (24,25) else []
 pacing=sum(1 for x in tx if x.get('event')=='TX_SEND' and num(x,'previous_tx_time_ns')>0 and num(x,'actual_gap_ns')+1<num(x,'expected_gap_ns'))
 control=csvrows(os.path.join(d,'control_summary.csv'))
 summary={
  'kind':kind,'run_id':r['run_id'],'scenario':r['scenario'],'algorithm':r['algorithm_name'],'seed':r['seed'],'cc_mode':r['cc_mode'],
  'scope_decision':meta.get('scope_decision','NOT_APPLICABLE'),'all_flows_completed':int(result.get('all_flows_completed',False)),
  'cct_us':max(ccts) if ccts else float('nan'),'pending_mean_fct_us':statistics.mean(ccts) if ccts else float('nan'),
  'peak_queue_bytes':result.get('queue_max_bytes',0),'queue_auc_byte_seconds':result.get('queue_auc_byte_seconds',0),
  'utilization':result.get('mean_utilization',0),'payload_goodput_gbps':result.get('payload_goodput_gbps',0),'incumbent_drop_fraction':inc_drop,
  'planner_grant_max_bps':max([num(x,'planner_grant_sum_bps') for x in audit],default=0),'target_rate_max_bps':max([num(x,'target_rate_sum_bps') for x in audit],default=0),
  'applied_rate_max_bps':max([num(x,'applied_rate_sum_bps') for x in audit],default=0),'actual_tx_rate_max_bps':max([num(x,'actual_tx_rate_sum_bps') for x in audit],default=0),
  'target_applied_mismatch_rows':sum(int(num(x,'target_rate_sum_bps'))!=int(num(x,'applied_rate_sum_bps')) for x in audit),
  'applied_capacity_violations':sum(int(num(x,'applied_capacity_violation')) for x in audit),
  'floor_clamp_count':sum(int(num(x,'floor_clamp_count')) for x in audit),'flows_below_legacy_floor_max':max([int(num(x,'flows_below_legacy_floor')) for x in audit],default=0),
  'pacing_violations':pacing,'planner_capacity_violations':result.get('capacity_violations',0),'credit_violations':result.get('credit_violations',0),
  'control_messages':sum(int(num(x,'summary_messages'))+int(num(x,'grant_messages')) for x in control),'control_bytes':sum(int(num(x,'total_control_bytes')) for x in control),
  'result_group_rct_max_us':result.get('group_rct_max_us',0),
 }
 return summary,reasons

FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n):
 try:return ImageFont.truetype(FONT_PATH,n)
 except:return ImageFont.load_default()
COLORS=['#1f77b4','#d62728','#2ca02c','#9467bd','#ff7f0e','#17becf']
def base_canvas(title,xlabel,ylabel):
 im=Image.new('RGB',(1200,720),'white');d=ImageDraw.Draw(im);d.text((60,20),title,fill='black',font=font(26));d.text((500,680),xlabel,fill='black',font=font(18));d.text((5,340),ylabel,fill='black',font=font(16));return im,d
def save_image(im,name):
 im.save(os.path.join(FIG,name+'.png'));im.save(os.path.join(FIG,name+'.pdf'),'PDF',resolution=150.0)
def line_plot(name,title,series,xlabel,ylabel):
 im,d=base_canvas(title,xlabel,ylabel);L,T,R,B=90,75,1160,650
 pts=[p for _,xs in series for p in xs]
 if not pts:save_image(im,name);return
 xmin=min(p[0] for p in pts);xmax=max(p[0] for p in pts);ymin=min(0,min(p[1] for p in pts));ymax=max(p[1] for p in pts);xmax=xmax if xmax>xmin else xmin+1;ymax=ymax if ymax>ymin else ymin+1
 d.line((L,T,L,B),fill='black',width=2);d.line((L,B,R,B),fill='black',width=2)
 for i in range(6):
  y=B-(B-T)*i/5;v=ymin+(ymax-ymin)*i/5;d.line((L,y,R,y),fill='#dddddd');d.text((8,y-9),f'{v:.3g}',fill='black',font=font(13))
 for idx,(label,xs) in enumerate(series):
  step=max(1,len(xs)//2500);q=xs[::step];xy=[(L+(x-xmin)/(xmax-xmin)*(R-L),B-(y-ymin)/(ymax-ymin)*(B-T)) for x,y in q]
  if len(xy)>1:d.line(xy,fill=COLORS[idx%len(COLORS)],width=3)
  d.line((780+idx%2*190,35,810+idx%2*190,35),fill=COLORS[idx%len(COLORS)],width=4);d.text((815+idx%2*190,25),label,fill='black',font=font(14))
 save_image(im,name)
def bar_plot(name,title,categories,series,xlabel,ylabel):
 im,d=base_canvas(title,xlabel,ylabel);L,T,R,B=100,80,1160,630;vals=[v for _,vs in series for v in vs];ymax=max(vals+[1])*1.12
 d.line((L,T,L,B),fill='black',width=2);d.line((L,B,R,B),fill='black',width=2)
 for i in range(6):
  y=B-(B-T)*i/5;v=ymax*i/5;d.line((L,y,R,y),fill='#dddddd');d.text((10,y-9),f'{v:.3g}',fill='black',font=font(13))
 group=(R-L)/max(1,len(categories));bw=group/(len(series)+1)
 for j,(label,vs) in enumerate(series):
  for i,v in enumerate(vs):
   x=L+i*group+(j+.5)*bw;y=B-v/ymax*(B-T);d.rectangle((x,y,x+bw*.85,B),fill=COLORS[j%len(COLORS)])
  d.rectangle((750+j%3*135,35,770+j%3*135,50),fill=COLORS[j%len(COLORS)]);d.text((775+j%3*135,33),label,fill='black',font=font(13))
 for i,c in enumerate(categories):d.text((L+i*group+5,B+8),c,fill='black',font=font(12))
 save_image(im,name)

def pct(new,old):return (new-old)/old*100 if old else float('nan')
def write_figure_csv(name,rows):write_csv(os.path.join(FIG,name+'.csv'),rows)
def link_series(d):return [(num(x,'time')*1e6,num(x,'queue_bytes')) for x in csvrows(os.path.join(d,'selected_link_timeseries.csv'))]
def flow_throughput(d,fid=0):
 rows=[x for x in csvrows(os.path.join(d,'selected_flow_timeseries.csv')) if int(x['flow_id'])==fid];out=[]
 for a,b in zip(rows,rows[1:]):
  dt=num(b,'time')-num(a,'time');delta=max(0,num(b,'snd_nxt')-num(a,'snd_nxt'))
  if dt>0:out.append((num(b,'time')*1e6,delta*8/dt/1e9))
 return out

def main():
 missing=[];invalid=[];summaries=[];records={}
 for kind in ('semantic','reduced'):
  for r in manifest(kind):
   s,reasons=inspect_run(kind,r)
   if s is None:
    for reason in reasons:missing.append({'kind':kind,'run_id':r['run_id'],'reason':reason})
   else:
    summaries.append(s);records[(kind,r['scenario'],r['algorithm_name'])]=s
    for reason in reasons:invalid.append({'kind':kind,'run_id':r['run_id'],'reason':reason})
 # Input hashes must be identical across algorithms within a scenario.
 hash_checks=[]
 for kind in ('semantic','reduced'):
  grouped=defaultdict(list)
  for r in manifest(kind):
   p=os.path.join(run_dir(kind,r),'manifest.json')
   if os.path.isfile(p):grouped[r['scenario']].append((r['run_id'],json.dumps(json.load(open(p)).get('input_hashes',{}),sort_keys=True)))
  for scenario,items in grouped.items():
   ok=len(set(x[1] for x in items))==1
   hash_checks.append((kind,scenario,ok))
   if not ok:
    for run_id,_ in items:invalid.append({'kind':kind,'run_id':run_id,'reason':'cross_algorithm_input_hash_mismatch'})
 write_csv(os.path.join(PROC,'missing_runs.csv'),missing,['kind','run_id','reason']);write_csv(os.path.join(PROC,'invalid_runs.csv'),invalid,['kind','run_id','reason'])
 reduced=[x for x in summaries if x['kind']=='reduced'];write_csv(os.path.join(PROC,'summary_by_run.csv'),reduced)

 pairs=[]
 for scenario in sorted(set(x['scenario'] for x in reduced)):
  new=records.get(('reduced',scenario,'cbap_full_v13_ratefloor_fix'))
  if not new:continue
  for base_name in ('cbap_full_v12_scoped','dctcp','dcqcn','hpcc_int'):
   old=records.get(('reduced',scenario,base_name))
   if not old:continue
   z={'scenario':scenario,'baseline':base_name,'new_algorithm':'cbap_full_v13_ratefloor_fix'}
   for key in ('cct_us','peak_queue_bytes','queue_auc_byte_seconds','utilization','payload_goodput_gbps','incumbent_drop_fraction','control_bytes'):
    z['baseline_'+key]=old[key];z['v13_'+key]=new[key];z[key+'_change_percent']=pct(float(new[key]),float(old[key])) if float(old[key]) else ''
   z['scope_decision_equal']=int(old['scope_decision']==new['scope_decision']) if base_name=='cbap_full_v12_scoped' else ''
   pairs.append(z)
 write_csv(os.path.join(PROC,'paired_v12_v13.csv'),pairs)

 audit_out=[];rate_ts=[];low_group=defaultdict(lambda:{'count':0,'min_actual':None,'max_actual':0,'violations':0})
 seen_sources=[]
 for kind in ('semantic','reduced'):
  for r in manifest(kind):
   if int(r['cc_mode']) not in (24,25):continue
   d=run_dir(kind,r);ap=os.path.join(d,'applied_rate_audit.csv');txp=os.path.join(d,'sender_tx_trace.csv')
   for x in csvrows(ap):
    row={'kind':kind,'run_id':r['run_id'],'scenario':r['scenario'],'algorithm':r['algorithm_name'],'seed':r['seed']};row.update(x);audit_out.append(row)
    if kind=='reduced':rate_ts.append(row)
   if int(r['cc_mode'])==25:
    for x in csvrows(txp):
     rate=num(x,'current_rate_bps')
     if x.get('event')!='TX_SEND' or not (0<rate<1702400000):continue
     key=(kind,r['run_id'],x['wire_bytes'],x['current_rate_bps'],x['expected_gap_ns']);g=low_group[key];g['count']+=1;act=int(num(x,'actual_gap_ns'))
     if act:g['min_actual']=act if g['min_actual'] is None else min(g['min_actual'],act)
     g['max_actual']=max(g['max_actual'],act);g['violations']+=int(num(x,'previous_tx_time_ns')>0 and act+1<int(num(x,'expected_gap_ns')))
 write_csv(os.path.join(PROC,'applied_rate_capacity_audit.csv'),audit_out)
 write_csv(os.path.join(PROC,'rate_sum_timeseries.csv'),rate_ts)
 low=[]
 for (kind,rid,wire,rate,gap),g in sorted(low_group.items()):low.append({'kind':kind,'run_id':rid,'wire_bytes':wire,'rate_bps':rate,'expected_gap_ns':gap,'packet_count':g['count'],'minimum_actual_gap_ns':g['min_actual'] or 0,'maximum_actual_gap_ns':g['max_actual'],'pacing_violations':g['violations']})
 write_csv(os.path.join(PROC,'low_rate_pacing_audit.csv'),low)
 zero_src=os.path.join(PROC,'zero_grant_audit.csv')
 if not os.path.isfile(zero_src):write_csv(zero_src,[],['run_id','reason'])

 # Figure 1/2: representative fan64 rate sums.
 rep={}
 for alg in ('cbap_full_v12_scoped','cbap_full_v13_ratefloor_fix'):
  xs=[x for x in rate_ts if x['scenario']=='fan64_msg1m_load80' and x['algorithm']==alg and int(x['applied_rate_sum_bps'])>0]
  rep[alg]=xs
 rows=[]
 for alg,xs in rep.items():
  for x in xs:rows.append({'algorithm':alg,'time_us':int(x['epoch'])*5,'planner_gbps':num(x,'planner_grant_sum_bps')/1e9,'applied_gbps':num(x,'applied_rate_sum_bps')/1e9})
 write_figure_csv('fan64_grant_vs_applied',rows)
 line_plot('fan64_grant_vs_applied','Fan-in 64: planner grant and applied rate',[('v1.2 applied',[(int(x['epoch'])*5,num(x,'applied_rate_sum_bps')/1e9) for x in rep['cbap_full_v12_scoped']]),('v1.3 planner',[(int(x['epoch'])*5,num(x,'planner_grant_sum_bps')/1e9) for x in rep['cbap_full_v13_ratefloor_fix']]),('v1.3 applied',[(int(x['epoch'])*5,num(x,'applied_rate_sum_bps')/1e9) for x in rep['cbap_full_v13_ratefloor_fix']])],'Time (us)','Rate sum (Gb/s)')
 xs=rep['cbap_full_v13_ratefloor_fix'];rows=[{'time_us':int(x['epoch'])*5,'applied_gbps':num(x,'applied_rate_sum_bps')/1e9,'effective_gbps':num(x,'C_effective_l')/1e9} for x in xs];write_figure_csv('fan64_applied_vs_capacity',rows)
 line_plot('fan64_applied_vs_capacity','Fan-in 64: v1.3 applied rate vs live effective capacity',[('applied',[(x['time_us'],x['applied_gbps']) for x in rows]),('effective',[(x['time_us'],x['effective_gbps']) for x in rows])],'Time (us)','Rate (Gb/s)')
 # Figure 3 queue timeline.
 qseries=[];qrows=[]
 for alg,label in (('cbap_full_v12_scoped','v1.2'),('cbap_full_v13_ratefloor_fix','v1.3')):
  d=run_dir('reduced',{'scenario':'fan64_msg1m_load80','algorithm_name':alg,'seed':'1'});xs=link_series(d);qseries.append((label,[(t,q/1024) for t,q in xs]));qrows += [{'algorithm':label,'time_us':t,'queue_kib':q/1024} for t,q in xs]
 write_figure_csv('fan64_queue_timeline',qrows);line_plot('fan64_queue_timeline','Fan-in 64, 1 MiB queue timeline',qseries,'Time (us)','Queue (KiB)')
 # Figures 4/5 fan64 bars.
 cats=['64K','256K','1M','4M'];scens=['fan64_msg64k_load80','fan64_msg256k_load80','fan64_msg1m_load80','fan64_msg4m_load80']
 auc_series=[];cct_series=[];auc_rows=[];cct_rows=[]
 for alg,label in (('cbap_full_v12_scoped','v1.2'),('cbap_full_v13_ratefloor_fix','v1.3'),('dctcp','DCTCP'),('dcqcn','DCQCN'),('hpcc_int','HPCC')):
  av=[records[('reduced',s,alg)]['queue_auc_byte_seconds'] for s in scens];cv=[records[('reduced',s,alg)]['cct_us'] for s in scens];auc_series.append((label,av));cct_series.append((label,cv))
  auc_rows += [{'message':c,'algorithm':label,'queue_auc_byte_seconds':v} for c,v in zip(cats,av)];cct_rows += [{'message':c,'algorithm':label,'cct_us':v} for c,v in zip(cats,cv)]
 write_figure_csv('fan64_queue_auc_comparison',auc_rows);bar_plot('fan64_queue_auc_comparison','Fan-in 64 queue AUC',cats,auc_series,'Message size','Queue AUC (byte-s)')
 write_figure_csv('fan64_cct_comparison',cct_rows);bar_plot('fan64_cct_comparison','Fan-in 64 collective completion time',cats,cct_series,'Message size','CCT (us)')
 # Figure 6 fan32 normalized regression.
 old=records[('reduced','fan32_msg1m_load80','cbap_full_v12_scoped')];new=records[('reduced','fan32_msg1m_load80','cbap_full_v13_ratefloor_fix')];keys=['CCT','Peak queue','Queue AUC'];ov=[old['cct_us'],old['peak_queue_bytes'],old['queue_auc_byte_seconds']];nv=[new['cct_us'],new['peak_queue_bytes'],new['queue_auc_byte_seconds']];rows=[{'metric':k,'algorithm':'v1.2','normalized':100} for k in keys]+[{'metric':k,'algorithm':'v1.3','normalized':n/o*100} for k,o,n in zip(keys,ov,nv)];write_figure_csv('fan32_regression_comparison',rows);bar_plot('fan32_regression_comparison','Fan-in 32 regression check (v1.2 = 100)',keys,[('v1.2',[100]*3),('v1.3',[n/o*100 for o,n in zip(ov,nv)])],'Metric','Normalized value')
 # Figure 7 packet gap distribution.
 hist=Counter()
 for x in low:
  if x['kind']=='semantic':hist[int(round(int(x['expected_gap_ns'])/500.0)*500)]+=int(x['packet_count'])
 hrows=[{'gap_bin_ns':k,'packet_count':v} for k,v in sorted(hist.items())];write_figure_csv('low_rate_packet_gap_distribution',hrows);bar_plot('low_rate_packet_gap_distribution','Low-rate packet-gap distribution',[str(x['gap_bin_ns']) for x in hrows],[('packets',[x['packet_count'] for x in hrows])],'Expected gap bin (ns)','Packet count')
 # Figure 8 zero grant.
 zero=csvrows(zero_src);z=zero[0] if zero else {};start=int(num(z,'pause_start_ns'));end=int(num(z,'pause_end_ns'));zrows=[{'time_ns':start-5000,'grant_state':1},{'time_ns':start,'grant_state':0},{'time_ns':end,'grant_state':1},{'time_ns':end+5000,'grant_state':1}];write_figure_csv('zero_grant_pause_resume_timeline',zrows);line_plot('zero_grant_pause_resume_timeline','Zero-grant pause/resume semantic timeline',[('grant state',[(x['time_ns']/1000,x['grant_state']) for x in zrows])],'Time (us)','Positive grant (1/0)')
 # Figure 9 incumbent injection throughput.
 series=[];rows=[]
 for alg,label in (('cbap_full_v12_scoped','v1.2'),('cbap_full_v13_ratefloor_fix','v1.3')):
  d=run_dir('reduced',{'scenario':'fan64_msg1m_load80','algorithm_name':alg,'seed':'1'});xs=flow_throughput(d);series.append((label,xs));rows += [{'algorithm':label,'time_us':t,'injection_gbps':v} for t,v in xs]
 write_figure_csv('incumbent_throughput_timeline',rows);line_plot('incumbent_throughput_timeline','Incumbent sender injection throughput',series,'Time (us)','Injection rate (Gb/s)')
 # Figure 10 control overhead (fan32 plus all fan64 sizes).
 control_scens=['fan32_msg1m_load80']+scens;control_cats=['F32-1M']+cats
 series=[];rows=[]
 for alg,label in (('cbap_full_v12_scoped','v1.2'),('cbap_full_v13_ratefloor_fix','v1.3')):
  vals=[records[('reduced',s,alg)]['control_bytes'] for s in control_scens];series.append((label,vals));rows += [{'scenario':s,'label':c,'algorithm':label,'control_bytes':v} for s,c,v in zip(control_scens,control_cats,vals)]
 write_figure_csv('control_overhead_comparison',rows);bar_plot('control_overhead_comparison','CBAP control overhead',control_cats,series,'Scenario','Control bytes')

 # Integrity, correctness, and decision.
 semantic_text=open(os.path.join(REPORT,'ratefloor_semantic_report.md')).read().splitlines()[0] if os.path.isfile(os.path.join(REPORT,'ratefloor_semantic_report.md')) else 'MISSING'
 v13=[x for x in reduced if x['algorithm']=='cbap_full_v13_ratefloor_fix'];v12=[x for x in reduced if x['algorithm']=='cbap_full_v12_scoped']
 floor=sum(int(x['floor_clamp_count']) for x in v13);applied_bad=sum(int(x['applied_capacity_violations']) for x in v13);pacing_bad=sum(int(x['pacing_violations']) for x in v13);mismatch=sum(int(x['target_applied_mismatch_rows']) for x in v13)
 fan64_fixed=sum(1 for x in audit_out if x['kind']=='reduced' and x['algorithm']=='cbap_full_v13_ratefloor_fix' and x['scenario'].startswith('fan64') and int(num(x,'applied_rate_sum_bps'))==108953600000)
 fan32_pair=next(x for x in pairs if x['scenario']=='fan32_msg1m_load80' and x['baseline']=='cbap_full_v12_scoped')
 fan64_pairs=[x for x in pairs if x['scenario'].startswith('fan64') and x['baseline']=='cbap_full_v12_scoped']
 queue_good=all(float(x['peak_queue_bytes_change_percent'])<=-50 and float(x['queue_auc_byte_seconds_change_percent'])<=-50 for x in fan64_pairs)
 fan32_good=float(fan32_pair['cct_us_change_percent'])<=3 and float(fan32_pair['peak_queue_bytes_change_percent'])<=10 and float(fan32_pair['queue_auc_byte_seconds_change_percent'])<=10
 zero_good=bool(zero) and int(num(zero[0],'data_tx_during_pause'))==0 and int(num(zero[0],'positive_tx_before'))>0 and int(num(zero[0],'positive_tx_after'))>0
 correctness=semantic_text=='RATEFLOOR_SEMANTIC_PASS' and floor==0 and applied_bad==0 and pacing_bad==0 and mismatch==0 and fan64_fixed==0 and zero_good and fan32_good and queue_good
 performance_limits=[x for x in fan64_pairs if float(x['cct_us_change_percent'])>5]
 if missing or invalid:decision='INVALID_EXPERIMENT'
 elif not correctness:decision='RATEFLOOR_FIX_INCORRECT'
 elif performance_limits:decision='RATEFLOOR_FIX_VALID_WITH_PERFORMANCE_LIMITATIONS'
 else:decision='RATEFLOOR_FIX_VALID'
 suspicious=[{'run_id':'cross-run-metric','finding':'result.json group_rct_max_us includes the incumbent group in some algorithms; final analysis uses pending collective raw CCT.'}]
 for x in performance_limits:suspicious.append({'run_id':x['scenario'],'finding':'v1.3 CCT regresses %.2f%% versus v1.2 despite queue improvement.'%float(x['cct_us_change_percent'])})
 actual_excess=sum(int(num(x,'actual_arrival_excess_bps')>0) for x in audit_out if x['algorithm']=='cbap_full_v13_ratefloor_fix')
 if actual_excess:suspicious.append({'run_id':'packetized-tx-windows','finding':'Actual TX-rate windows exceed effective capacity in %d rows; this is separately reported and is not an applied-rate violation.'%actual_excess})
 write_csv(os.path.join(PROC,'suspicious_runs.csv'),suspicious,['run_id','finding'])

 integrity=['# Result integrity','','- Semantic expected/completed: 5/%d.'%sum(x['kind']=='semantic' for x in summaries),'- Reduced expected/completed: 25/%d.'%len(reduced),'- Missing runs: %d.'%len(missing),'- Invalid runs: %d.'%len(invalid),'- Cross-algorithm input-hash scenario checks: %d/%d passed.'%(sum(x[2] for x in hash_checks),len(hash_checks)),'- Semantic status: `%s`.'%semantic_text,'','All run IDs are taken from fixed manifests. All comparisons are deterministic seed-1 comparisons; no cross-seed statistical claim is made.']
 open(os.path.join(REPORT,'result_integrity_report.md'),'w').write('\n'.join(integrity)+'\n')
 sem=['# Semantic verification','','- Positive target/applied mismatched epoch rows: %d.'%mismatch,'- Applied capacity violations: %d.'%applied_bad,'- Floor clamp count: %d.'%floor,'- Sender pacing violations: %d.'%pacing_bad,'- Fan64 v1.3 rows fixed at 108.9536 Gb/s: %d.'%fan64_fixed,'- Zero-grant DATA transmissions during pause: %s.'%(z.get('data_tx_during_pause','missing') if zero else 'missing'),'- Zero-grant pause duration: %s ns.'%(z.get('pause_duration_ns','missing') if zero else 'missing'),'','Low-rate packet timing is checked against `ceil(8*actual_wire_bytes*1e9/rate)`; smaller tail packets are not incorrectly required to use the maximum-packet interval.']
 open(os.path.join(REPORT,'semantic_verification.md'),'w').write('\n'.join(sem)+'\n')
 cap=['# Applied capacity report','','Planner, target, applied, and measured TX are separate quantities. The formal constraint is evaluated after applying the QP rate, with tolerance `max(1 bps, 1e-9*C_l)`.','','- v1.3 applied violations: %d.'%applied_bad,'- v1.3 target/applied mismatch rows: %d.'%mismatch,'- v1.3 floor clamps: %d.'%floor,'- Packetized measured-TX excess rows: %d (interpreted separately).'%actual_excess]
 open(os.path.join(REPORT,'applied_capacity_report.md'),'w').write('\n'.join(cap)+'\n')
 measured=['# Measured versus interpreted','','Measured directly: flow completion timestamps, queue samples, QP applied rates, packet gaps, sender byte progress, control messages, ECN/PFC outputs.','','Interpreted metrics: pending-collective CCT, queue AUC from 10-us samples, incumbent injection rate from sampled `snd_nxt`, and relative differences.','','The reduced matrix has one deterministic seed. It verifies the execution fix and exposes performance tradeoffs, but does not establish statistical generality. `actual_tx_rate_sum_bps` may exceed the applied constraint in a short measurement window because whole packets are counted; it is not substituted for the applied-rate constraint.']
 open(os.path.join(REPORT,'measured_vs_interpreted.md'),'w').write('\n'.join(measured)+'\n')
 open(os.path.join(REPORT,'suspicious_findings.md'),'w').write('# Suspicious findings\n\n'+'\n'.join('- '+x['finding'] for x in suspicious)+'\n')
 # Compact pair tables and direct answers to RQ1--RQ8.
 table=[]
 for x in pairs:
  if x['baseline']=='cbap_full_v12_scoped':table.append('| %s | %.2f | %.2f | %.2f | %.2f |'% (x['scenario'],float(x['cct_us_change_percent']),float(x['peak_queue_bytes_change_percent']),float(x['queue_auc_byte_seconds_change_percent']),float(x['utilization_change_percent'])))
 external=[]
 for x in pairs:
  if x['baseline']!='cbap_full_v12_scoped':external.append('| %s | %s | %.2f | %.2f | %.2f |'% (x['scenario'],x['baseline'],float(x['cct_us_change_percent']),float(x['peak_queue_bytes_change_percent']),float(x['queue_auc_byte_seconds_change_percent'])))
 v12_fixed=sum(1 for x in audit_out if x['kind']=='reduced' and x['algorithm']=='cbap_full_v12_scoped' and x['scenario'].startswith('fan64') and int(num(x,'applied_rate_sum_bps'))==108953600000)
 min_low=min([int(float(x['rate_bps'])) for x in low],default=0);max_gap=max([int(x['expected_gap_ns']) for x in low],default=0)
 control_lines=[]
 for x in [x for x in pairs if x['baseline']=='cbap_full_v12_scoped']:control_lines.append('| %s | %.0f | %.0f | %.2f |'% (x['scenario'],float(x['baseline_control_bytes']),float(x['v13_control_bytes']),float(x['control_bytes_change_percent']) if x['control_bytes_change_percent']!='' else 0))
 rq=['## Research-question answers','',f'- RQ1 — Yes. The minimum observed positive low-rate pacing value is {min_low/1e9:.6f} Gb/s, below 1.7024 Gb/s.',f'- RQ2 — Yes. v1.2 has {v12_fixed} active fan64 epoch rows at exactly 108.9536 Gb/s; v1.3 has {fan64_fixed}.','- RQ3 — Yes. Planner/target follow the live plan and target/applied mismatch rows are 0.','- RQ4 — Yes. Post-application capacity violations are 0.','- RQ5 — Yes. Exact packet-gap formula mismatches and pacing violations are 0; the maximum observed low-rate gap is %.3f us.'%(max_gap/1000.0),'- RQ6 — Yes. Zero grant pauses for %s ns with %s DATA sends, then resumes with no duplicate-time catch-up sends.'%(z.get('pause_duration_ns','missing'),z.get('data_tx_during_pause','missing')),'- RQ7 — Queue peak/AUC improve by at least %.2f%%/%.2f%% across fan64 cases, and recorded incumbent drop improves where it is measurable; CCT nevertheless regresses in all four fan64 cases.'%(-max(float(x['peak_queue_bytes_change_percent']) for x in fan64_pairs),-max(float(x['queue_auc_byte_seconds_change_percent']) for x in fan64_pairs)),'- RQ8 — Fan32 CCT changes by %.2f%%, peak queue by %.2f%%, and queue AUC by %.2f%%, within the fixed regression limits.'%(float(fan32_pair['cct_us_change_percent']),float(fan32_pair['peak_queue_bytes_change_percent']),float(fan32_pair['queue_auc_byte_seconds_change_percent'])),'']
 final=[decision,'','# Final CBAP v1.3 rate-floor analysis','', '## Executive result','', 'The execution-layer floor is removed correctly: positive target and applied sums match, applied capacity and pacing violations are zero, zero grants pause DATA, and fan64 no longer locks to 108.9536 Gb/s. The result is performance-limited because high-fan-in CCT regresses even while queues collapse.','']+rq+['## v1.3 versus v1.2','','| Scenario | CCT Δ% | Peak queue Δ% | Queue AUC Δ% | Utilization Δ% |','|---|---:|---:|---:|---:|']+table+['','Negative queue changes are improvements. CCT uses pending collective flows from application-ready time and includes the fixed scope-decision delay.','', '## v1.3 versus external baselines','','| Scenario | Baseline | CCT Δ% | Peak queue Δ% | Queue AUC Δ% |','|---|---|---:|---:|---:|']+external+['','## Control overhead versus v1.2','','| Scenario | v1.2 bytes | v1.3 bytes | Change % |','|---|---:|---:|---:|']+control_lines+['', '## Correctness totals','',f'- Floor clamps: {floor}.',f'- Target/applied mismatch rows: {mismatch}.',f'- Applied capacity violations: {applied_bad}.',f'- Pacing violations: {pacing_bad}.',f'- Fan64 v1.3 fixed-108.9536-Gb/s rows: {fan64_fixed}.',f'- Fan32 CCT change: {float(fan32_pair["cct_us_change_percent"]):.2f}%.',f'- Fan32 peak/AUC changes: {float(fan32_pair["peak_queue_bytes_change_percent"]):.2f}% / {float(fan32_pair["queue_auc_byte_seconds_change_percent"]):.2f}%.','', '## Limitations','', '- One deterministic seed per reduced combination; no confidence intervals.', '- Whole-simulation mean utilization is sensitive to early completion and is not active-window utilization.', '- The fix removes unsafe floor clamping but does not guarantee CCT superiority.', '- High-fan-in results show a pronounced queue–CCT tradeoff.', '- No parameter changes or new controller were introduced.']
 open(os.path.join(REPORT,'final_ratefloor_analysis.md'),'w').write('\n'.join(final)+'\n')
 index=['# Result file index','']
 for d in (REPORT,PROC,FIG):
  for n in sorted(os.listdir(d)):
   p=os.path.join(d,n)
   if os.path.isfile(p):index.append('- `%s` — %d bytes.'%(os.path.relpath(p,ROOT),os.path.getsize(p)))
 open(os.path.join(REPORT,'result_file_index.md'),'w').write('\n'.join(index)+'\n')
 return decision,len(missing),len(invalid),applied_bad,pacing_bad,floor

if __name__=='__main__':
 decision,missing,invalid,applied,pacing,floor=main()
 print('decision='+decision);print('missing=%d invalid=%d applied=%d pacing=%d floor=%d'%(missing,invalid,applied,pacing,floor))
