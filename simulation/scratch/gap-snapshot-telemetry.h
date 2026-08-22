// Gap-boundary QP snapshot recorder.  DEFAULT OFF.  Read-only.
//
// Purpose (this round only): decide between four named hypotheses for CBAP's
// sender underfeed, using a CORRECTED phase measurement.  The previous round's
// phase reading was withdrawn because it inferred per-QP m_nextAvail from
// historical rows, which produced impossible values (leads of -2.0e9 ns).  Here
// every snapshot reads all 65 QPs AT THE SAME INSTANT, so no inference is
// involved.
//
// WHAT IT RECORDS: two snapshots per bottleneck gap -- one at gap start (the
// TX_END that leaves the port idle) and one at gap end (the next TX_BEGIN) --
// each containing one row per QP.  Nothing else.  No per-scheduling-attempt log.
//
// BUFFERING: rows accumulate in memory and are written once at Close().  At
// ~1065 gaps x 2 boundaries x 65 QPs the upper bound is ~138k rows; a hard cap
// stops accumulation rather than growing without bound.
//
// IDENTITY: node_id + qp_index only.  crfm.flowId is assigned late
// (rdma-hw.cc:5527) and reads 0 before assignment -- measured at 3.1 % of rows
// in the CBAP arm and 63 of 65 nodes in the DCQCN arm -- so it is recorded for
// reference but must never be used as the join key.
//
// BYPASS: no Simulator::Schedule / Cancel / Remove; only Simulator::Now().
// Nothing is written to any QP, device, queue or controller field.  With no
// output path configured, Open() returns false and no row is ever appended.
#ifndef GAP_SNAPSHOT_TELEMETRY_H
#define GAP_SNAPSHOT_TELEMETRY_H

#include <cstdio>
#include <string>
#include <vector>
#include <ns3/simulator.h>

namespace ns3 {

class GapSnapshotTrace {
public:
	struct Row {
		uint64_t gapId;
		uint64_t timeNs;
		uint32_t boundary;        // 0 = gap start, 1 = gap end
		uint32_t nodeId;
		uint32_t qpIndex;
		uint32_t flowIdRef;       // reference only; NOT an identity
		uint32_t active;
		uint32_t finished;
		uint32_t ownsRate;
		uint32_t inFloor;
		uint64_t bytesLeft;
		uint64_t packetPending;
		uint64_t commandedRateBps;
		uint64_t appliedRateBps;
		uint64_t nextAvailNs;
		uint64_t lastTxTimeNs;
		uint64_t lastCommandTimeNs;
		uint32_t generation;
		uint64_t oldRateBps;
		uint64_t newRateBps;
		uint64_t oldNextAvailNs;
		uint64_t newNextAvailNs;
	};

	static bool Open(const std::string &path, uint64_t winStartNs,
			uint64_t winEndNs, uint64_t maxRows)
	{
		if (path.empty())
			return false;
		s_path = path;
		s_lo = winStartNs;
		s_hi = winEndNs;
		s_max = maxRows ? maxRows : 400000;
		s_rows.clear();
		s_open = true;
		s_gapId = 0;
		s_dropped = 0;
		return true;
	}
	static bool IsOpen() { return s_open; }
	static bool InWindow()
	{
		if (!s_open)
			return false;
		const uint64_t now = Simulator::Now().GetTimeStep();
		return !(s_hi > 0 && (now < s_lo || now > s_hi));
	}
	static uint64_t NextGapId() { return ++s_gapId; }
	static uint64_t Rows() { return (uint64_t)s_rows.size(); }
	static uint64_t Dropped() { return s_dropped; }

	static void Append(const Row &r)
	{
		if (!s_open)
			return;
		if (s_rows.size() >= s_max) {
			s_dropped++;          // reported, never silently truncated
			return;
		}
		s_rows.push_back(r);
	}

	// Written once, at end of run.
	static void Close()
	{
		if (!s_open)
			return;
		FILE *f = fopen(s_path.c_str(), "w");
		if (f) {
			fprintf(f,
				"gap_id,time_ns,boundary,node_id,qp_index,flow_id_ref,"
				"active,finished,owns_rate,in_floor,"
				"bytes_left,packet_pending,commanded_rate_bps,"
				"applied_rate_bps,next_avail_ns,last_tx_time_ns,"
				"last_command_time_ns,generation,old_rate_bps,new_rate_bps,"
				"old_next_avail_ns,new_next_avail_ns\n");
			for (uint32_t i = 0; i < s_rows.size(); ++i) {
				const Row &r = s_rows[i];
				fprintf(f,
					"%lu,%lu,%u,%u,%u,%u,%u,%u,%u,%u,"
					"%lu,%lu,%lu,%lu,%lu,%lu,%lu,%u,%lu,%lu,%lu,%lu\n",
					(unsigned long)r.gapId, (unsigned long)r.timeNs,
					r.boundary, r.nodeId, r.qpIndex, r.flowIdRef,
					r.active, r.finished, r.ownsRate, r.inFloor,
					(unsigned long)r.bytesLeft,
					(unsigned long)r.packetPending,
					(unsigned long)r.commandedRateBps,
					(unsigned long)r.appliedRateBps,
					(unsigned long)r.nextAvailNs,
					(unsigned long)r.lastTxTimeNs,
					(unsigned long)r.lastCommandTimeNs,
					r.generation,
					(unsigned long)r.oldRateBps,
					(unsigned long)r.newRateBps,
					(unsigned long)r.oldNextAvailNs,
					(unsigned long)r.newNextAvailNs);
			}
			fclose(f);
		}
		printf("GAP_SNAPSHOT_ROWS %lu DROPPED %lu GAPS %lu\n",
			(unsigned long)s_rows.size(), (unsigned long)s_dropped,
			(unsigned long)s_gapId);
		fflush(stdout);
		s_open = false;
		s_rows.clear();
	}

private:
	static bool s_open;
	static std::string s_path;
	static std::vector<Row> s_rows;
	static uint64_t s_lo, s_hi, s_max, s_gapId, s_dropped;
};

} // namespace ns3

#endif // GAP_SNAPSHOT_TELEMETRY_H
