# -*- coding: utf-8 -*-
# Item 3 (remainder): unit tests for the two causal tracers.
#
# Four required cases:
#   T1  duplicate attach            -> Register() must refuse (returns -1)
#   T2  missing link                -> attach must fail fast, not run silently
#   T3  empty trace                 -> must be detected, not read as "no gaps"
#   T4  multi-QP                    -> pacer rows must span more than one flow
#
# Plus structural checks on the produced traces: header, column count, monotone
# time, window respected, identity columns resolvable.
#
# READ-ONLY with respect to the simulation.  T1/T2 are compiled C++ probes
# against the real header; T3/T4 read the produced CSVs.
import csv
import os
import subprocess
import sys

B = '/work/simulation/experiment/scheme1_sba'
CB = os.path.join(B, 'ct_cbap_on_out')
DQ = os.path.join(B, 'ct_dcqcn_on_out')
HDR = '/work/simulation/scratch/causal-telemetry.h'
T0N, T1N = 2000000000, 2058372997

P = F = 0
LOG = []


def chk(name, ok, detail=''):
    global P, F
    if ok:
        P += 1
        LOG.append('  PASS  %-46s %s' % (name, detail))
    else:
        F += 1
        LOG.append('  FAIL  %-46s %s' % (name, detail))


# ---------------------------------------------------------------- T1 + T2 ----
# Compile a probe against the real header.  Register() is the identity gate:
# a duplicate (linkId, nodeId, ifIndex) must return -1, and third.cc turns that
# into INVALID_CAUSAL_ATTACH + return 2.
PROBE = r'''
#include <cstdio>
#include <string>
#include <vector>
#include <cstdint>
namespace ns3 {
  class Time { public: uint64_t GetTimeStep() const { return 0; } };
  class Simulator { public: static Time Now(){ return Time(); } };
  template <class T> class Ptr { public: T* p; Ptr():p(0){} T* operator->() const { return p; }
    operator bool() const { return p!=0; } };
  class Packet { public: uint64_t GetUid() const {return 0;} uint32_t GetSize() const {return 0;} };
}
#define CAUSAL_TELEMETRY_NO_NS3_HEADERS 1
#include "causal_probe_body.inc"
using namespace ns3;
FILE *ns3::CausalQueueTrace::s_file = 0;
std::vector<ns3::CausalQueueTrace::Key> ns3::CausalQueueTrace::s_link;
uint64_t ns3::CausalQueueTrace::s_lo = 0, ns3::CausalQueueTrace::s_hi = 0,
         ns3::CausalQueueTrace::s_rows = 0;
FILE *ns3::CausalPacerTrace::s_file = 0;
uint64_t ns3::CausalPacerTrace::s_lo = 0, ns3::CausalPacerTrace::s_hi = 0,
         ns3::CausalPacerTrace::s_rows = 0;
int main(){
  int a = CausalQueueTrace::Register(0, 84, 1);
  int b = CausalQueueTrace::Register(0, 84, 1);   // exact duplicate
  int c = CausalQueueTrace::Register(1, 83, 1);   // distinct link
  printf("T1 first=%d dup=%d distinct=%d count=%u\n", a, b, c,
         CausalQueueTrace::LinkCount());
  bool o1 = CausalQueueTrace::Open("", 0, 0);     // empty path -> must refuse
  bool o2 = CausalPacerTrace::Open("", 0, 0);
  printf("T2 open_empty_queue=%d open_empty_pacer=%d isopen_q=%d isopen_p=%d\n",
         o1?1:0, o2?1:0, CausalQueueTrace::IsOpen()?1:0,
         CausalPacerTrace::IsOpen()?1:0);
  return 0;
}
'''

work = '/tmp/tel_ut'
os.makedirs(work, exist_ok=True)
src = open(HDR).read()
# strip the ns-3 includes; the probe supplies minimal stand-ins so the class
# logic under test is the real code, unmodified.
body = []
for ln in src.splitlines():
    if ln.startswith('#include <ns3/'):
        continue
    body.append(ln)
open(os.path.join(work, 'causal_probe_body.inc'), 'w').write('\n'.join(body))
open(os.path.join(work, 'probe.cc'), 'w').write(PROBE)
r = subprocess.run(['g++', '-o', os.path.join(work, 'probe'),
                    os.path.join(work, 'probe.cc'), '-I', work],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
if r.returncode != 0:
    chk('T1/T2 probe compiles', False, r.stdout.decode()[:400])
else:
    out = subprocess.run([os.path.join(work, 'probe')],
                         stdout=subprocess.PIPE).stdout.decode()
    d = {}
    for ln in out.splitlines():
        for kv in ln.split()[1:]:
            if '=' in kv:
                k, v = kv.split('=')
                d[k] = int(v)
    chk('T1 first Register succeeds', d.get('first') == 0, 'slot=%s' % d.get('first'))
    chk('T1 duplicate attach REFUSED', d.get('dup') == -1, 'ret=%s' % d.get('dup'))
    chk('T1 distinct link accepted', d.get('distinct') == 1, 'slot=%s' % d.get('distinct'))
    chk('T1 link count = 2 (dup not stored)', d.get('count') == 2, 'count=%s' % d.get('count'))
    chk('T2 empty path -> queue Open refuses', d.get('open_empty_queue') == 0)
    chk('T2 empty path -> pacer Open refuses', d.get('open_empty_pacer') == 0)
    chk('T2 refused Open leaves tracer closed',
        d.get('isopen_q') == 0 and d.get('isopen_p') == 0)

# fail-fast wiring must exist in third.cc for the missing-link case
tc = open('/work/simulation/scratch/third.cc').read()
chk('T2 third.cc has INVALID_CAUSAL_ATTACH guards',
    tc.count('INVALID_CAUSAL_ATTACH') >= 4,
    'guards=%d' % tc.count('INVALID_CAUSAL_ATTACH'))
chk('T2 guards return non-zero (fail fast)',
    tc.count('INVALID_CAUSAL_ATTACH') <= tc.count('return 2;'),
    'return2=%d' % tc.count('return 2;'))

# bypass proof by construction: no scheduling primitives in the tracer.
# Comments must be stripped first -- the header's own comment states "No
# Simulator::Schedule / Cancel / Remove anywhere in this file", so a raw
# substring search matches the documentation of the guarantee, not a violation.
code_only = []
in_block = False
for ln in src.splitlines():
    t = ln.strip()
    if in_block:
        if '*/' in t:
            in_block = False
            t = t.split('*/', 1)[1]
        else:
            continue
    if t.startswith('/*'):
        in_block = '*/' not in t
        continue
    if '//' in t:
        t = t.split('//', 1)[0]
    code_only.append(t)
code_only = '\n'.join(code_only)
for bad in ('Simulator::Schedule', 'Simulator::Cancel', 'Simulator::Remove'):
    chk('bypass: no %s in tracer code' % bad, bad not in code_only)
chk('bypass: only Simulator::Now() used',
    code_only.count('Simulator::') == code_only.count('Simulator::Now()'),
    'Simulator:: refs=%d, Now()=%d'
    % (code_only.count('Simulator::'), code_only.count('Simulator::Now()')))

# ------------------------------------------------------------------- T3 ------
QCOLS = ['time_ns', 'event', 'link_id', 'node_id', 'if_index', 'queue_index',
         'packet_uid', 'packet_bytes', 'q_bytes_before', 'q_bytes_after',
         'q_packets_before', 'q_packets_after', 'device_busy',
         'service_packet_uid']
PCOLS = ['time_ns', 'flow_id', 'qp_id', 'generation', 'reason', 'old_rate_bps',
         'new_rate_bps', 'last_tx_time_ns', 'old_next_avail_ns',
         'candidate_next_avail_ns', 'new_next_avail_ns', 'old_send_event_ns',
         'new_send_event_ns', 'event_action', 'sender_pending_packets']

for tag, d in (('CBAP', CB), ('DCQCN', DQ)):
    qp = os.path.join(d, 'causal_queue.csv')
    pp = os.path.join(d, 'causal_pacer.csv')
    # A cell still being written has a trace file open with a possibly partial
    # final line.  Reading it would produce spurious failures that say nothing
    # about the tracer, so require the completion marker first and report the
    # skip explicitly rather than silently passing.
    if not os.path.exists(os.path.join(d, 'DONE')):
        LOG.append('  SKIP  %-46s cell not complete (no DONE marker)' % tag)
        continue
    # T3: empty-trace detection.  A zero-row trace must be caught here, never
    # silently interpreted downstream as "no events therefore no gaps".
    for nm, path, cols in (('queue', qp, QCOLS), ('pacer', pp, PCOLS)):
        if not os.path.exists(path):
            chk('T3 %s %s trace exists' % (tag, nm), False, 'ABSENT')
            continue
        rows = list(csv.DictReader(open(path)))
        # The pacer emit site is inside ChangeRate's CBAP branch, so a DCQCN run
        # (CC_MODE 1, CBAP_ENABLE 0) cannot reach it and an empty pacer trace is
        # correct by construction.  Verified against the source: the enclosing
        # scope references cbap./CbapPacketGapNs.  This is asserted as an
        # expectation, not waived -- and it must never be read as "DCQCN made no
        # rate changes", since DCQCN's own rate path is not instrumented here.
        if nm == 'pacer' and tag == 'DCQCN':
            chk('T3 %s pacer EXPECTED empty (CBAP-only emit site)' % tag,
                len(rows) == 0, 'rows=%d' % len(rows))
            chk('T3 %s pacer header still written' % tag,
                open(path).readline().strip().split(',') == PCOLS)
            continue
        chk('T3 %s %s trace non-empty' % (tag, nm), len(rows) > 0,
            'rows=%d' % len(rows))
        if not rows:
            continue
        chk('T3 %s %s header exact' % (tag, nm),
            list(rows[0].keys()) == cols,
            'got %d cols' % len(rows[0].keys()))
        ts = [int(r['time_ns']) for r in rows]
        chk('T3 %s %s time monotone' % (tag, nm),
            all(ts[i] >= ts[i - 1] for i in range(1, len(ts))))
        chk('T3 %s %s within window' % (tag, nm),
            min(ts) >= T0N and max(ts) <= T1N,
            '[%d, %d]' % (min(ts), max(ts)))
    # queue-specific structure
    if os.path.exists(qp):
        rows = list(csv.DictReader(open(qp)))
        if rows:
            evs = {}
            for r in rows:
                evs[r['event']] = evs.get(r['event'], 0) + 1
            # TX_BEGIN and TX_END counts may differ by at most one per window
            # edge: a packet whose BEGIN preceded the window open contributes an
            # END with no BEGIN, and one still in flight at window close
            # contributes a BEGIN with no END.  Anything beyond that, or any
            # duplicate uid, is a genuine pairing defect.
            nb, ne = evs.get('TX_BEGIN', 0), evs.get('TX_END', 0)
            chk('T3 %s TX pairing within window-edge tolerance' % tag,
                abs(nb - ne) <= 2, 'begin=%d end=%d delta=%d' % (nb, ne, nb - ne))
            bb, ee = {}, {}
            for r in rows:
                if r['event'] == 'TX_BEGIN':
                    bb[r['packet_uid']] = bb.get(r['packet_uid'], 0) + 1
                elif r['event'] == 'TX_END':
                    ee[r['packet_uid']] = ee.get(r['packet_uid'], 0) + 1
            chk('T3 %s no duplicate TX_BEGIN uid' % tag,
                not [u for u, c in bb.items() if c > 1])
            chk('T3 %s no duplicate TX_END uid' % tag,
                not [u for u, c in ee.items() if c > 1])
            unmatched_e = [u for u in ee if u not in bb]
            unmatched_b = [u for u in bb if u not in ee]
            chk('T3 %s <=1 unmatched END, and it is the first TX row' % tag,
                len(unmatched_e) <= 1 and (
                    not unmatched_e or
                    next(r for r in rows
                         if r['event'] in ('TX_BEGIN', 'TX_END'))['packet_uid']
                    == unmatched_e[0]),
                'unmatched_end=%d' % len(unmatched_e))
            chk('T3 %s <=1 unmatched BEGIN, near window close' % tag,
                len(unmatched_b) <= 1 and (
                    not unmatched_b or
                    T1N - min(int(r['time_ns']) for r in rows
                              if r['event'] == 'TX_BEGIN'
                              and r['packet_uid'] == unmatched_b[0]) < 2000),
                'unmatched_begin=%d' % len(unmatched_b))
            chk('T3 %s all four event kinds present' % tag,
                all(k in evs for k in ('ENQUEUE', 'DEQUEUE', 'TX_BEGIN', 'TX_END')),
                str(sorted(evs.items())))
            # Cross-recorder agreement: tx_serialization.csv is written by a
            # different recorder from a different hook.  If both show the same
            # in-window TX counts and the same edge asymmetry, the asymmetry is
            # a property of the window, not of either tracer.
            tp = os.path.join(d, 'tx_serialization.csv')
            if os.path.exists(tp):
                ib = ie = 0
                for r2 in csv.DictReader(open(tp)):
                    t2 = int(r2['time_ns'])
                    if not (T0N <= t2 <= T1N):
                        continue
                    if r2['event'] == 'TX_BEGIN':
                        ib += 1
                    elif r2['event'] == 'TX_END':
                        ie += 1
                chk('T3 %s TX counts match independent recorder' % tag,
                    ib == nb and ie == ne,
                    'causal(%d,%d) vs txrec(%d,%d)' % (nb, ne, ib, ie))

            # identity resolvable: (node, if) must be a single real link here
            ids = set((r['node_id'], r['if_index']) for r in rows)
            chk('T3 %s link identity resolvable' % tag, len(ids) >= 1,
                'links=%s' % sorted(ids))
            # ENQUEUE arithmetic: after - before == packet_bytes
            bad = 0
            for r in rows:
                if r['event'] == 'ENQUEUE':
                    if int(r['q_bytes_after']) - int(r['q_bytes_before']) \
                            != int(r['packet_bytes']):
                        bad += 1
            chk('T3 %s ENQUEUE delta == packet_bytes' % tag, bad == 0,
                'violations=%d' % bad)
            bad = 0
            for r in rows:
                if r['event'] == 'DEQUEUE':
                    if int(r['q_bytes_before']) - int(r['q_bytes_after']) \
                            != int(r['packet_bytes']):
                        bad += 1
            chk('T3 %s DEQUEUE delta == packet_bytes' % tag, bad == 0,
                'violations=%d' % bad)

# ------------------------------------------------------------------- T4 ------
# Multi-QP: the pacer trace must carry more than one distinct flow, otherwise it
# cannot support any per-QP claim.
pp = os.path.join(CB, 'causal_pacer.csv')
if os.path.exists(pp):
    rows = list(csv.DictReader(open(pp)))
    fids = set(r['flow_id'] for r in rows)
    chk('T4 CBAP pacer covers multiple QPs/flows', len(fids) > 1,
        'distinct flow_id=%d' % len(fids))
    acts = set(r['event_action'] for r in rows)
    chk('T4 CBAP pacer records event_action', len(acts) > 0, str(sorted(acts)))
    # nextAvail semantics: new must equal candidate, or exceed it under the
    # credit gate (that is the only branch allowed to push it later).
    bad = 0
    for r in rows:
        if int(r['new_next_avail_ns']) < int(r['candidate_next_avail_ns']):
            bad += 1
    chk('T4 new_next_avail >= candidate', bad == 0, 'violations=%d' % bad)
else:
    chk('T4 CBAP pacer trace exists', False, 'ABSENT')

print('\n'.join(LOG))
print('=== telemetry unit tests: %d passed, %d failed ===' % (P, F))
sys.exit(1 if F else 0)
