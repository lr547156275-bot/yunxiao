import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# Replace the sentinel-based arming with an explicit bool.  flow_id 0 is a
# legitimate flow (the background flow), so 0 cannot double as "disarmed".
old_g='''static uint64_t cbap_pending_effect_flow = 0;
static uint64_t cbap_pending_effect_bytes = 0;'''
assert src.count(old_g)==1
src=src.replace(old_g,'''static uint64_t cbap_pending_effect_flow = 0;
static bool cbap_effect_armed = false;   // flow_id 0 is REAL (the bg flow), so
                                         // 0 must not double as "disarmed"
static uint64_t cbap_pending_effect_bytes = 0;''')

old1='''	cbap_last_sender_effect_ns = 0;
	cbap_pending_effect_flow = flowId;'''
assert src.count(old1)==1
src=src.replace(old1,'''	cbap_last_sender_effect_ns = 0;
	cbap_pending_effect_flow = flowId;
	cbap_effect_armed = true;''')

old2='''	if (!cbap_actuation_csv || !qp || cbap_pending_effect_flow == 0)
		return;'''
assert src.count(old2)==1
src=src.replace(old2,'''	if (!cbap_actuation_csv || !qp || !cbap_effect_armed)
		return;''')

old3='''	if (!cbap_actuation_csv || cbap_pending_effect_flow == 0)
		return;'''
assert src.count(old3)==1
src=src.replace(old3,'''	if (!cbap_actuation_csv || !cbap_effect_armed)
		return;''')

old4='''	// One measurement per rate command; re-arm only on the next command.
	cbap_pending_effect_flow = 0;
	cbap_last_sender_effect_ns = 0;'''
assert src.count(old4)==1
src=src.replace(old4,'''	// One measurement per rate command; re-arm only on the next command.
	cbap_effect_armed = false;
	cbap_last_sender_effect_ns = 0;''')

io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("sentinel fixed; armed-flag uses: %d" % src.count("cbap_effect_armed"))
