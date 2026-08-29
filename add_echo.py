import io
p = '/work/simulation/scratch/third.cc'
s = io.open(p, encoding='utf-8', errors='surrogateescape').read()
if 'CBAP_REALLOC_PARSED' in s:
    print('already present'); raise SystemExit(0)
a = '\tconfig.migrationTrace = cbap_migration_trace;'
assert s.count(a) == 1, ('anchor', s.count(a))
# Echo the PARSED values (not the file text) so the run.log itself is the
# evidence.  Logging only; no algorithm, parameter or threshold is touched.
s = s.replace(a, a + '''
\tstd::cout << "CBAP_REALLOC_PARSED migration_enable=" << (cbap_migration_enable ? 1 : 0)
\t\t<< " core_initial_release=" << cbap_core_initial_release
\t\t<< " initial_release_ratio=" << cbap_initial_release_ratio
\t\t<< " migration_trace=" << (cbap_migration_trace ? 1 : 0) << "\n";
\tfflush(stdout);''')
io.open(p, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('echo added; sites =', s.count('CBAP_REALLOC_PARSED'))
