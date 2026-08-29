# -*- coding: utf-8 -*-
# Add CBAP_STEADY_CAP_FRACTION as a config key so the Pareto sweep can vary it.
# steadyCapFraction already exists in CbapConfig (default 0.995) but had no
# parser entry, so it was effectively hardcoded.  This adds ONLY the plumbing;
# the default stays 0.995 so every existing config reproduces byte-identically.
import io
import sys

T = '/work/simulation/scratch/third.cc'
s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

if 'CBAP_STEADY_CAP_FRACTION' in s:
    print('already applied')
    sys.exit(0)

a = 'uint32_t cbap_steady_cap = 0;'
if s.count(a) != 1:
    print('ANCHOR FAIL decl: %d' % s.count(a))
    sys.exit(2)
s = s.replace(a, a + '\ndouble cbap_steady_cap_fraction = 0.995;', 1)

a = '\t\t\telse if(key.compare("CBAP_STEADY_CAP_ENABLE")==0){'
if s.count(a) != 1:
    print('ANCHOR FAIL cfg: %d' % s.count(a))
    sys.exit(2)
s = s.replace(a, '''			else if(key.compare("CBAP_STEADY_CAP_FRACTION")==0){
				conf>>cbap_steady_cap_fraction;
				std::cout << "CBAP_STEADY_CAP_FRACTION\\t\\t"
					<< cbap_steady_cap_fraction << "\\n";
			}
''' + a, 1)

a = '\tconfig.steadyCapEnable = (cbap_steady_cap != 0);'
if s.count(a) != 1:
    print('ANCHOR FAIL assign: %d' % s.count(a))
    sys.exit(2)
s = s.replace(a, a + '\n\tconfig.steadyCapFraction = cbap_steady_cap_fraction;', 1)

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('cap-fraction key added')
print('  decl   : %d' % s.count('double cbap_steady_cap_fraction = 0.995;'))
print('  parse  : %d' % s.count('conf>>cbap_steady_cap_fraction;'))
print('  assign : %d' % s.count('config.steadyCapFraction = cbap_steady_cap_fraction;'))
