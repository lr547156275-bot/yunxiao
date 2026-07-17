#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <map>
#include <string>
#include <sys/stat.h>
#include <unordered_map>
#include "trace-format.h"
#include "sim-setting.h"

using namespace ns3;
using namespace std;

struct NodeStats {
	uint64_t total = 0;
	uint64_t event[4] = {0, 0, 0, 0};
	uint64_t udp = 0, ack = 0, nack = 0, pfc = 0, cnp = 0;
	uint64_t first_time = 0, last_time = 0;
	int node_type = -1;
	bool type_conflict = false;
};

struct PortStats {
	uint64_t total = 0;
	uint64_t event[4] = {0, 0, 0, 0};
	uint64_t udp = 0, ack = 0, pfc = 0, cnp = 0;
	uint32_t max_qlen = 0;
	uint64_t first_time = 0, last_time = 0;
	int node_type = -1;
	bool type_conflict = false;
};

static uint64_t file_size(const char* path) {
	struct stat st;
	if (stat(path, &st) != 0)
		return 0;
	return static_cast<uint64_t>(st.st_size);
}

static string protocol_name(uint8_t prot) {
	switch (prot) {
		case 0x06: return "TCP数据";
		case 0x11: return "UDP/RDMA数据";
		case 0xFC: return "ACK";
		case 0xFD: return "NACK";
		case 0xFE: return "PFC";
		case 0xFF: return "CNP";
		case 0x00: return "QP可用事件";
		default: return "其他协议";
	}
}

static string event_name(int event) {
	switch (event) {
		case Recv: return "Recv";
		case Enqu: return "Enqu";
		case Dequ: return "Dequ";
		case Drop: return "Drop";
		default: return "Unknown";
	}
}

static string ecn_name(int ecn) {
	switch (ecn) {
		case 0: return "0";
		case 1: return "1";
		case 2: return "2";
		case 3: return "3";
		default: return "非法值";
	}
}

static void print_ratio_line(const char* kind, int id, const string& name, uint64_t count, uint64_t total) {
	double pct = total == 0 ? 0.0 : static_cast<double>(count) * 100.0 / static_cast<double>(total);
	printf("%s\t%d\t%s\t%lu\t%.9f\n", kind, id, name.c_str(), count, pct);
}

int main(int argc, char** argv) {
	if (argc != 2) {
		fprintf(stderr, "Usage: %s <trace_file>\n", argv[0]);
		return 2;
	}

	const char* trace_path = argv[1];
	uint64_t fsize = file_size(trace_path);
	printf("META\ttrace_format_size\t%lu\n", static_cast<unsigned long>(sizeof(TraceFormat)));
	printf("META\tfile_size_bytes\t%lu\n", static_cast<unsigned long>(fsize));
	if (fsize == 0) {
		printf("ERROR\tempty_trace_file\t%s\n", trace_path);
		return 1;
	}

	FILE* file = fopen(trace_path, "rb");
	if (!file) {
		printf("ERROR\topen_trace_failed\t%s\n", trace_path);
		return 1;
	}

	SimSetting sim_setting;
	long header_start = ftell(file);
	sim_setting.Deserialize(file);
	long header_end = ftell(file);
	if (header_start < 0 || header_end < 0 || header_end <= header_start) {
		printf("ERROR\tsimsetting_deserialize_failed\tinvalid_header_offset\n");
		fclose(file);
		return 1;
	}

	uint64_t header_size = static_cast<uint64_t>(header_end - header_start);
	uint64_t sim_port_count = 0;
	for (auto const& node_entry : sim_setting.port_speed)
		sim_port_count += node_entry.second.size();

	printf("META\theader_size_bytes\t%lu\n", static_cast<unsigned long>(header_size));
	printf("META\tsimsetting_port_count\t%lu\n", static_cast<unsigned long>(sim_port_count));
	printf("META\tsimsetting_win\t%u\n", sim_setting.win);

	uint64_t record_region = fsize >= header_size ? fsize - header_size : 0;
	uint64_t tail_bytes = record_region % sizeof(TraceFormat);
	uint64_t expected_records = record_region / sizeof(TraceFormat);
	printf("META\trecord_region_bytes\t%lu\n", static_cast<unsigned long>(record_region));
	printf("META\trecord_region_complete\t%s\n", tail_bytes == 0 ? "1" : "0");
	printf("META\ttail_bytes\t%lu\n", static_cast<unsigned long>(tail_bytes));
	printf("META\texpected_record_count\t%lu\n", static_cast<unsigned long>(expected_records));

	for (auto const& node_entry : sim_setting.port_speed) {
		for (auto const& port_entry : node_entry.second) {
			printf("SIM_PORT\t%u\t%u\t%lu\t%u\n", node_entry.first, port_entry.first, static_cast<unsigned long>(port_entry.second), sim_setting.win);
		}
	}

	uint64_t event_counts[4] = {0, 0, 0, 0};
	uint64_t unknown_event_count = 0;
	uint64_t protocol_counts[256];
	uint64_t ecn_counts[256];
	memset(protocol_counts, 0, sizeof(protocol_counts));
	memset(ecn_counts, 0, sizeof(ecn_counts));
	map<uint16_t, NodeStats> node_stats;
	map<pair<uint16_t, uint8_t>, PortStats> port_stats;
	uint64_t record_count = 0;
	uint64_t reverse_time_count = 0;
	uint64_t invalid_node_type_count = 0;
	uint64_t first_time = 0, last_time = 0, previous_time = 0;
	bool have_record = false;

	TraceFormat tr;
	while (tr.Deserialize(file) > 0) {
		record_count++;
		if (record_count % 10000000lu == 0)
			fprintf(stderr, "trace_probe progress: %lu records\n", static_cast<unsigned long>(record_count));

		if (!have_record) {
			first_time = tr.time;
			have_record = true;
		} else if (tr.time < previous_time) {
			reverse_time_count++;
		}
		previous_time = tr.time;
		last_time = tr.time;

		if (tr.event <= Drop)
			event_counts[tr.event]++;
		else
			unknown_event_count++;
		if (tr.nodeType > 1)
			invalid_node_type_count++;
		protocol_counts[tr.l3Prot]++;
		ecn_counts[tr.ecn]++;

		NodeStats& ns = node_stats[tr.node];
		if (ns.total == 0) {
			ns.first_time = tr.time;
			ns.node_type = tr.nodeType;
		}
		ns.total++;
		ns.last_time = tr.time;
		if (ns.node_type != static_cast<int>(tr.nodeType))
			ns.type_conflict = true;
		if (tr.event <= Drop)
			ns.event[tr.event]++;
		if (tr.l3Prot == 0x11) ns.udp++;
		else if (tr.l3Prot == 0xFC) ns.ack++;
		else if (tr.l3Prot == 0xFD) ns.nack++;
		else if (tr.l3Prot == 0xFE) ns.pfc++;
		else if (tr.l3Prot == 0xFF) ns.cnp++;

		PortStats& ps = port_stats[make_pair(tr.node, tr.intf)];
		if (ps.total == 0) {
			ps.first_time = tr.time;
			ps.node_type = tr.nodeType;
		}
		ps.total++;
		ps.last_time = tr.time;
		if (ps.node_type != static_cast<int>(tr.nodeType))
			ps.type_conflict = true;
		if (tr.event <= Drop)
			ps.event[tr.event]++;
		if (tr.l3Prot == 0x11) ps.udp++;
		else if (tr.l3Prot == 0xFC) ps.ack++;
		else if (tr.l3Prot == 0xFE) ps.pfc++;
		else if (tr.l3Prot == 0xFF) ps.cnp++;
		if (tr.qlen > ps.max_qlen)
			ps.max_qlen = tr.qlen;
	}

	printf("META\trecord_count\t%lu\n", static_cast<unsigned long>(record_count));
	printf("META\tfirst_time_ns\t%lu\n", static_cast<unsigned long>(first_time));
	printf("META\tlast_time_ns\t%lu\n", static_cast<unsigned long>(last_time));
	printf("META\ttime_reverse_count\t%lu\n", static_cast<unsigned long>(reverse_time_count));
	printf("META\tinvalid_event_count\t%lu\n", static_cast<unsigned long>(unknown_event_count));
	printf("META\tinvalid_node_type_count\t%lu\n", static_cast<unsigned long>(invalid_node_type_count));

	for (int i = 0; i <= 3; i++)
		print_ratio_line("EVENT", i, event_name(i), event_counts[i], record_count);
	print_ratio_line("EVENT", -1, "Unknown", unknown_event_count, record_count);

	const int known_protocols[] = {0x06, 0x11, 0xFC, 0xFD, 0xFE, 0xFF, 0x00};
	bool known[256];
	memset(known, 0, sizeof(known));
	for (size_t i = 0; i < sizeof(known_protocols) / sizeof(known_protocols[0]); i++) {
		int prot = known_protocols[i];
		known[prot] = true;
		print_ratio_line("PROTOCOL", prot, protocol_name(static_cast<uint8_t>(prot)), protocol_counts[prot], record_count);
	}
	uint64_t other_protocol_count = 0;
	for (int i = 0; i < 256; i++)
		if (!known[i])
			other_protocol_count += protocol_counts[i];
	print_ratio_line("PROTOCOL", -1, "其他协议", other_protocol_count, record_count);
	printf("META\tinvalid_protocol_count\t%lu\n", static_cast<unsigned long>(other_protocol_count));

	for (int i = 0; i <= 3; i++)
		print_ratio_line("ECN", i, ecn_name(i), ecn_counts[i], record_count);
	uint64_t invalid_ecn_count = 0;
	for (int i = 4; i < 256; i++)
		invalid_ecn_count += ecn_counts[i];
	print_ratio_line("ECN", -1, "非法值", invalid_ecn_count, record_count);
	printf("META\tinvalid_ecn_count\t%lu\n", static_cast<unsigned long>(invalid_ecn_count));

	for (auto const& item : node_stats) {
		NodeStats const& s = item.second;
		printf("NODE\t%u\t%d\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\n",
			item.first, s.node_type,
			static_cast<unsigned long>(s.total),
			static_cast<unsigned long>(s.event[Recv]),
			static_cast<unsigned long>(s.event[Enqu]),
			static_cast<unsigned long>(s.event[Dequ]),
			static_cast<unsigned long>(s.event[Drop]),
			static_cast<unsigned long>(s.udp),
			static_cast<unsigned long>(s.ack),
			static_cast<unsigned long>(s.nack),
			static_cast<unsigned long>(s.pfc),
			static_cast<unsigned long>(s.cnp),
			static_cast<unsigned long>(s.first_time),
			static_cast<unsigned long>(s.last_time));
		if (s.type_conflict)
			printf("WARNING\tnode_type_conflict\t%u\n", item.first);
	}

	for (auto const& item : port_stats) {
		PortStats const& s = item.second;
		printf("PORT\t%u\t%u\t%d\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\t%lu\n",
			item.first.first, item.first.second, s.node_type,
			static_cast<unsigned long>(s.total),
			static_cast<unsigned long>(s.event[Recv]),
			static_cast<unsigned long>(s.event[Enqu]),
			static_cast<unsigned long>(s.event[Dequ]),
			static_cast<unsigned long>(s.event[Drop]),
			static_cast<unsigned long>(s.udp),
			static_cast<unsigned long>(s.ack),
			static_cast<unsigned long>(s.pfc),
			static_cast<unsigned long>(s.cnp),
			static_cast<unsigned long>(s.max_qlen),
			static_cast<unsigned long>(s.first_time),
			static_cast<unsigned long>(s.last_time));
		if (s.type_conflict)
			printf("WARNING\tport_node_type_conflict\t%u:%u\n", item.first.first, item.first.second);
	}

	fclose(file);

	bool failed = false;
	if (tail_bytes != 0) {
		printf("ERROR\ttail_incomplete_bytes\t%lu\n", static_cast<unsigned long>(tail_bytes));
		failed = true;
	}
	if (record_count == 0) {
		printf("ERROR\tno_trace_records\t0\n");
		failed = true;
	}
	if (unknown_event_count > 0) {
		printf("ERROR\tinvalid_event_count\t%lu\n", static_cast<unsigned long>(unknown_event_count));
		failed = true;
	}
	if (reverse_time_count > 0) {
		printf("ERROR\ttime_reverse_count\t%lu\n", static_cast<unsigned long>(reverse_time_count));
		failed = true;
	}
	if (invalid_node_type_count > 0) {
		printf("ERROR\tinvalid_node_type_count\t%lu\n", static_cast<unsigned long>(invalid_node_type_count));
		failed = true;
	}
	return failed ? 1 : 0;
}
