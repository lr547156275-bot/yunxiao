import csv, os
D='/work/simulation/experiment/scheme1_sba/analysis/s3_full_metrics_v1'
r=list(csv.DictReader(open(os.path.join(D,'S3_FULL_METRICS.csv'))))
def g(mid,algo,win,scope='link84:1'):
    for x in r:
        if x['metric_id']==mid and x['algorithm']==algo and x['window']==win and x['scope']==scope:
            return x['value']
    return 'NA'
def sh(v,n=12):
    try: return ('%.6f'%float(v))[:n]
    except: return str(v)[:n]
out=[]
for win in ('W2','W3'):
    out.append('=== %s served/util/idle ==='%win)
    for k in ('C.served.wire.mean','C.served.wire.p95','C.served.wire.max','C.utilization.mean','C.utilization.max','C.idle.fraction','C.util.frac_below_95','C.service_deficit.frac','C.served.total_bytes'):
        out.append('  %-26s CBAP=%-12s DCQCN=%s'%(k,sh(g(k,'CBAP',win)),sh(g(k,'DCQCN',win))))
    out.append('=== %s queue ==='%win)
    for k in ('D.queue.bytes.mean','D.queue.bytes.p95','D.queue.bytes.max','D.queue.delay.max','D.queue.pct_Qabs.max'):
        out.append('  %-26s CBAP=%-12s DCQCN=%s'%(k,sh(g(k,'CBAP',win)),sh(g(k,'DCQCN',win))))
out.append('=== CBAP-only arrival/service W2 ===')
for k in ('C.arrival.wire.mean','C.arrival.wire.max','C.service_rate.mean','C.service_rate.max','C.arrival.frac_above_C'):
    out.append('  %-26s %s'%(k,sh(g(k,'CBAP','W2'))))
out.append('=== zones/migration/ecn ===')
for x in r:
    if x['metric_id'] in ('E.zone.fraction','E.zone.transitions') and x['window']=='W2':
        out.append('  %-20s %-14s %s'%(x['metric_id'],x['scope'],sh(x['value'])))
    if x['metric_id'].startswith('E.migration'):
        out.append('  %-30s %-8s %s'%(x['metric_id'],x['window'],sh(x['value'])))
    if x['metric_id'].startswith('E.boost') or x['metric_id'].startswith('E.drain'):
        out.append('  %-30s %-8s %s'%(x['metric_id'],x['window'],sh(x['value'])))
out.append('  ECN W2 CBAP=%s DCQCN=%s'%(sh(g('G.ecn.marks','CBAP','W2')),sh(g('G.ecn.marks','DCQCN','W2'))))
open(os.path.join(D,'_report.txt'),'w').write('\n'.join(out))
print('\n'.join(out))
