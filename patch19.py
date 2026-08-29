import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
a='\tWriteCbapSummaries();'
assert src.count(a)==1
src=src.replace(a,'\tWriteCbapActuationCounters();\n'+a)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("counters call inserted:", src.count("WriteCbapActuationCounters();"))
