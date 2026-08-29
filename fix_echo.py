import io
p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()
bad = '<< " migration_trace=" << (cbap_migration_trace ? 1 : 0) << "\n";'
good = '<< " migration_trace=" << (cbap_migration_trace ? 1 : 0) << std::endl;'
n = s.count(bad)
if n != 1:
    print('BAD ANCHOR count=%d' % n); raise SystemExit(2)
s = s.replace(bad, good)
io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('fixed: std::endl used, count=%d' % s.count('std::endl;'))
