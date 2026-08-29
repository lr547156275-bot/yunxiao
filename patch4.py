import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()

# --- A) per-ingress-port PFC detail file -----------------------------------
assert src.count("CBAP_PFC_PORTS_FILE")==0, "already patched"
a='''			else if(key.compare("CBAP_PFC_AUDIT_FILE")==0)
				conf>>cbap_pfc_audit_file;'''
assert src.count(a)==1
src=src.replace(a, a+'''
			else if(key.compare("CBAP_PFC_PORTS_FILE")==0)
				conf>>cbap_pfc_ports_file;
			else if(key.compare("CBAP_ACTUATION_FILE")==0)
				conf>>cbap_actuation_file;''')

b='''string cbap_pfc_audit_file;
static FILE *cbap_pfc_audit_csv = NULL;'''
assert src.count(b)==1
src=src.replace(b, b+'''
// Per-ingress-port PFC detail: every port that actually feeds the bottleneck
// egress gets its own row, so "min slack" is a measured minimum over real
// contributors rather than over all ports indiscriminately.
string cbap_pfc_ports_file;
static FILE *cbap_pfc_ports_csv = NULL;
// Actuation closed loop: rate command -> sender effect -> first affected packet
// observed at the bottleneck.  Read-only; no control decision uses these.
string cbap_actuation_file;
static FILE *cbap_actuation_csv = NULL;
static uint64_t cbap_last_rate_cmd_ns = 0;
static uint64_t cbap_last_rate_cmd_flow = 0;
static uint64_t cbap_last_rate_cmd_bps = 0;
static uint64_t cbap_last_sender_effect_ns = 0;
static uint64_t cbap_pending_effect_flow = 0;
static uint64_t cbap_pending_effect_bytes = 0;''')

io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("A ok: keys=%d/%d globals ok" % (src.count('"CBAP_PFC_PORTS_FILE"'),
                                       src.count('"CBAP_ACTUATION_FILE"')))
