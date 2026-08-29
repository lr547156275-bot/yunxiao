# -*- coding: utf-8 -*-
# Trace columns for the three sets and the lifecycle counters.  Telemetry only:
# no control-path change.  Without these the item-3 assertions cannot be checked
# against a real run, and the previous acceptance pass had to guess at
# scope_violations / ownership_transitions (they were absent, reading as 0).
import io
import sys

T = '/workspaces/yunxiao/simulation/scratch/third.cc'


def need(hay, needle, n=1, tag=''):
    got = hay.count(needle)
    if got != n:
        print('ANCHOR FAIL [%s]: expected %d, found %d' % (tag, n, got))
        sys.exit(2)


s = io.open(T, encoding='utf-8', errors='surrogateescape').read()

if 'qc.floorCount' not in s:
    old = '''		"%lu,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.0f,%s,%lu,%lu,%lu,%lu,%lu,"
		"%lu,%lu,%lu,%lu,%u,%u,%u\\n",'''
    need(s, old, 1, 't:fmt')
    s = s.replace(old, '''		"%lu,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.0f,%s,%lu,%lu,%lu,%lu,%lu,"
		"%lu,%lu,%lu,%lu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\\n",''')

    old = '''		qc.protectedCount,
		qc.ownsRates ? 1u : 0u,
		qc.exitRecoveryPending ? 1u : 0u);'''
    need(s, old, 1, 't:args')
    s = s.replace(old, '''		qc.protectedCount,
		qc.ownsRates ? 1u : 0u,
		qc.exitRecoveryPending ? 1u : 0u,
		// defect C: the three sets, reported separately so the assertion
		// floor=65 / newgen=64 / oldside=1 is checkable per epoch.
		qc.floorCount,
		qc.newGenCount,
		qc.oldSideCount,
		qc.ledgerCount,
		// defect B lifecycle counters
		qc.ownershipTransitions,
		qc.scopeViolations,
		qc.pathMetadataMissing);''')

    old = '''				"owns_rates,exit_recovery_pending\\n");'''
    need(s, old, 1, 't:hdr')
    s = s.replace(old, '''				"owns_rates,exit_recovery_pending,"
				"floor_count,new_gen_count,old_side_count,ledger_count,"
				"ownership_transitions,scope_violations,"
				"path_metadata_missing\\n");''')

io.open(T, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('trace: +7 columns (floor/new_gen/old_side/ledger + 3 counters) = 31')
print('  header updated : %d' % s.count('floor_count,new_gen_count'))
print('  args updated   : %d' % s.count('qc.floorCount'))
