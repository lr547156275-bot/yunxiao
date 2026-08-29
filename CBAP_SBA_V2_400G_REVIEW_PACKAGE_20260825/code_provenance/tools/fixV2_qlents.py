# -*- coding: utf-8 -*-
# v2 observation-only patch: QLEN_TS_FILE / QLEN_TS_INTERVAL_NS.
#
# Preflight round 1 showed the 64-way burst spreads its backlog across the
# multi-tier fabric, so the single-bottleneck timeseries cannot verify the
# first-order arrival theory.  This adds an AGGREGATE cross-switch queue
# timeseries (sum + max port over all switch egress queues), emitted from the
# existing monitor_buffer walk.  Default OFF (empty file key) = v1
# byte-identical, to be proven by the usual twin regression.
import io
import sys

T = '/work/simulation/scratch/third.cc'
t = io.open(T, encoding='utf-8', errors='surrogateescape').read()
if 'qlen_ts_file' in t:
    print('already applied')
    sys.exit(0)

BSN = chr(92) + 'n'          # backslash-n as it appears in C source
BST = chr(92) + 't'          # backslash-t as it appears in C source
edits = []


def E(tag, old, new):
    edits.append((tag, old, new))


E('globals',
  'string qlen_mon_file;',
  'string qlen_mon_file;\n'
  '// v2: aggregate cross-switch queue timeseries (observation only)\n'
  'string qlen_ts_file;\n'
  'uint64_t qlen_ts_interval = 10000;\n'
  'FILE* qlen_ts_output = NULL;')
E('parse',
  "<< qlen_mon_file << '" + BSN + "';",
  "<< qlen_mon_file << '" + BSN + "';\n"
  '\t\t\t}else if (key.compare("QLEN_TS_FILE") == 0){\n'
  '\t\t\t\tconf >> qlen_ts_file;\n'
  '\t\t\t\tstd::cout << "QLEN_TS_FILE' + BST + BST + BST + BST +
  '" << qlen_ts_file << \'' + BSN + '\';\n'
  '\t\t\t}else if (key.compare("QLEN_TS_INTERVAL_NS") == 0){\n'
  '\t\t\t\tconf >> qlen_ts_interval;\n'
  '\t\t\t\tstd::cout << "QLEN_TS_INTERVAL_NS' + BST + BST + BST +
  '" << qlen_ts_interval << \'' + BSN + '\';')
E('fn-locals',
  'void monitor_buffer(FILE* qlen_output, NodeContainer *n){',
  'void monitor_buffer(FILE* qlen_output, NodeContainer *n){\n'
  '\tuint64_t qlen_ts_total = 0, qlen_ts_maxport = 0;')
E('fn-sum',
  'queue_result[i][j].add(size);',
  'queue_result[i][j].add(size);\n'
  '\t\t\t\tqlen_ts_total += size;\n'
  '\t\t\t\tif (size > qlen_ts_maxport)\n'
  '\t\t\t\t\tqlen_ts_maxport = size;')
E('fn-emit',
  '\tif (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0){',
  '\tif (qlen_ts_output != NULL && qlen_ts_interval > 0 &&\n'
  '\t\t\tSimulator::Now().GetTimeStep() % qlen_ts_interval == 0){\n'
  '\t\tfprintf(qlen_ts_output, "%lu,%lu,%lu' + BSN + '",\n'
  '\t\t\tSimulator::Now().GetTimeStep(), qlen_ts_total, qlen_ts_maxport);\n'
  '\t\tfflush(qlen_ts_output);\n'
  '\t}\n'
  '\tif (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0){')
E('open',
  'FILE* qlen_output = fopen(qlen_mon_file.c_str(), "w");',
  'FILE* qlen_output = fopen(qlen_mon_file.c_str(), "w");\n'
  '\tif (!qlen_ts_file.empty()){\n'
  '\t\tqlen_ts_output = fopen(qlen_ts_file.c_str(), "w");\n'
  '\t\tif (qlen_ts_output == NULL)\n'
  '\t\t\tConfigError("cannot open " + qlen_ts_file);\n'
  '\t\tfprintf(qlen_ts_output,\n'
  '\t\t\t"time_ns,total_queue_bytes,max_port_queue_bytes' + BSN + '");\n'
  '\t}')

bad = 0
for tag, old, new in edits:
    n = t.count(old)
    print('%-10s count=%d %s' % (tag, n, 'OK' if n == 1 else 'FAIL'))
    if n != 1:
        bad += 1
if bad:
    print('ANCHOR FAIL -- nothing written')
    sys.exit(2)
for tag, old, new in edits:
    t = t.replace(old, new, 1)
io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(t)
print('qlen_ts observation patch applied (default OFF = v1 byte-identical)')
