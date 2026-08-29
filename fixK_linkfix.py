# -*- coding: utf-8 -*-
# Fix the link error: CausalPacerTrace statics were defined in third.cc (the
# program) but referenced from libns3-point-to-point (rdma-hw.cc).  Move the
# pacer statics into rdma-hw.cc so the library owns them; third.cc keeps only
# the queue-tracer statics, which only it references.
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'
H = '/workspaces/yunxiao/simulation/src/point-to-point/model/rdma-hw.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: %d' % (tag, got))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()
old = '''FILE *ns3::CausalPacerTrace::s_file = 0;
uint64_t ns3::CausalPacerTrace::s_lo = 0;
uint64_t ns3::CausalPacerTrace::s_hi = 0;
uint64_t ns3::CausalPacerTrace::s_rows = 0;
'''
need(s, old, 1, 'third-statics')
s = s.replace(old, '// CausalPacerTrace statics live in rdma-hw.cc (the library\n'
                   '// that references them); defining them here would leave the\n'
                   '// shared object with undefined references.\n')
io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)

c = io.open(H, encoding='utf-8', errors='surrogateescape').read()
if 'ns3::CausalPacerTrace::s_file' not in c:
    a = '#include "../../../scratch/causal-telemetry.h"'
    need(c, a, 1, 'hw-include')
    c = c.replace(a, a + '''
// Owned here: rdma-hw.cc is inside libns3-point-to-point, which references
// these symbols from ChangeRate.  Telemetry only.
FILE *ns3::CausalPacerTrace::s_file = 0;
uint64_t ns3::CausalPacerTrace::s_lo = 0;
uint64_t ns3::CausalPacerTrace::s_hi = 0;
uint64_t ns3::CausalPacerTrace::s_rows = 0;''')
    io.open(H, 'w', encoding='utf-8', errors='surrogateescape').write(c)

print('linkfix applied')
print('  third.cc pacer statics   : %d (expect 0)'
      % s.count('ns3::CausalPacerTrace::s_file = 0'))
print('  rdma-hw.cc pacer statics : %d (expect 1)'
      % c.count('ns3::CausalPacerTrace::s_file = 0'))
print('  third.cc queue statics   : %d (expect 1)'
      % s.count('ns3::CausalQueueTrace::s_file = 0'))
