# -*- coding: utf-8 -*-
# Add the TX_SERIALIZATION_TRACE_FILE config-key parser that fixF skipped.
#
# fixF guarded on `'TX_SERIALIZATION_TRACE_FILE' not in s`, but step 1 had
# already inserted a COMMENT containing that string, so the guard was already
# false and the parser block was silently not added.  Without it the key can
# never be read from the config file and the recorder could never turn on.
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'
s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

if 'key.compare("TX_SERIALIZATION_TRACE_FILE")' in s:
    print('already present; nothing to do')
    sys.exit(0)

a = '\t\t\telse if(key.compare("ROUND_TRACE_SELECTED_LINKS")==0) conf>>round_selected_link_ids;'
if s.count(a) != 1:
    print('ANCHOR FAIL: found %d' % s.count(a))
    sys.exit(2)

s = s.replace(a, a + '''
			else if(key.compare("TX_SERIALIZATION_TRACE_FILE")==0){
				conf>>tx_serialization_trace_file;
				std::cout << "TX_SERIALIZATION_TRACE_FILE\\t\\t"
					<< tx_serialization_trace_file << "\\n";
			}''')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('config-key parser added')
print('  key.compare sites : %d'
      % s.count('key.compare("TX_SERIALIZATION_TRACE_FILE")'))
