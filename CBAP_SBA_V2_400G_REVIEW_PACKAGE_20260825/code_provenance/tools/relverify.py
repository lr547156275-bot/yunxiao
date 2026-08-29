# -*- coding: utf-8 -*-
# Verify the evidence-2026-08 release tars against the on-disk v1 outputs,
# then (only with --delete) remove the verified on-disk copies.
# Verification per tar: gzip/tar integrity, every member present on disk
# with identical size, plus sha256 spot-check of 12 sampled members.
# Runs on the codespace HOST.  Phase 1: python3 relverify.py
# Phase 2 (after human review): python3 relverify.py --delete
import hashlib
import os
import sys
import tarfile

ROOT = '/workspaces/yunxiao/simulation/experiment/scheme1_sba'
TARS = ['g1_matrix', 'g2_validation', 'g3_stress_frontier']
# the twin-regression reference outputs must stay on disk
EXCLUDE_TOP = {'scr8_b040_out'}
TDIR = '/tmp/relver'
DO_DELETE = '--delete' in sys.argv
report = []
all_ok = True
covered_top = set()

for name in TARS:
    p = os.path.join(TDIR, name + '.tar.gz')
    if not os.path.isfile(p):
        print('MISSING %s (download first)' % p)
        sys.exit(2)
    n_files = 0
    n_size_ok = 0
    missing = []
    size_bad = []
    members = []
    with tarfile.open(p, 'r:gz') as tf:
        for m in tf:
            if not m.isreg():
                continue
            n_files += 1
            members.append((m.name, m.size))
            covered_top.add(m.name.split('/')[0])
            dp = os.path.join(ROOT, m.name)
            if not os.path.isfile(dp):
                missing.append(m.name)
            elif os.path.getsize(dp) != m.size:
                size_bad.append(m.name)
            else:
                n_size_ok += 1
    # sha spot-check: 12 deterministic samples spread across the archive
    sha_bad = []
    idx = [int(i * (len(members) - 1) / 11.0) for i in range(12)]
    with tarfile.open(p, 'r:gz') as tf:
        for i in sorted(set(idx)):
            nm, sz = members[i]
            dp = os.path.join(ROOT, nm)
            if not os.path.isfile(dp):
                continue
            h1 = hashlib.sha256()
            fh = tf.extractfile(nm)
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                h1.update(chunk)
            h2 = hashlib.sha256()
            with open(dp, 'rb') as dfh:
                for chunk in iter(lambda: dfh.read(1 << 20), b''):
                    h2.update(chunk)
            if h1.hexdigest() != h2.hexdigest():
                sha_bad.append(nm)
    ok = not missing and not size_bad and not sha_bad
    all_ok = all_ok and ok
    report.append((name, n_files, n_size_ok, missing, size_bad, sha_bad))
    print('%s: files=%d size_ok=%d missing_on_disk=%d size_mismatch=%d '
          'sha_spot_bad=%d -> %s'
          % (name, n_files, n_size_ok, len(missing), len(size_bad),
             len(sha_bad), 'OK' if ok else 'FAIL'))
    for nm in (missing + size_bad + sha_bad)[:5]:
        print('   !! ' + nm)

print('covered top-level paths: %s' % ', '.join(sorted(covered_top)))
if not all_ok:
    print('VERIFY FAILED -- nothing will be deleted')
    sys.exit(3)
print('VERIFY OK: release tars fully cover the on-disk copies')

if DO_DELETE:
    import shutil
    freed = 0
    man = open('/workspaces/yunxiao/v2_400g/reports/'
               'DISK_RECLAIM_MANIFEST.txt', 'a')
    man.write('# verified against evidence-2026-08 assets; deleted:\n')
    for name in TARS:
        p = os.path.join(TDIR, name + '.tar.gz')
        with tarfile.open(p, 'r:gz') as tf:
            for m in tf:
                if not m.isreg():
                    continue
                if m.name.split('/')[0] in EXCLUDE_TOP:
                    continue
                dp = os.path.join(ROOT, m.name)
                if os.path.isfile(dp):
                    freed += os.path.getsize(dp)
                    man.write(m.name + '\n')
                    os.remove(dp)
    man.close()
    # sweep now-empty directories under the covered top-level paths
    for top in covered_top - EXCLUDE_TOP:
        for dirpath, dirnames, filenames in os.walk(
                os.path.join(ROOT, top), topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
    print('DELETED %.2f GB of verified-archived files; manifest appended to '
          'v2_400g/reports/DISK_RECLAIM_MANIFEST.txt' % (freed / 1e9))
else:
    print('(dry run -- rerun with --delete to reclaim)')
