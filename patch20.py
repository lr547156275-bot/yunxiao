import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
lines=src.split('\n')
# lines 1099..1115 region: repair the two broken literals
NL=chr(92)+'n'
bad1='\t\t"0,0,0,0,0,counters_unmatched_%lu_superseded_%lu_negative_%lu,0,0,0'
bad2='\t\t"0,0,0,0,0,counters_pending_%lu_inflight_%lu,0,0,0'
n1=n2=0
out=[]
i=0
while i < len(lines):
    L=lines[i]
    if L==bad1 and i+1<len(lines) and lines[i+1]=='",':
        out.append(bad1+NL+'",'); i+=2; n1+=1; continue
    if L==bad2 and i+1<len(lines) and lines[i+1]=='",':
        out.append(bad2+NL+'",'); i+=2; n2+=1; continue
    out.append(L); i+=1
src='\n'.join(out)
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("repaired literal 1 x%d, literal 2 x%d" % (n1,n2))
