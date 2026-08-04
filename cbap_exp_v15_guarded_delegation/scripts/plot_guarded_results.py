#!/usr/bin/env python3
import csv,html,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
p=os.path.join(ROOT,"processed","summary_by_run.csv")
rows=list(csv.DictReader(open(p))) if os.path.isfile(p) else []
try:
 import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
except Exception:
 plt=None
plots=[("newcomer_cct","group_rct_max_us"),("incumbent_remaining_bytes","incumbent_remaining_bytes"),
 ("incumbent_completion_time","all_work_makespan_seconds"),("all_work_makespan","all_work_makespan_seconds"),
 ("peak_queue","queue_max_bytes"),("queue_auc","queue_auc_byte_seconds"),
 ("desired_vs_applied_aggregate_rate","payload_goodput_gbps"),("envelope_budget_and_incumbent_reserve","incumbent_remaining_fraction"),
 ("reserve_release_timeline","incumbent_remaining_fraction"),("queue_timeline","queue_max_bytes"),
 ("incumbent_newcomer_throughput","payload_goodput_gbps"),("control_message_comparison","total_control_bytes")]
os.makedirs(os.path.join(ROOT,"figures"),exist_ok=True)

colors={
 "dcqcn":"#4C78A8","hpcc_int":"#F58518","cbap_init_only":"#E45756",
 "cbap_full_v13_ratefloor_fix":"#72B7B2",
 "cbap_full_v14_stable_handoff":"#54A24B",
 "cbap_full_v15_guarded_delegation":"#B279A2"}

def fallback_plot(name,key,vals,labels):
 # The experiment VM intentionally has no online Python dependencies.  Keep
 # plotting deterministic and bounded with a small SVG/PDF renderer instead
 # of making result packaging depend on matplotlib installation.
 width,height=960,460; left,right,top,bottom=85,25,55,95
 chart_w=width-left-right; chart_h=height-top-bottom
 ymax=max(vals+[0.0]); ymax=ymax if ymax>0 else 1.0
 bar_w=chart_w/max(len(vals),1)
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'%(width,height,width,height),
      '<rect width="100%" height="100%" fill="white"/>',
      '<text x="%d" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">%s</text>'%(width//2,html.escape(name.replace('_',' '))),
      '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="black"/>'%(left,top,left,top+chart_h),
      '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="black"/>'%(left,top+chart_h,left+chart_w,top+chart_h)]
 for tick in range(6):
  value=ymax*tick/5.0; y=top+chart_h-chart_h*tick/5.0
  svg.append('<line x1="%d" y1="%.2f" x2="%d" y2="%.2f" stroke="#dddddd"/>'%(left,y,left+chart_w,y))
  svg.append('<text x="%d" y="%.2f" text-anchor="end" font-family="sans-serif" font-size="10">%.4g</text>'%(left-5,y+4,value))
 for i,(value,label) in enumerate(zip(vals,labels)):
  h=chart_h*value/ymax; x=left+i*bar_w+0.5; y=top+chart_h-h
  svg.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'%(x,y,max(bar_w-1,0.5),h,colors.get(label,"#777777")))
 svg.extend(['<text x="%d" y="%d" text-anchor="middle" font-family="sans-serif" font-size="12">preregistered run index</text>'%(left+chart_w//2,height-14),
             '<text transform="translate(18 %d) rotate(-90)" text-anchor="middle" font-family="sans-serif" font-size="12">%s</text>'%(top+chart_h//2,html.escape(key))])
 legend=[]
 for label in labels:
  if label not in legend: legend.append(label)
 lx=left
 for label in legend:
  svg.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>'%(lx,height-70,colors.get(label,"#777777")))
  svg.append('<text x="%d" y="%d" font-family="sans-serif" font-size="9">%s</text>'%(lx+13,height-61,html.escape(label)))
  lx+=max(115,8*len(label))
 svg.append('</svg>')
 open(os.path.join(ROOT,"figures",name+".svg"),"w").write('\n'.join(svg)+'\n')

 from reportlab.pdfgen import canvas
 from reportlab.lib.pagesizes import landscape,letter
 from reportlab.lib.colors import HexColor
 pdf=os.path.join(ROOT,"figures",name+".pdf"); c=canvas.Canvas(pdf,pagesize=landscape(letter))
 pw,ph=landscape(letter); ml,mr,mt,mb=65,20,42,70; cw=pw-ml-mr; ch=ph-mt-mb
 c.setFont("Helvetica-Bold",14); c.drawCentredString(pw/2,ph-22,name.replace('_',' '))
 c.line(ml,mb,ml,mb+ch); c.line(ml,mb,ml+cw,mb)
 bw=cw/max(len(vals),1)
 for i,(value,label) in enumerate(zip(vals,labels)):
  h=ch*value/ymax; c.setFillColor(HexColor(colors.get(label,"#777777"))); c.rect(ml+i*bw+.4,mb,max(bw-.8,.4),h,stroke=0,fill=1)
 c.setFillColorRGB(0,0,0); c.setFont("Helvetica",8); c.drawCentredString(ml+cw/2,18,"preregistered run index")
 c.save()

for name,key in plots:
 vals=[]; labels=[]
 for r in rows:
  try: vals.append(float(r.get(key,0) or 0)); labels.append(r.get("algorithm_name",r.get("algorithm","")))
  except: pass
 if plt is None:
  fallback_plot(name,key,vals,labels)
 else:
  fig,ax=plt.subplots(figsize=(8,3.8)); ax.bar(range(len(vals)),vals); ax.set_ylabel(key); ax.set_xlabel("preregistered run index")
  ax.set_title(name.replace("_"," ")); fig.tight_layout()
  for ext in ("svg","pdf"):fig.savefig(os.path.join(ROOT,"figures",name+"."+ext))
  plt.close(fig)
