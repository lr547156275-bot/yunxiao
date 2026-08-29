import io,re
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# collision check first: the key must not already be parsed anywhere
for k in ("CBAP_PFC_AUDIT_FILE",):
    assert src.count(k)==0, ("collision",k,src.count(k))

# find an existing string-file config key to copy the parse idiom from
m=re.search(r'\n(\t*)else if \(key == "CBAP_PORT_SUMMARY_FILE"\) \{\n(.*?)\n\1\}', src, re.S)
print("parse idiom found:", bool(m))
if m: print(repr(m.group(0)[:300]))
