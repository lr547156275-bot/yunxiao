#!/usr/bin/env python3
import math
def project(desired,paths,budgets):
 sums={l:sum(desired[f] for f,p in paths.items() if l in p) for l in budgets}
 scales={l:min(1.0,budgets[l]/sums[l]) if sums[l] else 1.0 for l in budgets}
 flow_scale={f:min(scales[l] for l in p) for f,p in paths.items()}
 applied={f:math.floor(desired[f]*flow_scale[f]) for f in desired}
 return scales,flow_scale,applied
desired={0:80,1:60,2:40}; paths={0:[1,2],1:[1],2:[2]}; budgets={1:70,2:60}
scales,flow_scale,applied=project(desired,paths,budgets)
assert flow_scale[0]==min(scales[1],scales[2])
assert flow_scale[0]!=scales[1]*scales[2]
for l,b in budgets.items(): assert sum(applied[f] for f in applied if l in paths[f])<=b
assert all(0<=x<=1 for x in scales.values())
print("PASS guarded path-min proportional model")
