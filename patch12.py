import io, re
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# The observers were gated on cbap_actuation_csv, which is opened 44 lines LATER
# (line 4472) than the connect block (4428) -- so the guard was always false and
# the trace sources were never connected.  Gate on the FILENAME instead, exactly
# like the rate_command hook one line above, which did work.
old='	if (cbap_actuation_csv && !cbap_links.empty()){'
assert src.count(old)==1, src.count(old)
src=src.replace(old,'''	// Gate on the filename, not the FILE* -- the handle is opened later, so
	// testing it here would silently skip every TraceConnect (it did).
	if (!cbap_actuation_file.empty() && !cbap_links.empty()){''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)

# verify ordering claim
i_connect=src.index('!cbap_actuation_file.empty() && !cbap_links.empty()')
i_open=src.index('cbap_actuation_csv = fopen')
print("connect-block offset %d, fopen offset %d -> connect is %s fopen"
      % (i_connect, i_open, "BEFORE" if i_connect<i_open else "AFTER"))
print("guard now on filename:", src.count('!cbap_actuation_file.empty() && !cbap_links.empty()'))
