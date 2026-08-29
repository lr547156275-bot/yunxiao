import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
assert src.count("CBAP_PFC_AUDIT_FILE")==0, "already patched"

a='''			else if(key.compare("CBAP_PORT_SUMMARY_FILE")==0)
				conf>>cbap_port_summary_file;'''
assert src.count(a)==1
src=src.replace(a, a+'''
			else if(key.compare("CBAP_PFC_AUDIT_FILE")==0)
				conf>>cbap_pfc_audit_file;''')

# Build the target line piecewise so no escape is ambiguous.
NL = chr(92) + 'n'          # the two characters  \ n  as they appear in C source
b = '\tstd::cout << "Running Simulation.' + NL + '";'
assert src.count(b)==1, ("anchor count", src.count(b))

hdr = ('"time_ns,link_id,cbap_egress_queue_bytes,"' + '\n'
       '\t\t\t\t"egress_port_occupancy_bytes,worst_ingress_port,"' + '\n'
       '\t\t\t\t"pfc_counter_occupancy_bytes,dynamic_pfc_threshold_bytes,"' + '\n'
       '\t\t\t\t"pfc_slack_bytes,hdrm_bytes,shared_used_bytes,"' + '\n'
       '\t\t\t\t"total_hdrm,total_rsrv,sum_ingress_bytes,pfc_guard_state' + NL + '");')
ins = ('\tif (!cbap_pfc_audit_file.empty()){\n'
       '\t\tcbap_pfc_audit_csv = fopen(cbap_pfc_audit_file.c_str(), "w");\n'
       '\t\tif (cbap_pfc_audit_csv)\n'
       '\t\t\tfprintf(cbap_pfc_audit_csv,\n'
       '\t\t\t\t' + hdr + '\n'
       '\t}\n')
src=src.replace(b, ins + b)

io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("OK: key x%d, fopen x%d" % (src.count('"CBAP_PFC_AUDIT_FILE"'),
                                  src.count('cbap_pfc_audit_csv = fopen')))
