/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

#undef PGO_TRAINING
#define PATH_TO_PGO_CONFIG "path_to_pgo_config"

#include <iostream>
#include <fstream>
#include <cstdlib>
#include <set>
#include <cmath>
#include <limits>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <unordered_map>
#include <time.h> 
#include "ns3/core-module.h"
#include "ns3/qbb-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/global-route-manager.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/packet.h"
#include "ns3/flow-id-tag.h"
#include "ns3/error-model.h"
#include <ns3/rdma.h>
#include <ns3/rdma-client.h>
#include <ns3/rdma-client-helper.h>
#include <ns3/rdma-driver.h>
#include <ns3/switch-node.h>
#include <ns3/sim-setting.h>
#include "bop-final-validation.h"

using namespace ns3;
using namespace std;

NS_LOG_COMPONENT_DEFINE("GENERIC_SIMULATION");

uint32_t cc_mode = 1;//拥塞控制模式
uint32_t sim_seed = 1;
bool enable_qcn = true, use_dynamic_pfc_threshold = true;//启用QCN，使用动态PFC阈值
bool pfc_runtime_enable = true;
uint32_t packet_payload_size = 1000, l2_chunk_size = 0, l2_ack_interval = 0;//数据包载荷大小；「L2 分块」大小，收到NACK时按chunk回退重传；0 表示关闭chunk模式；发ack的时间间隔
double pause_time = 5, simulator_stop_time = 3.01;//暂停时间，模拟器停止时间
std::string data_rate, link_delay, topology_file, flow_file, trace_file, trace_output_file;
std::string fct_output_file = "fct.txt";
std::string pfc_output_file = "pfc.txt";
std::string fixed_path_file, fixed_path_output_file, port_monitor_output_file;
uint64_t port_monitor_interval = 10000;
string round_schedule_file;
bool round_mode = false;
uint64_t crfm_trace_sample_us = 10;
uint32_t crfm_max_trace_file_mb = 64, crfm_max_trace_total_mb = 128;
uint32_t crfm_min_free_gb = 5, crfm_max_event_rows = 100000;
bool crfm_debug = false;
double bop_rho = 1.0;
uint64_t bop_background_bps = 0, bop_bottleneck_bps = 0;
bool bop_phase_stagger = true;
uint32_t bop_packet_bytes = 1024;
bool bop_multilink_enable = false;
string bop_multilink_link_file, bop_multilink_path_file;
string bop_multilink_group_file;
string bop_multilink_group_decisions_file;
string bop_multilink_link_constraints_file;
double bop_qc_bdp_factor = 1.0, bop_qc_default_tau_us = 10.0;
double bop_qc_tau_ewma_alpha = 0.20;
uint32_t bop_qc_queue_limit_mode = 1, bop_qc_packet_margin = 1;
bool bop_qc_enable_phase_stagger = true;
double bop_qb_queue_fraction = 0.50;
uint32_t bop_qb_packet_margin = 1;
bool bop_qb_enable_phase_stagger = true;
uint32_t bop_qb_max_packet_margin = 1;
bool bop_qb_max_enable_phase_stagger = true;
string flow_summary_file, round_summary_file, feedback_summary_file;
string link_timeseries_file, selected_flow_timeseries_file;
string controller_summary_file, group_round_summary_file, flow_plan_file;
string bop_qc_group_decisions_file;
string bop_qb_group_decisions_file;
string bop_qb_max_group_decisions_file;
string prt_probe_summary_file, prt_group_decisions_file;
string round_selected_flow_ids, round_selected_link_ids;
string algorithm_name = "unknown", scenario_name = "unknown";
bool short_diag_enable = false;
uint32_t short_diag_bottleneck_node = 0, short_diag_bottleneck_if = 0;
uint32_t short_diag_max_event_mb = 16;
string short_diag_pipeline_file, short_diag_idle_file;
string short_diag_qp_tail_file, short_diag_meta_file;
string short_diag_events_file;
string short_diag_topology_sha256, short_diag_flow_sha256;
string short_diag_round_sha256;
bool final_validation_enable = false;
uint32_t final_bottleneck_node = 0, final_bottleneck_if = 0;
uint32_t final_collective_flow_count = 0;
uint32_t final_primer_first_flow = std::numeric_limits<uint32_t>::max();
string final_wire_size_file, final_release_queue_file;
bool prerelease_audit_enable = false;
uint32_t prerelease_audit_bottleneck_node = 0;
uint32_t prerelease_audit_bottleneck_if = 0;
uint32_t prerelease_audit_collective_flow_count = 0;
uint32_t prerelease_audit_primer_first_flow = 0;
uint32_t prerelease_audit_max_event_mb = 32;
string prerelease_audit_timeline_file, prerelease_audit_residual_file;
string prerelease_audit_queue_file, prerelease_audit_ecn_file;
string prerelease_audit_meta_file;
string prerelease_audit_topology_sha256, prerelease_audit_flow_sha256;
string prerelease_audit_round_sha256;
bool pfc_semantic_audit_enable = false;
uint32_t pfc_audit_node = 0, pfc_audit_if = 0, pfc_audit_priority = 3;
string pfc_event_trace_file, pfc_semantic_summary_file;
bool cbap_enable = false;
string cbap_link_file, cbap_path_file;
uint64_t cbap_control_epoch_us = 5, cbap_planning_delay_us = 5;
uint64_t cbap_control_delay_us = 5;
double cbap_rho = 0.95, cbap_epsilon_rate = 0.02;
uint32_t cbap_priority = 3, cbap_max_wire_packet_bytes = 1064;
uint32_t cbap_summary_bytes = 64, cbap_grant_bytes = 48;
string cbap_port_summary_file, cbap_admission_file;
string cbap_rate_transition_file, cbap_flow_state_file;
string cbap_increase_audit_file;
string cbap_applied_rate_audit_file;
string cbap_control_overhead_file;
string cbap_packet_trace_file;
uint32_t cbap_packet_trace_max_mb = 96;
string cbap_tx_event_file;
string cbap_scope_summary_file, cbap_scope_link_file;
string cbap_handoff_summary_file, cbap_handoff_flow_file;
string cbap_controller_ownership_file, cbap_control_message_file;
string cbap_envelope_link_file, cbap_envelope_flow_file;
string cbap_incumbent_progress_file;
string cbap_v20_batch_file, cbap_v20_flow_file;
string cbap_sba_event_file;
// UNCALIBRATED (doc 3.3): fixed placeholder deadline, not derived from a
// measured DCQCN/HPCC feedback blind-window distribution.
uint64_t cbap_sba_lease_us = 1000;
// Scheme-1 batch-to-batch reclaim redesign: dynamic per-link budget
// and batch-level target weights (see cbap-sba design notes).
double cbap_budget_q_low_fraction = 0.5;
double cbap_budget_q_high_fraction = 1.0;
double cbap_max_drain_ratio = 0.20;
double cbap_old_batch_weight = 1.0;
double cbap_new_batch_weight = 1.0;
// Capacity migration (docs/cbap_sba_capacity_migration_design.md).
bool cbap_migration_enable = false;
double cbap_migration_release_ratio = 0.5;
double cbap_migration_decay_base = 0.30;
double cbap_migration_rise_base = 0.30;
double cbap_migration_rise_skew = 0.35;
uint32_t cbap_migration_max_rtt = 5;
double cbap_queue_target_fraction = 0.25;
uint32_t cbap_tx_trace_tracking_packets = 4096;
uint32_t cbap_increase_policy = RdmaHw::CBAP_INCREASE_LEGACY_V1;
double cbap_increase_fraction = 0.10;
uint64_t cbap_increase_absolute_bps = UINT64_C(2000000000);
string cbap_version = "v1";
uint32_t cbap_scope_policy = RdmaHw::CBAP_SCOPE_ALWAYS;
uint32_t cbap_scope_base_cc = 1;
uint32_t cbap_rate_floor_policy =
	RdmaHw::CBAP_RATE_FLOOR_ONE_PACKET_PER_EPOCH_LEGACY;
bool cbap_ratefloor_semantic_zero_test = false;
uint32_t cbap_ratefloor_semantic_zero_flow = 0;
uint32_t cbap_ratefloor_semantic_zero_start_epoch = 0;
uint32_t cbap_ratefloor_semantic_zero_end_epoch = 0;
bool cbap_handoff_enable = false;
uint32_t cbap_handoff_stable_epochs = 2;
uint32_t cbap_handoff_base_cc = 1;
bool cbap_handoff_diagnostic_force_root = false;
uint32_t cbap_handoff_diagnostic_recovery_until_epoch = 0;
uint32_t cbap_delegation_diagnostic_force_stale_epochs = 0;

double alpha_resume_interval = 55, rp_timer, ewma_gain = 1 / 16;//恢复间隔；在reaction阶段的时候多久做一次AI；EWMA增益
double rate_decrease_interval = 4;//速率降低间隔，也就是在降速的时候多久降速一次
uint32_t fast_recovery_times = 5;//快速恢复次数，也就是收到CNP后快速恢复阶段做几次加速
std::string rate_ai, rate_hai, min_rate = "100Mb/s";//速率AI，速率HAI，最小速率
std::string dctcp_rate_ai = "1000Mb/s";//DCTCP速率AI

bool clamp_target_rate = false, l2_back_to_zero = false;//连续降速时，是否锁定目标速率；DCQCN的ACK重传策略：go-back-0
double error_rate_per_link = 0.0;//每条链路的错误率
uint32_t has_win = 1;//是否有设置BDP窗口
uint32_t global_t = 1;//是否全局都用RTT_Max还是每条流自己的RTT
uint32_t mi_thresh = 5;//连续AI几次后进MI（乘性增速）
bool var_win = false, fast_react = true;//窗口是否随当前速率缩放；是否每一个ACK都快速反应，即DCQCN是否每一个ACK都提速，如果是否的话就是使用定时器/发送字节数批量提速
bool multi_rate = true;//多速率，也就是每一跳是否单独速率还是说聚合跳数的速率
bool sample_feedback = false;//采样反馈，也就是INT反馈是每个包都反馈还是采样
double pint_log_base = 1.05;//PINT对数量化底数
double pint_prob = 1.0;//PINT概率
double u_target = 0.95;//目标利用率
uint32_t int_multi = 1;//INT头里的qLen的量化倍数
bool rate_bound = true;//速率限制/即是否按照CC算出来的速率来限制nic发包速率

uint32_t ack_high_prio = 0;//设置ack为高优先级
uint64_t link_down_time = 0;//链路断开时间
uint32_t link_down_A = 0, link_down_B = 0;

uint32_t enable_trace = 1;//启用跟踪

uint32_t buffer_size = 16;//缓冲区大小

uint32_t qlen_dump_interval = 100000, qlen_mon_interval = 100;//队列长度dump间隔，队列长度监控间隔
uint64_t qlen_mon_start = 2000000000, qlen_mon_end = 2100000000;//队列长度监控开始时间，队列长度监控结束时间
string qlen_mon_file;

unordered_map<uint64_t, uint32_t> rate2kmax, rate2kmin;//这里设置的ECN是RED-ECN，也就是说这两个值是RED-ECN的阈值，当队列长度超过kmax时，触发ECN，当队列长度低于kmin时，不触发ECN
unordered_map<uint64_t, double> rate2pmax;//这个就是标记概率的最大值

/************************************************
 * Runtime varibles
 ***********************************************/
std::ifstream topof, flowf, tracef;

NodeContainer n;

uint64_t nic_rate;//网卡发送速率

uint64_t maxRtt, maxBdp;//最大RTT，最大BDP

struct Interface{//接口结构体
	uint32_t idx;//出接口编号
	bool up;//表示接口是否被拉起来了
	uint64_t delay;//延迟
	uint64_t bw;//带宽

	Interface() : idx(0), up(false){}//默认接口为0，默认接口下线状态为false
};

map<Ptr<Node>, map<Ptr<Node>, Interface> > nbr2if;//将node到邻居节点映射到interface即端口上
// Mapping destination to next hop for each node: <node, <dest, <nexthop0, ...> > >
map<Ptr<Node>, map<Ptr<Node>, vector<Ptr<Node> > > > nextHop;//映射表的吓一跳
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairDelay;//映射表的delay等等的属性，如果是路由阶段的话，pairdelay这些被取出放入新建表中开始累加
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairTxDelay;
map<uint32_t, map<uint32_t, uint64_t> > pairBw;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairBdp;
map<uint32_t, map<uint32_t, uint64_t> > pairRtt;

std::vector<Ipv4Address> serverAddress;

// maintain port number for each host pair
std::unordered_map<uint32_t, unordered_map<uint32_t, uint16_t> > portNumder;

struct FlowInput{
	uint32_t src, dst, pg, maxPacketCount, port, dport;
	double start_time;
	uint32_t idx;
};//建立流
FlowInput flow_input = {0};//初始化
uint32_t flow_num;

struct ExperimentFlow {
	uint32_t id, src, dst, pg;
	uint16_t sport, dport;
	uint64_t size;
	double start;
	double finish;
	Ptr<RdmaQueuePair> qp;
	bool completed;
	ExperimentFlow(): finish(0), qp(0), completed(false) {}
};
vector<ExperimentFlow> experiment_flows;
map<uint32_t, vector<RdmaQueuePair::CrfmRoundState> > round_schedules;
map<uint32_t, int64_t> multilink_group_predecessors;
map<uint32_t, uint64_t> multilink_group_gaps;
map<uint32_t, uint64_t> multilink_group_initial_releases;
FILE *flow_summary_csv = NULL, *round_summary_csv = NULL;
FILE *feedback_summary_csv = NULL, *controller_summary_csv = NULL;
FILE *group_round_summary_csv = NULL, *flow_plan_csv = NULL;
FILE *bop_qc_group_decisions_csv = NULL;
FILE *bop_qb_group_decisions_csv = NULL;
FILE *bop_qb_max_group_decisions_csv = NULL;
FILE *bop_multilink_group_decisions_csv = NULL;
FILE *bop_multilink_link_constraints_csv = NULL;
FILE *prt_probe_summary_csv = NULL;
FILE *prt_group_decisions_csv = NULL;
FILE *link_csv = NULL, *selected_csv = NULL, *pfc_csv = NULL;
FILE *pfc_semantic_csv = NULL;
FILE *cbap_packet_trace_csv = NULL;
uint64_t cbap_packet_trace_rows = 0;
bool cbap_packet_trace_truncated = false;
uint64_t trace_total_bytes = 0;
bool trace_truncated = false;
uint64_t pfc_event_rows = 0, pfc_total_events = 0, pfc_last_sample_events = 0;
map<uint64_t,uint32_t> pfc_states;
map<pair<uint32_t,uint32_t>,uint64_t> trace_last_tx, trace_last_ecn;
set<uint32_t> selected_flow_set;
set<pair<uint32_t,uint32_t> > selected_link_set;
vector<RdmaHw::BopMultilinkLink> cbap_links;
map<uint32_t, vector<uint32_t> > cbap_flow_paths;
map<uint32_t, RdmaHw::BopMultilinkLink> cbap_link_by_id;

void ConfigError(const string &message);
bool DetailedCsvWrite(FILE *f, uint64_t per_file_limit,
	const string &line);

struct PfcSemanticState {
	uint64_t queueMaxBytes;
	uint64_t pauseGenerated;
	uint64_t pauseReceived;
	uint64_t senderPaused;
	uint64_t resumeGenerated;
	uint64_t resumeReceived;
	uint64_t senderResumed;
	uint64_t pauseDurationNs;
	uint64_t lastThresholdBytes;
	map<uint64_t, uint64_t> pauseStartNs;
	PfcSemanticState(): queueMaxBytes(0), pauseGenerated(0),
		pauseReceived(0), senderPaused(0), resumeGenerated(0),
		resumeReceived(0), senderResumed(0), pauseDurationNs(0),
		lastThresholdBytes(0) {}
} pfc_semantic_state;

const char *PfcSemanticEventName(uint32_t event){
	static const char *names[] = {
		"pause_generated", "pause_received", "sender_paused",
		"resume_generated", "resume_received", "sender_resumed"
	};
	return event < 6 ? names[event] : "unknown";
}

void WritePfcSemanticEvent(uint32_t nodeId, uint32_t deviceId,
		uint32_t portId, uint32_t priority, uint64_t queueBytes,
		uint64_t thresholdBytes, uint32_t event, uint32_t pauseQuanta,
		uint64_t pauseDurationNs, bool senderPaused){
	if (!pfc_semantic_csv)
		return;
	if (pfc_event_rows >= crfm_max_event_rows){
		if (!trace_truncated){
			trace_truncated = true;
			cerr << "LOG_TRUNCATED" << endl;
		}
		return;
	}
	stringstream row;
	row << Simulator::Now().GetNanoSeconds() << "," << nodeId << ","
		<< deviceId << "," << portId << "," << priority << ","
		<< queueBytes << "," << thresholdBytes << ","
		<< PfcSemanticEventName(event) << "," << pauseQuanta << ","
		<< pauseDurationNs << "," << (senderPaused ? 1 : 0)
		<< ",pfc_control\n";
	if (DetailedCsvWrite(pfc_semantic_csv,
			(uint64_t)crfm_max_trace_file_mb * 1024 * 1024, row.str()))
		pfc_event_rows++;
}

void SwitchPfcSemantic(Ptr<SwitchNode> sw, uint32_t port,
		uint32_t priority, uint32_t queueBytes, uint32_t thresholdBytes,
		uint32_t event){
	pfc_semantic_state.queueMaxBytes =
		max(pfc_semantic_state.queueMaxBytes, (uint64_t)queueBytes);
	pfc_semantic_state.lastThresholdBytes = thresholdBytes;
	if (event == 0)
		pfc_semantic_state.pauseGenerated++;
	else if (event == 3)
		pfc_semantic_state.resumeGenerated++;
	WritePfcSemanticEvent(sw->GetId(), port, port, priority, queueBytes,
		thresholdBytes, event, event == 0 ? (uint32_t)pause_time : 0,
		0, false);
}

void DevicePfcSemantic(Ptr<QbbNetDevice> dev, uint32_t priority,
		uint32_t event, uint32_t queueBytes, uint32_t pauseQuanta){
	uint64_t key = ((uint64_t)dev->GetNode()->GetId() << 32) |
		((uint64_t)dev->GetIfIndex() << 16) | priority;
	uint64_t duration = 0;
	if (event == 1)
		pfc_semantic_state.pauseReceived++;
	else if (event == 2){
		pfc_semantic_state.senderPaused++;
		pfc_semantic_state.pauseStartNs[key] =
			Simulator::Now().GetNanoSeconds();
	}else if (event == 4)
		pfc_semantic_state.resumeReceived++;
	else if (event == 5){
		pfc_semantic_state.senderResumed++;
		map<uint64_t,uint64_t>::iterator start =
			pfc_semantic_state.pauseStartNs.find(key);
		if (start != pfc_semantic_state.pauseStartNs.end()){
			duration = Simulator::Now().GetNanoSeconds() - start->second;
			pfc_semantic_state.pauseDurationNs += duration;
			pfc_semantic_state.pauseStartNs.erase(start);
		}
	}
	WritePfcSemanticEvent(dev->GetNode()->GetId(), dev->GetIfIndex(),
		dev->GetIfIndex(), priority, queueBytes,
		pfc_semantic_state.lastThresholdBytes, event, pauseQuanta,
		duration, event == 2 || (event != 5 && dev->IsPaused(priority)));
}

void PfcAuditQueueEvent(Ptr<QbbNetDevice> dev, Ptr<const Packet>,
		uint32_t){
	pfc_semantic_state.queueMaxBytes = max(
		pfc_semantic_state.queueMaxBytes,
		(uint64_t)dev->GetQueue()->GetNBytesTotal());
}

void WritePfcSemanticSummary(){
	if (!pfc_semantic_audit_enable)
		return;
	ofstream output(pfc_semantic_summary_file.c_str());
	if (!output.is_open())
		ConfigError("cannot open PFC_SEMANTIC_SUMMARY_FILE");
	Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(pfc_audit_node));
	NS_ASSERT_MSG(sw && pfc_audit_if < sw->GetNDevices(),
		"PFC semantic audit bottleneck is invalid");
	Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(
		sw->GetDevice(pfc_audit_if));
	NS_ASSERT_MSG(dev, "PFC semantic audit device is not QbbNetDevice");
	stringstream queueObject, pfcObject;
	queueObject << "BEgressQueue@" << PeekPointer(dev->GetQueue());
	pfcObject << "SwitchMmu@" << PeekPointer(sw->m_mmu);
	uint64_t threshold = sw->m_mmu->GetPfcThreshold(pfc_audit_if);
	bool verified = pfc_semantic_state.pauseGenerated > 0 &&
		pfc_semantic_state.pauseReceived > 0 &&
		pfc_semantic_state.senderPaused > 0 &&
		pfc_semantic_state.resumeGenerated > 0 &&
		pfc_semantic_state.resumeReceived > 0 &&
		pfc_semantic_state.senderResumed > 0;
	output << "{\n"
		<< "  \"queue_object_id\": \"" << queueObject.str() << "\",\n"
		<< "  \"pfc_queue_object_id\": \"" << pfcObject.str() << "\",\n"
		<< "  \"queue_priority\": " << pfc_audit_priority << ",\n"
		<< "  \"pfc_priority\": " << pfc_audit_priority << ",\n"
		<< "  \"pfc_threshold_bytes\": " << threshold << ",\n"
		<< "  \"queue_max_bytes\": " << pfc_semantic_state.queueMaxBytes << ",\n"
		<< "  \"pause_generated_count\": " << pfc_semantic_state.pauseGenerated << ",\n"
		<< "  \"pause_received_count\": " << pfc_semantic_state.pauseReceived << ",\n"
		<< "  \"sender_paused_count\": " << pfc_semantic_state.senderPaused << ",\n"
		<< "  \"resume_generated_count\": " << pfc_semantic_state.resumeGenerated << ",\n"
		<< "  \"resume_received_count\": " << pfc_semantic_state.resumeReceived << ",\n"
		<< "  \"sender_resumed_count\": " << pfc_semantic_state.senderResumed << ",\n"
		<< "  \"pause_duration_us\": " << fixed << setprecision(6)
		<< (pfc_semantic_state.pauseDurationNs / 1000.0) << ",\n"
		<< "  \"pfc_runtime_enabled\": "
		<< (pfc_runtime_enable ? "true" : "false") << ",\n"
		<< "  \"queue_and_pfc_objects_identical\": false,\n"
		<< "  \"pfc_path_verified\": " << (verified ? "true" : "false")
		<< "\n}\n";
}

uint64_t ReadFinalValidationQueue(){
	if (!final_validation_enable)
		return 0;
	Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(
		n.Get(final_bottleneck_node));
	NS_ASSERT_MSG(sw && final_bottleneck_if < sw->GetNDevices(),
			"final-validation bottleneck is invalid");
	Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(
		sw->GetDevice(final_bottleneck_if));
	NS_ASSERT_MSG(dev, "final-validation bottleneck is not QbbNetDevice");
	uint64_t queue = dev->GetQueue()->GetNBytesTotal();
	return queue;
}

const char *BopQ0OriginName(uint32_t value){
	switch (value){
	case RdmaHw::BOP_Q0_ORIGIN_INT: return "pre_release_int";
	case RdmaHw::BOP_Q0_ORIGIN_ORACLE_RELEASE:
		return "oracle_release_queue";
	default: return "no_valid_pre_release_queue";
	}
}

bool DetailedCsvWrite(FILE *f, uint64_t per_file_limit, const string &line){
	if (!f || trace_truncated) return false;
	long pos = ftell(f);
	if (pos < 0 || (uint64_t)pos + line.size() > per_file_limit ||
		trace_total_bytes + line.size() >
			(uint64_t)crfm_max_trace_total_mb*1024*1024){
		trace_truncated = true;
		cerr << "LOG_TRUNCATED" << endl;
		return false;
	}
	fwrite(line.data(), 1, line.size(), f);
	trace_total_bytes += line.size();
	return true;
}

void ParseIdSets(){
	string token;
	stringstream fs(round_selected_flow_ids);
	while (getline(fs, token, ',')) if (!token.empty()) selected_flow_set.insert(atoi(token.c_str()));
	stringstream ls(round_selected_link_ids);
	while (getline(ls, token, ',')){
		size_t p=token.find(':');
		if (p!=string::npos) selected_link_set.insert(make_pair(atoi(token.substr(0,p).c_str()),atoi(token.substr(p+1).c_str())));
	}
}

void ReadBopMultilinkInputs(){
	if (!bop_multilink_enable){
		RdmaHw::ConfigureBopMultilink(false,
			vector<RdmaHw::BopMultilinkLink>(),
			map<uint32_t, vector<uint32_t> >(),
			map<uint32_t, int64_t>());
		return;
	}
	if (bop_multilink_link_file.empty() ||
			bop_multilink_path_file.empty() ||
			bop_multilink_group_file.empty())
		ConfigError("BOP multilink mode requires link, path, and group files");
	ifstream links(bop_multilink_link_file.c_str());
	ifstream paths(bop_multilink_path_file.c_str());
	ifstream groups(bop_multilink_group_file.c_str());
	if (!links.is_open() || !paths.is_open() || !groups.is_open())
		ConfigError("cannot open one or more BOP multilink input files");

	uint32_t linkCount = 0;
	links >> linkCount;
	vector<RdmaHw::BopMultilinkLink> definitions;
	for (uint32_t i = 0; i < linkCount; ++i){
		RdmaHw::BopMultilinkLink link;
		uint32_t telemetryEligible = 0;
		links >> link.linkId >> link.nodeId >> link.ifIndex >>
			link.capacityBps >> link.ecnThresholdBytes >>
			link.backgroundBps >> telemetryEligible;
		if (!links || link.capacityBps <= link.backgroundBps ||
				link.ecnThresholdBytes == 0 || telemetryEligible > 1)
			ConfigError("malformed BOP multilink link row");
		link.telemetryEligible = telemetryEligible != 0;
		definitions.push_back(link);
		if (link.telemetryEligible)
			selected_link_set.insert(make_pair(link.nodeId, link.ifIndex));
	}
	string extra;
	if (links >> extra)
		ConfigError("extra content in BOP multilink link file");

	uint32_t pathCount = 0;
	paths >> pathCount;
	if (pathCount != flow_num)
		ConfigError("BOP multilink path count differs from flow count");
	map<uint32_t, vector<uint32_t> > flowPaths;
	for (uint32_t i = 0; i < pathCount; ++i){
		uint32_t flowId = 0, hopCount = 0;
		paths >> flowId >> hopCount;
		if (!paths || flowId >= flow_num || hopCount == 0 ||
				hopCount > IntHeader::maxHop ||
				flowPaths.count(flowId))
			ConfigError("malformed BOP multilink flow path row");
		for (uint32_t hop = 0; hop < hopCount; ++hop){
			uint32_t linkId = 0;
			paths >> linkId;
			if (!paths)
				ConfigError("truncated BOP multilink flow path");
			flowPaths[flowId].push_back(linkId);
		}
	}
	if (paths >> extra)
		ConfigError("extra content in BOP multilink path file");

	uint32_t groupCount = 0;
	groups >> groupCount;
	for (uint32_t i = 0; i < groupCount; ++i){
		uint32_t groupId = 0;
		int64_t predecessor = -1;
		uint64_t gapNs = 0, initialReleaseNs = 0;
		groups >> groupId >> predecessor >> gapNs >> initialReleaseNs;
		if (!groups || multilink_group_predecessors.count(groupId))
			ConfigError("malformed BOP multilink group row");
		if ((predecessor < 0 && initialReleaseNs == 0) ||
				(predecessor >= 0 && initialReleaseNs != 0))
			ConfigError("invalid BOP multilink root/release metadata");
		multilink_group_predecessors[groupId] = predecessor;
		multilink_group_gaps[groupId] = gapNs;
		multilink_group_initial_releases[groupId] = initialReleaseNs;
	}
	if (groups >> extra)
		ConfigError("extra content in BOP multilink group file");
	RdmaHw::ConfigureBopMultilink(true, definitions, flowPaths,
		multilink_group_predecessors);
}

void ReadCbapInputs(){
	cbap_links.clear();
	cbap_flow_paths.clear();
	cbap_link_by_id.clear();
	RdmaHw::CbapConfig config;
	config.enabled = cbap_enable;
	config.controlEpochNs = cbap_control_epoch_us * 1000;
	config.planningDelayNs = cbap_planning_delay_us * 1000;
	config.controlDelayNs = cbap_control_delay_us * 1000;
	config.rho = cbap_rho;
	config.epsilonRate = cbap_epsilon_rate;
	config.priority = cbap_priority;
	config.maxWirePacketBytes = cbap_max_wire_packet_bytes;
	config.summaryBytes = cbap_summary_bytes;
	config.grantBytes = cbap_grant_bytes;
	config.txTraceTrackingPackets = cbap_tx_trace_tracking_packets;
	config.increasePolicy = cbap_increase_policy;
	config.increaseFraction = cbap_increase_fraction;
	config.increaseAbsoluteBps = cbap_increase_absolute_bps;
	config.scopePolicy = cbap_scope_policy;
	config.scopeBaseCc = cbap_scope_base_cc;
	config.rateFloorPolicy = cbap_rate_floor_policy;
	config.rateFloorSemanticZeroTest = cbap_ratefloor_semantic_zero_test;
	config.rateFloorSemanticZeroFlow = cbap_ratefloor_semantic_zero_flow;
	config.rateFloorSemanticZeroStartEpoch =
		cbap_ratefloor_semantic_zero_start_epoch;
	config.rateFloorSemanticZeroEndEpoch =
		cbap_ratefloor_semantic_zero_end_epoch;
	config.handoffEnabled = cbap_handoff_enable;
	config.handoffStableEpochsRequired = cbap_handoff_stable_epochs;
	config.handoffBaseCc = cbap_handoff_base_cc;
	config.handoffDiagnosticForceRoot =
		cbap_handoff_diagnostic_force_root;
	config.handoffDiagnosticRecoveryUntilEpoch =
		cbap_handoff_diagnostic_recovery_until_epoch;
	config.delegationDiagnosticForceStaleEpochs =
		cbap_delegation_diagnostic_force_stale_epochs;
	config.queueTargetFraction = cbap_queue_target_fraction;
	config.sbaLeaseNs = cbap_sba_lease_us * 1000;
	config.budgetQLowFraction = cbap_budget_q_low_fraction;
	config.budgetQHighFraction = cbap_budget_q_high_fraction;
	config.maxDrainRatio = cbap_max_drain_ratio;
	config.oldBatchWeight = cbap_old_batch_weight;
	config.newBatchWeight = cbap_new_batch_weight;
	config.migrationEnabled = cbap_migration_enable;
	config.migrationReleaseRatio = cbap_migration_release_ratio;
	config.migrationDecayBase = cbap_migration_decay_base;
	config.migrationRiseBase = cbap_migration_rise_base;
	config.migrationRiseSkew = cbap_migration_rise_skew;
	config.migrationMaxRtt = cbap_migration_max_rtt;
	config.scenario = scenario_name;
	config.algorithm = algorithm_name;
	config.cbapVersion = cbap_version;
	if (!cbap_enable){
		RdmaHw::ConfigureCbap(config, cbap_links, cbap_flow_paths);
		return;
	}
	if (!RdmaHw::IsCbapMode(cc_mode))
		ConfigError("CBAP_ENABLE requires a CBAP CC_MODE");
	if (cbap_link_file.empty() || cbap_path_file.empty())
		ConfigError("CBAP link and path files are required");
	ifstream links(cbap_link_file.c_str());
	ifstream paths(cbap_path_file.c_str());
	if (!links.is_open() || !paths.is_open())
		ConfigError("cannot open CBAP link/path input");
	uint32_t linkCount = 0;
	links >> linkCount;
	for (uint32_t i = 0; i < linkCount; ++i){
		RdmaHw::BopMultilinkLink link;
		uint32_t telemetry = 0;
		links >> link.linkId >> link.nodeId >> link.ifIndex >>
			link.capacityBps >> link.ecnThresholdBytes >>
			link.backgroundBps >> telemetry;
		if (!links || link.capacityBps <= link.backgroundBps ||
				link.ecnThresholdBytes == 0 ||
				telemetry > 1 ||
				cbap_link_by_id.count(link.linkId))
			ConfigError("malformed CBAP link row");
		link.telemetryEligible = telemetry != 0;
		cbap_links.push_back(link);
		cbap_link_by_id[link.linkId] = link;
		if (link.telemetryEligible)
			selected_link_set.insert(make_pair(link.nodeId, link.ifIndex));
	}
	string extra;
	if (links >> extra)
		ConfigError("extra content in CBAP link file");
	uint32_t pathCount = 0;
	paths >> pathCount;
	if (pathCount != flow_num)
		ConfigError("CBAP path count differs from flow count");
	for (uint32_t i = 0; i < pathCount; ++i){
		uint32_t flowId = 0, hopCount = 0;
		paths >> flowId >> hopCount;
		if (!paths || flowId >= flow_num || hopCount == 0 ||
				cbap_flow_paths.count(flowId))
			ConfigError("malformed CBAP path row");
		for (uint32_t hop = 0; hop < hopCount; ++hop){
			uint32_t linkId = 0;
			paths >> linkId;
			if (!paths || !cbap_link_by_id.count(linkId))
				ConfigError("CBAP path references unknown link");
			cbap_flow_paths[flowId].push_back(linkId);
		}
	}
	if (paths >> extra)
		ConfigError("extra content in CBAP path file");
	RdmaHw::ConfigureCbap(config, cbap_links, cbap_flow_paths);
}

RdmaHw::CbapPortSnapshot ReadCbapPort(uint32_t linkId){
	RdmaHw::CbapPortSnapshot snapshot;
	map<uint32_t, RdmaHw::BopMultilinkLink>::const_iterator definition =
		cbap_link_by_id.find(linkId);
	if (definition == cbap_link_by_id.end() ||
			definition->second.nodeId >= n.GetN())
		return snapshot;
	snapshot.timestampNs = Simulator::Now().GetTimeStep();
	snapshot.linkId = linkId;
	snapshot.switchId = definition->second.nodeId;
	snapshot.egressPort = definition->second.ifIndex;
	snapshot.capacityBps = definition->second.capacityBps;
	// Non-telemetry links (for example a dedicated host access link in the
	// Clos manifest) remain real path-capacity constraints, but they do not
	// expose switch queue/ECN/PFC counters.  Represent them as a valid static
	// capacity observation instead of treating the host as a switch.
	if (!definition->second.telemetryEligible){
		if (definition->second.ifIndex >=
				n.Get(definition->second.nodeId)->GetNDevices())
			return RdmaHw::CbapPortSnapshot();
		snapshot.valid = true;
		return snapshot;
	}
	Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(
		n.Get(definition->second.nodeId));
	if (!sw || definition->second.ifIndex >= sw->GetNDevices())
		return snapshot;
	snapshot.valid = true;
	snapshot.capacityBps =
		sw->GetEgressCapacityBps(definition->second.ifIndex);
	snapshot.queueBytes =
		sw->GetEgressQueueBytes(definition->second.ifIndex);
	snapshot.ingressBytes =
		sw->GetRxBytes(definition->second.ifIndex);
	snapshot.txBytes = sw->GetTxBytes(definition->second.ifIndex);
	snapshot.ecnMarks = sw->GetEcnMarks(definition->second.ifIndex);
	snapshot.pfcPauseEvents =
		sw->GetPfcPauseEvents(definition->second.ifIndex);
	snapshot.pfcResumeEvents =
		sw->GetPfcResumeEvents(definition->second.ifIndex);
	snapshot.pfcPauseDurationNs =
		sw->GetPfcPauseDurationNs(definition->second.ifIndex);
	snapshot.localPaused = sw->IsLocallyPaused(
		definition->second.ifIndex, cbap_priority);
	snapshot.downstreamPaused = sw->IsDownstreamPaused(
		definition->second.ifIndex, cbap_priority);
	return snapshot;
}

void WriteCbapSummaries(){
	if (!cbap_enable)
		return;
	if (!cbap_port_summary_file.empty()){
		ofstream output(cbap_port_summary_file.c_str());
		output << "sample_time_ns,delivery_time_ns,link_id,switch_id,"
			"egress_port,capacity_bps,queue_bytes,previous_queue_bytes,"
			"input_bytes_delta,output_bytes_delta,ecn_marks_delta,"
			"pfc_events_delta,pause_duration_delta_ns,arrival_rate_bps,"
			"service_rate_bps,queue_gradient_bytes_per_second,port_state,"
			"root_id,root_reason,effective_capacity_bps,"
			"active_controlled_flows,pending_controlled_flows,"
			"local_paused,downstream_paused,stale\n";
		const vector<RdmaHw::CbapPortRecord> &rows =
			RdmaHw::GetCbapPortRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapPortRecord &r = rows[i];
			output << r.sampleTimeNs << ',' << r.deliveryTimeNs << ','
				<< r.linkId << ',' << r.switchId << ','
				<< r.egressPort << ',' << r.capacityBps << ','
				<< r.queueBytes << ',' << r.previousQueueBytes << ','
				<< r.inputBytesDelta << ',' << r.outputBytesDelta << ','
				<< r.ecnMarksDelta << ',' << r.pfcEventsDelta << ','
				<< r.pauseDurationDeltaNs << ','
				<< r.arrivalRateBps << ',' << r.serviceRateBps << ','
				<< r.queueGradientBytesPerSecond << ','
				<< r.portState << ',' << r.rootId << ','
				<< r.rootReason << ',' << r.effectiveCapacityBps << ','
				<< r.activeControlledFlows << ','
				<< r.pendingControlledFlows << ','
				<< r.localPaused << ',' << r.downstreamPaused << ','
				<< r.stale << '\n';
		}
	}
	if (!cbap_admission_file.empty()){
		ofstream output(cbap_admission_file.c_str());
		output << "plan_start_ns,plan_complete_ns,application_ready_ns,"
			"network_release_ns,batch_id,flow_id,base_rate_bps,"
			"admit_rate_bps,initial_rate_bps,credit_bytes,"
			"feedback_horizon_ns,observed_queue_bytes,packet_margin_bytes,"
			"effective_capacity_bps,floor_scale,independent_diagnostic,"
			"capacity_valid\n";
		const vector<RdmaHw::CbapAdmissionRecord> &rows =
			RdmaHw::GetCbapAdmissionRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapAdmissionRecord &r = rows[i];
			output << r.planStartNs << ',' << r.planCompleteNs << ','
				<< r.applicationReadyNs << ',' << r.networkReleaseNs
				<< ',' << r.batchId << ',' << r.flowId << ','
				<< r.baseRateBps << ',' << r.admitRateBps << ','
				<< r.initialRateBps << ',' << r.creditBytes << ','
				<< r.feedbackHorizonNs << ',' << r.observedQueueBytes
				<< ',' << r.packetMarginBytes << ','
				<< r.effectiveCapacityBps << ',' << r.floorScale << ','
				<< r.independentDiagnostic << ',' << r.capacityValid
				<< '\n';
		}
	}
	if (!cbap_rate_transition_file.empty()){
		ofstream output(cbap_rate_transition_file.c_str());
		output << "time_ns,epoch,batch_id,flow_id,phase_before,"
			"phase_after,old_rate_bps,target_rate_bps,new_rate_bps,"
			"reason,root_id,feedback_age_ns,credit_remaining_bytes,"
			"protection_floor_bps,rebalance_start_ns,rebalance_end_ns,"
			"stale_feedback,capacity_valid\n";
		const vector<RdmaHw::CbapRateRecord> &rows =
			RdmaHw::GetCbapRateRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapRateRecord &r = rows[i];
			output << r.timeNs << ',' << r.epoch << ',' << r.batchId
				<< ',' << r.flowId << ',' << r.phaseBefore << ','
				<< r.phaseAfter << ',' << r.oldRateBps << ','
				<< r.targetRateBps << ',' << r.newRateBps << ','
				<< r.reason << ',' << r.rootId << ','
				<< r.feedbackAgeNs << ',' << r.creditRemainingBytes << ','
				<< r.protectionFloorBps << ',' << r.rebalanceStartNs << ','
				<< r.rebalanceEndNs << ',' << r.staleFeedback << ',' << r.capacityValid
				<< '\n';
		}
	}
	if (!cbap_applied_rate_audit_file.empty()){
		ofstream output(cbap_applied_rate_audit_file.c_str());
		output << "link_id,epoch,C_l,rho_C_l,C_effective_l,"
			"planner_grant_sum_bps,target_rate_sum_bps,"
			"applied_rate_sum_bps,actual_tx_rate_sum_bps,"
			"background_rate_bps,legacy_floor_rate_bps,"
			"flows_below_legacy_floor,floor_clamp_count,"
			"rate_clamp_delta_sum_bps,zero_grant_flow_count,"
			"paused_zero_grant_count,applied_capacity_excess_bps,"
			"applied_capacity_violation,actual_arrival_excess_bps\n";
		const vector<RdmaHw::CbapAppliedRateAuditRecord> &rows =
			RdmaHw::GetCbapAppliedRateAuditRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapAppliedRateAuditRecord &r = rows[i];
			output << r.linkId << ',' << r.epoch << ',' << r.capacityBps
				<< ',' << r.rhoCapacityBps << ','
				<< r.effectiveCapacityBps << ','
				<< r.plannerGrantSumBps << ',' << r.targetRateSumBps
				<< ',' << r.appliedRateSumBps << ','
				<< r.actualTxRateSumBps << ',' << r.backgroundRateBps
				<< ',' << r.legacyFloorRateBps << ','
				<< r.flowsBelowLegacyFloor << ',' << r.floorClampCount
				<< ',' << r.rateClampDeltaSumBps << ','
				<< r.zeroGrantFlowCount << ','
				<< r.pausedZeroGrantCount << ','
				<< r.appliedCapacityExcessBps << ','
				<< r.appliedCapacityViolation << ','
				<< r.actualArrivalExcessBps << '\n';
		}
	}
	if (!cbap_increase_audit_file.empty()){
		ofstream output(cbap_increase_audit_file.c_str());
		output << "timestamp_ns,scenario,algorithm,cbap_version,"
			"increase_policy,flow_id,batch_id,phase,"
			"current_rate_before_bps,target_rate_bps,max_rate_bps,"
			"fractional_candidate_bps,absolute_candidate_bps,"
			"selected_delta_bps,new_rate_bps,stable_epoch_count,"
			"feedback_age_ns,stale_feedback,limiting_link,reason\n";
		const vector<RdmaHw::CbapIncreaseRecord> &rows =
			RdmaHw::GetCbapIncreaseRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapIncreaseRecord &r = rows[i];
			output << r.timestampNs << ',' << r.scenario << ','
				<< r.algorithm << ',' << r.cbapVersion << ','
				<< r.increasePolicy << ',' << r.flowId << ','
				<< r.batchId << ',' << r.phase << ','
				<< r.currentRateBeforeBps << ',' << r.targetRateBps
				<< ',' << r.maxRateBps << ','
				<< r.fractionalCandidateBps << ','
				<< r.absoluteCandidateBps << ','
				<< r.selectedDeltaBps << ',' << r.newRateBps << ','
				<< r.stableEpochCount << ',' << r.feedbackAgeNs << ','
				<< r.staleFeedback << ',' << r.limitingLink << ','
				<< r.reason << '\n';
		}
	}
	if (!cbap_flow_state_file.empty()){
		ofstream output(cbap_flow_state_file.c_str());
		output << "flow_id,batch_id,application_ready_ns,"
			"network_release_ns,first_fresh_feedback_ns,admission_enter_ns,"
			"admission_exit_ns,first_data_tx_ns,first_post_release_sample_ns,"
			"first_complete_fresh_feedback_ns,initial_admit_rate_bps,"
			"actual_admission_mean_rate_bps,bytes_sent_before_fresh_feedback,"
			"rate_updates_before_first_tx,ordinary_rate_updates_during_admission,"
			"emergency_rate_updates_during_admission,credit_gate_enter_ns,"
			"credit_gate_exit_ns,credit_gate_active_at_finish,"
			"credit_remaining_at_admission_exit,tracking_actual_rate_bps,"
			"tracking_current_rate_bps,tracking_base_rate_bps,pacing_violations,"
			"estimated_first_feedback_ns,finish_ns,bytes_sent,"
			"bytes_acked,base_rate_bps,admit_rate_bps,final_rate_bps,"
			"initial_credit_bytes,remaining_credit_bytes,excess_bytes,"
			"capacity_violations,credit_violations,stale_feedback,"
			"rate_increases,rate_decreases,rate_holds,reschedules,"
			"fair80_ns,fair90_ns,fair95_ns\n";
		const vector<RdmaHw::CbapFlowRecord> &rows =
			RdmaHw::GetCbapFlowRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapFlowRecord &r = rows[i];
			output << r.flowId << ',' << r.batchId << ','
				<< r.applicationReadyNs << ',' << r.networkReleaseNs
				<< ',' << r.firstFreshFeedbackNs << ','
				<< r.admissionEnterNs << ',' << r.admissionExitNs << ','
				<< r.firstDataTxNs << ','
				<< r.firstPostReleaseSampleNs << ','
				<< r.firstCompleteFreshFeedbackNs << ','
				<< r.initialAdmitRateBps << ','
				<< r.actualAdmissionMeanRateBps << ','
				<< r.bytesSentBeforeFreshFeedback << ','
				<< r.rateUpdatesBeforeFirstTx << ','
				<< r.ordinaryRateUpdatesDuringAdmission << ','
				<< r.emergencyRateUpdatesDuringAdmission << ','
				<< r.creditGateEnterNs << ',' << r.creditGateExitNs << ','
				<< r.creditGateActiveAtFinish << ','
				<< r.creditRemainingAtAdmissionExit << ','
				<< r.trackingActualRateBps << ','
				<< r.trackingCurrentRateBps << ','
				<< r.trackingBaseRateBps << ',' << r.pacingViolations << ','
				<< r.estimatedFirstFeedbackNs << ',' << r.finishNs
				<< ',' << r.bytesSent << ',' << r.bytesAcked << ','
				<< r.baseRateBps << ',' << r.admitRateBps << ','
				<< r.finalRateBps << ',' << r.initialCreditBytes << ','
				<< r.remainingCreditBytes << ',' << r.excessBytes << ','
				<< r.capacityViolations << ',' << r.creditViolations
				<< ',' << r.staleFeedback << ',' << r.rateIncreases
				<< ',' << r.rateDecreases << ',' << r.rateHolds << ','
				<< r.reschedules << ',' << r.fair80Ns << ','
				<< r.fair90Ns << ',' << r.fair95Ns << '\n';
		}
	}
	if (!cbap_tx_event_file.empty()){
		ofstream output(cbap_tx_event_file.c_str());
		output << "time_ns,event,flow_id,batch_id,packet_seq,wire_bytes,phase,"
			"current_rate_bps,target_rate_bps,admit_rate_bps,base_rate_bps,"
			"credit_gate_active,credit_remaining_bytes,scheduled_time_ns,"
			"actual_send_time_ns,previous_tx_time_ns,expected_gap_ns,"
			"actual_gap_ns,reschedule_reason\n";
		const vector<RdmaHw::CbapTxRecord> &rows =
			RdmaHw::GetCbapTxRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapTxRecord &r = rows[i];
			const char *event = r.eventType == RdmaHw::CBAP_TX_SCHEDULE ?
				"TX_SCHEDULE" : r.eventType == RdmaHw::CBAP_TX_SEND ?
				"TX_SEND" : r.eventType == RdmaHw::CBAP_TX_RESCHEDULE ?
				"TX_RESCHEDULE" : "TX_CANCEL_OR_INVALIDATE";
			output << r.timeNs << ',' << event << ',' << r.flowId << ','
				<< r.batchId << ',' << r.packetSeq << ',' << r.wireBytes
				<< ',' << r.phase << ',' << r.currentRateBps << ','
				<< r.targetRateBps << ',' << r.admitRateBps << ','
				<< r.baseRateBps << ',' << r.creditGateActive << ','
				<< r.creditRemainingBytes << ',' << r.scheduledTimeNs << ','
				<< r.actualSendTimeNs << ',' << r.previousTxTimeNs << ','
				<< r.expectedGapNs << ',' << r.actualGapNs << ','
				<< r.rescheduleReason << '\n';
		}
	}
	if (!cbap_control_overhead_file.empty()){
		ofstream output(cbap_control_overhead_file.c_str());
		uint64_t summaries = RdmaHw::GetCbapSummaryMessageCount();
		uint64_t grants = RdmaHw::GetCbapGrantMessageCount();
		output << "summary_messages,grant_messages,summary_bytes_each,"
			"grant_bytes_each,total_control_bytes,control_delay_ns,"
			"planning_delay_ns\n";
		output << summaries << ',' << grants << ','
			<< cbap_summary_bytes << ',' << cbap_grant_bytes << ','
			<< summaries * cbap_summary_bytes +
				grants * cbap_grant_bytes << ','
			<< cbap_control_delay_us * 1000 << ','
			<< cbap_planning_delay_us * 1000 << '\n';
	}
	if (!cbap_scope_summary_file.empty()){
		ofstream output(cbap_scope_summary_file.c_str());
		output << "batch_id,application_ready_ns,decision_complete_ns,"
			"decision_delay_ns,flow_count,used_link_count,enabled,reason,"
			"triggering_link_count,maximum_pending_count,"
			"maximum_oversubscription_ratio\n";
		const vector<RdmaHw::CbapScopeBatchRecord> &rows =
			RdmaHw::GetCbapScopeBatchRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapScopeBatchRecord &r = rows[i];
			const char *reason = r.reason ==
				RdmaHw::CBAP_SCOPE_REASON_SHARED_BATCH_OVERSUBSCRIBED ?
				"SHARED_BATCH_OVERSUBSCRIBED" : r.reason ==
				RdmaHw::CBAP_SCOPE_REASON_NO_SHARED_LINK ?
				"NO_SHARED_LINK" : r.reason ==
				RdmaHw::CBAP_SCOPE_REASON_WITHIN_ADMISSION_CAPACITY ?
				"WITHIN_ADMISSION_CAPACITY" : "ALWAYS";
			output << r.batchId << ',' << r.applicationReadyNs << ','
				<< r.decisionCompleteNs << ',' << r.decisionDelayNs << ','
				<< r.flowCount << ',' << r.usedLinkCount << ','
				<< r.enabled << ',' << reason << ','
				<< r.triggeringLinkCount << ',' << r.maximumPendingCount
				<< ',' << r.maximumOversubscriptionRatio << '\n';
		}
	}
	if (!cbap_scope_link_file.empty()){
		ofstream output(cbap_scope_link_file.c_str());
		output << "batch_id,application_ready_ns,newest_summary_sample_ns,"
			"newest_summary_delivery_ns,link_id,switch_id,egress_port,"
			"pending_count,A_admit_bps,independent_aggregate_bps,"
			"oversubscription_bps,oversubscription_ratio,enabled_on_link,"
			"pre_release_causal\n";
		const vector<RdmaHw::CbapScopeLinkRecord> &rows =
			RdmaHw::GetCbapScopeLinkRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapScopeLinkRecord &r = rows[i];
			output << r.batchId << ',' << r.applicationReadyNs << ','
				<< r.newestSummarySampleNs << ','
				<< r.newestSummaryDeliveryNs << ',' << r.linkId << ','
				<< r.switchId << ',' << r.egressPort << ','
				<< r.pendingCount << ',' << r.admissionCapacityBps << ','
				<< r.independentAggregateBps << ','
				<< r.oversubscriptionBps << ','
				<< r.oversubscriptionRatio << ',' << r.enabledOnLink << ','
				<< r.preReleaseCausal << '\n';
		}
	}
	if (!cbap_handoff_summary_file.empty()){
		ofstream output(cbap_handoff_summary_file.c_str());
		output << "scenario,algorithm,batch_id,application_ready_ns,"
			"network_release_ns,tracking_enter_ns,first_stable_epoch_ns,"
			"handoff_candidate_ns,handoff_execute_ns,handoff_occurred,"
			"no_handoff_reason,stable_epoch_count,measured_rtt_ns,"
			"minimum_tracking_time_ns,active_flow_count,"
			"remaining_bytes_total,remaining_fraction,"
			"queue_bytes_at_handoff,queue_gradient_at_handoff,"
			"applied_rate_sum_before,dcqcn_rate_sum_after_init,"
			"max_per_flow_rate_jump_bps,first_dcqcn_rate_update_ns,"
			"first_dcqcn_cnp_ns,grants_before_handoff,"
			"grants_after_handoff,control_bytes_before_handoff,"
			"control_bytes_after_handoff,shadow_handoff_candidate_time,"
			"shadow_remaining_bytes,shadow_remaining_fraction,"
			"shadow_queue,shadow_rate_sum,"
			"shadow_controlled_after_candidate_ns\n";
		const vector<RdmaHw::CbapHandoffBatchRecord> &rows =
			RdmaHw::GetCbapHandoffBatchRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapHandoffBatchRecord &r = rows[i];
			output << scenario_name << ',' << algorithm_name << ','
				<< r.batchId << ',' << r.applicationReadyNs << ','
				<< r.networkReleaseNs << ',' << r.trackingEnterNs << ','
				<< r.firstStableEpochNs << ',' << r.handoffCandidateNs << ','
				<< r.handoffExecuteNs << ',' << r.handoffOccurred << ','
				<< r.noHandoffReason << ',' << r.stableEpochCount << ','
				<< r.measuredRttNs << ',' << r.minimumTrackingTimeNs << ','
				<< r.activeFlowCount << ',' << r.remainingBytesTotal << ','
				<< r.remainingFraction << ',' << r.queueBytesAtHandoff << ','
				<< r.queueGradientAtHandoff << ','
				<< r.appliedRateSumBefore << ',' << r.dcqcnRateSumAfterInit
				<< ',' << r.maxPerFlowRateJumpBps << ','
				<< r.firstDcqcnRateUpdateNs << ',' << r.firstDcqcnCnpNs
				<< ',' << r.grantsBeforeHandoff << ','
				<< r.grantsAfterHandoff << ','
				<< r.controlBytesBeforeHandoff << ','
				<< r.controlBytesAfterHandoff << ','
				<< r.shadowHandoffCandidateNs << ','
				<< r.shadowRemainingBytes << ','
				<< r.shadowRemainingFraction << ','
				<< r.shadowQueueBytes << ',' << r.shadowRateSumBps << ','
				<< r.shadowControlledAfterCandidateNs << '\n';
		}
	}
	if (!cbap_handoff_flow_file.empty()){
		ofstream output(cbap_handoff_flow_file.c_str());
		output << "flow_id,batch_id,phase_before,phase_after,remaining_bytes,"
			"cbap_applied_rate_before,dcqcn_current_rate_after,"
			"dcqcn_target_rate_after,alpha_after,next_tx_before,"
			"next_tx_after,first_tx_after_handoff,packet_gap_required,"
			"packet_gap_actual,catchup_burst_detected\n";
		const vector<RdmaHw::CbapHandoffFlowRecord> &rows =
			RdmaHw::GetCbapHandoffFlowRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapHandoffFlowRecord &r = rows[i];
			output << r.flowId << ',' << r.batchId << ',' << r.phaseBefore
				<< ',' << r.phaseAfter << ',' << r.remainingBytes << ','
				<< r.cbapAppliedRateBefore << ',' << r.dcqcnCurrentRateAfter
				<< ',' << r.dcqcnTargetRateAfter << ',' << r.alphaAfter << ','
				<< r.nextTxBeforeNs << ',' << r.nextTxAfterNs << ','
				<< r.firstTxAfterHandoffNs << ',' << r.packetGapRequiredNs
				<< ',' << r.packetGapActualNs << ','
				<< r.catchupBurstDetected << '\n';
		}
	}
	if (!cbap_controller_ownership_file.empty()){
		ofstream output(cbap_controller_ownership_file.c_str());
		output << "time_ns,epoch,batch_id,flow_id,phase,owner,"
			"cbap_rate_update,dcqcn_rate_update\n";
		const vector<RdmaHw::CbapControllerOwnershipRecord> &rows =
			RdmaHw::GetCbapControllerOwnershipRecords();
		for (uint32_t i = 0; i < rows.size(); ++i)
			output << rows[i].timeNs << ',' << rows[i].epoch << ','
				<< rows[i].batchId << ',' << rows[i].flowId << ','
				<< rows[i].phase << ',' << rows[i].owner << ','
				<< rows[i].cbapRateUpdate << ','
				<< rows[i].dcqcnRateUpdate << '\n';
	}
	if (!cbap_control_message_file.empty()){
		ofstream output(cbap_control_message_file.c_str());
		output << "time_ns,epoch,batch_id,"
			"cbap_active_control_message_count,"
			"cbap_monitoring_only_message_count,grant_message_count\n";
		const vector<RdmaHw::CbapControlMessageRecord> &rows =
			RdmaHw::GetCbapControlMessageRecords();
		for (uint32_t i = 0; i < rows.size(); ++i)
			output << rows[i].timeNs << ',' << rows[i].epoch << ','
				<< rows[i].batchId << ',' << rows[i].activeControlSummaries
				<< ',' << rows[i].monitoringOnlySummaries << ','
				<< rows[i].grants << '\n';
	}
	if (!cbap_envelope_link_file.empty()){
		ofstream output(cbap_envelope_link_file.c_str());
		output << "epoch_ns,epoch,batch_id,link_id,C_effective_bps,"
			"incumbent_reserve_bps,batch_budget_bps,delegated_flow_count,"
			"desired_rate_sum_bps,applied_rate_sum_bps,scale_l,"
			"stale_feedback,cap_increase_allowed,reserve_release_bps,"
			"envelope_capacity_excess_bps,envelope_capacity_violation\n";
		const vector<RdmaHw::CbapEnvelopeLinkRecord> &rows =
			RdmaHw::GetCbapEnvelopeLinkRecords();
		for (uint32_t i=0; i<rows.size(); ++i){ const auto &r=rows[i];
			output << r.epochNs << ',' << r.epoch << ',' << r.batchId << ','
				<< r.linkId << ',' << r.effectiveCapacityBps << ','
				<< r.incumbentReserveBps << ',' << r.batchBudgetBps << ','
				<< r.delegatedFlowCount << ',' << r.desiredRateSumBps << ','
				<< r.appliedRateSumBps << ',' << r.scale << ','
				<< r.staleFeedback << ',' << r.capIncreaseAllowed << ','
				<< r.reserveReleaseBps << ',' << r.capacityExcessBps << ','
				<< r.capacityViolation << '\n'; }
	}
	if (!cbap_envelope_flow_file.empty()){
		ofstream output(cbap_envelope_flow_file.c_str());
		output << "epoch_ns,epoch,batch_id,flow_id,desired_rate_bps,"
			"applied_rate_bps,path_scale,envelope_bound,"
			"positive_ai_suppressed,decrease_applied,packet_gap_ns,"
			"simulator_internal_rate_write_count,"
			"post_delegation_full_cbap_grant_count,"
			"desired_writer,applied_writer\n";
		const vector<RdmaHw::CbapEnvelopeFlowRecord> &rows =
			RdmaHw::GetCbapEnvelopeFlowRecords();
		for (uint32_t i=0; i<rows.size(); ++i){ const auto &r=rows[i];
			output << r.epochNs << ',' << r.epoch << ',' << r.batchId << ','
				<< r.flowId << ',' << r.desiredRateBps << ','
				<< r.appliedRateBps << ',' << r.pathScale << ','
				<< r.envelopeBound << ',' << r.positiveAiSuppressed << ','
				<< r.decreaseApplied << ',' << r.packetGapNs << ','
				<< r.simulatorInternalRateWriteCount << ','
				<< r.postDelegationFullCbapGrantCount << ','
				<< r.desiredWriter << ',' << r.appliedWriter << '\n'; }
	}
	if (!cbap_incumbent_progress_file.empty()){
		ofstream output(cbap_incumbent_progress_file.c_str());
		output << "time_ns,flow_id,batch_id,size_bytes,sent_bytes,acked_bytes,"
			"remaining_bytes,current_rate_bps,target_rate_bps,"
			"protection_floor_bps,time_below_90_target_ns,"
			"time_below_80_target_ns,time_below_50_target_ns,finished\n";
		vector<RdmaHw::CbapIncumbentRecord> rows =
			RdmaHw::GetCbapIncumbentRecords();
		for (uint32_t i=0; i<rows.size(); ++i){ const auto &r=rows[i];
			output << r.timeNs << ',' << r.flowId << ',' << r.batchId << ','
				<< r.sizeBytes << ',' << r.sentBytes << ',' << r.ackedBytes << ','
				<< r.remainingBytes << ',' << r.currentRateBps << ','
				<< r.targetRateBps << ',' << r.protectionFloorBps << ','
				<< r.timeBelow90TargetNs << ',' << r.timeBelow80TargetNs << ','
				<< r.timeBelow50TargetNs << ',' << r.finished << '\n'; }
	}
	if (!cbap_v20_batch_file.empty()){
		ofstream output(cbap_v20_batch_file.c_str());
		output << "batch_id,link_id,classification,classification_reason,"
			"risky_link_count,blind_window_ns,Q0_bytes,Q_target_bytes,"
			"C_effective_bps,W_l_bytes,S_l_bytes,E_l_bytes,R_startup_bps,"
			"admission_aggregate_bps,actual_applied_aggregate_bps,"
			"first_fresh_feedback_ns,lease_expiry_ns,handoff_ns,"
			"handoff_reason,base_cc,post_handoff_cbap_write_count,"
			"catch_up_burst,capacity_violation,pacing_violation,"
			"pre_release_causal\n";
		const vector<RdmaHw::CbapV20BatchRecord> &rows =
			RdmaHw::GetCbapV20BatchRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapV20BatchRecord &r = rows[i];
			output << r.batchId << ',' << r.linkId << ','
				<< r.classification << ',' << r.classificationReason << ','
				<< r.riskyLinkCount << ',' << r.blindWindowNs << ','
				<< r.queue0Bytes << ',' << r.queueTargetBytes << ','
				<< r.effectiveCapacityBps << ',' << r.blindWorkBytes << ','
				<< r.serviceAndBufferBytes << ',' << r.excessBytes << ','
				<< r.startupBudgetBps << ',' << r.admissionAggregateBps << ','
				<< r.actualAppliedAggregateBps << ','
				<< r.firstFreshFeedbackNs << ',' << r.leaseExpiryNs << ','
				<< r.handoffNs << ',' << r.handoffReason << ',' << r.baseCc
				<< ',' << r.postHandoffCbapWriteCount << ','
				<< r.catchUpBurst << ',' << r.capacityViolation << ','
				<< r.pacingViolation << ',' << r.preReleaseCausal << '\n';
		}
	}
	if (!cbap_v20_flow_file.empty()){
		ofstream output(cbap_v20_flow_file.c_str());
		output << "batch_id,flow_id,classification,startup_grant_bps,"
			"path_min_grant_bps,applied_rate_bps,packet_gap_ns,"
			"first_fresh_feedback_ns,handoff_initial_rate_bps,"
			"post_handoff_owner,post_handoff_cbap_write_count,"
			"catch_up_burst\n";
		const vector<RdmaHw::CbapV20FlowRecord> &rows =
			RdmaHw::GetCbapV20FlowRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const RdmaHw::CbapV20FlowRecord &r = rows[i];
			output << r.batchId << ',' << r.flowId << ','
				<< r.classification << ',' << r.startupGrantBps << ','
				<< r.pathMinGrantBps << ',' << r.appliedRateBps << ','
				<< r.packetGapNs << ',' << r.firstFreshFeedbackNs << ','
				<< r.handoffInitialRateBps << ',' << r.postHandoffOwner << ','
				<< r.postHandoffCbapWriteCount << ',' << r.catchUpBurst
				<< '\n';
		}
	}
	if (!cbap_sba_event_file.empty()){
		ofstream output(cbap_sba_event_file.c_str());
		output << "batch_id,flow_id,release_time,path,available_capacity,"
			"grant_rate,applied_rate,state_transition,hold_reason,"
			"readmission_reason,first_feedback_time,handoff_rate\n";
		const vector<CbapSbaController::EventRecord> &rows =
			RdmaHw::GetCbapSbaEventRecords();
		for (uint32_t i = 0; i < rows.size(); ++i){
			const CbapSbaController::EventRecord &r = rows[i];
			output << r.batchId << ',' << r.flowId << ','
				<< r.releaseTimeNs << ',' << r.path << ','
				<< r.availableCapacity << ',' << r.grantRateBps << ','
				<< r.appliedRateBps << ',' << r.stateTransition << ','
				<< r.holdReason << ',' << r.readmissionReason << ','
				<< r.firstFeedbackTimeNs << ',' << r.handoffRateBps
				<< '\n';
		}
	}
}

void ReadRoundSchedule(){
	if (!round_mode)
		return;
	ifstream input(round_schedule_file.c_str());
	if (!input.is_open())
		ConfigError("cannot open ROUND_SCHEDULE_FILE " + round_schedule_file);
	uint32_t count = 0;
	input >> count;
	for (uint32_t i = 0; i < count; ++i){
		uint32_t flowId;
		RdmaQueuePair::CrfmRoundState round;
		input >> flowId >> round.roundId >> round.roundGroupId >>
			round.participantCount >> round.roundBytes >>
			round.computeGapNs >> round.jitterNs >> round.jitterGroup >>
			round.commonReleaseHintNs;
		if (!input)
			ConfigError("malformed ROUND_SCHEDULE_FILE row");
		if (flowId >= flow_num)
			ConfigError("round flow_id out of range");
		vector<RdmaQueuePair::CrfmRoundState> &rounds =
			round_schedules[flowId];
		if (round.roundId != rounds.size())
			ConfigError("round_id must be contiguous per flow");
			if (!bop_multilink_enable){
				if (round.roundId == 0 && round.computeGapNs != 0)
					ConfigError("first round compute_gap must be zero");
				if (round.roundId == 0 && round.commonReleaseHintNs == 0)
					ConfigError("first round requires common_release_hint_ns");
				if (round.roundId > 0 && round.commonReleaseHintNs != 0)
					ConfigError("later rounds must use dynamic common release");
			}else{
				if (!multilink_group_predecessors.count(
						round.roundGroupId) ||
						round.computeGapNs !=
							multilink_group_gaps[round.roundGroupId] ||
						round.commonReleaseHintNs !=
							multilink_group_initial_releases[
								round.roundGroupId])
					ConfigError("round row differs from multilink group schedule");
			}
			if (round.participantCount == 0)
				ConfigError("round participant_count must be positive");
			if (!bop_multilink_enable && round.roundId > 0 &&
					(int64_t)round.computeGapNs + round.jitterNs <= 0)
				ConfigError("round compute_gap+jitter must be positive");
		rounds.push_back(round);
	}
	string extra;
	if (input >> extra)
		ConfigError("extra content in ROUND_SCHEDULE_FILE");
	if (round_schedules.size() != flow_num)
		ConfigError("every flow must have a round schedule");
	map<uint32_t, uint32_t> groupParticipants;
	map<uint32_t, uint64_t> groupGaps, groupHints;
	map<uint32_t, set<uint32_t> > groupFlows;
	for (auto schedule : round_schedules)
		for (auto round : schedule.second){
			auto known = groupParticipants.find(round.roundGroupId);
			if (known == groupParticipants.end())
				groupParticipants[round.roundGroupId] =
					round.participantCount;
			else if (known->second != round.participantCount)
				ConfigError("round_group participant_count mismatch");
			groupFlows[round.roundGroupId].insert(schedule.first);
			if (!groupGaps.count(round.roundGroupId)){
				groupGaps[round.roundGroupId] = round.computeGapNs;
				groupHints[round.roundGroupId] = round.commonReleaseHintNs;
			}else if (groupGaps[round.roundGroupId] != round.computeGapNs ||
					groupHints[round.roundGroupId] != round.commonReleaseHintNs)
				ConfigError("round_group release metadata mismatch");
		}
	for (auto group : groupParticipants)
		if (groupFlows[group.first].size() != group.second)
			ConfigError("round_group membership differs from participant_count");
}

Ptr<RdmaQueuePair> FindExperimentQp(ExperimentFlow &f){
	if (f.qp) return f.qp;
	Ptr<RdmaDriver> d=n.Get(f.src)->GetObject<RdmaDriver>();
	f.qp=d->m_rdma->GetQp(serverAddress[f.dst].Get(),f.sport,f.pg);
	return f.qp;
}

string CrfmPhase(Ptr<RdmaQueuePair> qp);

void CbapPacketTraceDequeue(Ptr<SwitchNode> sw,
		Ptr<const Packet> original, uint32_t inputPort,
		uint32_t outputPort, uint32_t qIndex){
	if (!cbap_packet_trace_csv || cbap_packet_trace_truncated ||
			qIndex == 0 ||
			!selected_link_set.count(
				make_pair(sw->GetId(), outputPort)))
		return;
	Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(
		sw->GetDevice(outputPort));
	if (!dev)
		return;
	Ptr<Packet> packet = original->Copy();
	CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
		CustomHeader::L4_Header);
	ch.brief = 0;
	ch.getInt = 1;
	packet->PeekHeader(ch);
	if (ch.l3Prot != 0x11)
		return;
	uint32_t src = (ch.sip >> 8) & 0xffff;
	uint32_t dst = (ch.dip >> 8) & 0xffff;
	ExperimentFlow *flow = NULL;
	for (size_t i = 0; i < experiment_flows.size(); ++i){
		if (experiment_flows[i].src == src &&
				experiment_flows[i].dst == dst &&
				experiment_flows[i].sport == ch.udp.sport &&
				experiment_flows[i].dport == ch.udp.dport){
			flow = &experiment_flows[i];
			break;
		}
	}
	if (!flow)
		return;
	Ptr<RdmaQueuePair> qp = FindExperimentQp(*flow);
	uint32_t batchId = 0;
	if (qp && qp->crfm.enabled && qp->crfm.currentRoundIndex >= 0)
		batchId = qp->crfm.rounds[
			qp->crfm.currentRoundIndex].roundGroupId;
	if (qp && qp->cbap.enabled)
		batchId = qp->cbap.batchId;
	uint32_t intBytes = IntHeader::GetStaticSize();
	uint32_t seqBytes = 6;
	uint32_t payloadBytes = ch.udp.payload_size >
		8 + intBytes + seqBytes ?
		ch.udp.payload_size - 8 - intBytes - seqBytes : 0;
	uint64_t queueAfter = dev->GetQueue()->GetNBytesTotal();
	uint64_t queueBefore = queueAfter + packet->GetSize();
	uint64_t currentRate = qp ? qp->m_rate.GetBitRate() : 0;
	uint64_t targetRate = qp && qp->cbap.enabled ?
		qp->cbap.targetRateBps : currentRate;
	uint64_t admitRate = qp && qp->cbap.enabled ?
		qp->cbap.admitRateBps : currentRate;
	uint64_t baseRate = qp && qp->cbap.enabled ?
		qp->cbap.baseRateBps : currentRate;
	uint64_t credit = qp && qp->cbap.enabled ?
		qp->cbap.creditRemainingBytes : 0;
	uint64_t feedbackAge = qp && qp->cbap.enabled &&
		qp->cbap.lastFreshFeedbackNs ?
		Simulator::Now().GetNanoSeconds() -
			qp->cbap.lastFreshFeedbackNs : 0;
	string phase = qp && qp->cbap.enabled ?
		to_string((uint32_t)qp->cbap.phase) : CrfmPhase(qp);
	stringstream row;
	row << Simulator::Now().GetNanoSeconds() << ','
		<< scenario_name << ",," << algorithm_name << ',' << sim_seed
		<< ',' << batchId << ',' << flow->id << ',' << ch.udp.seq
		<< ",DATA," << payloadBytes << ',' << packet->GetSize() << ','
		<< src << ',' << dst << ',' << dev->GetNode()->GetId() << ','
		<< inputPort << ',' << dev->GetIfIndex()
		<< ",SWITCH_DEQUEUE," << queueBefore << ',' << queueAfter << ','
		<< currentRate << ',' << targetRate << ',' << targetRate << ','
		<< targetRate << ',' << admitRate << ',' << baseRate << ','
		<< credit << ',' << phase << ','
		<< (qp && qp->cbap.enabled ? qp->cbap.rootId : 0)
		<< ",-1," << feedbackAge << '\n';
	long position = ftell(cbap_packet_trace_csv);
	uint64_t limit =
		(uint64_t)cbap_packet_trace_max_mb * 1024 * 1024;
	if (position < 0 || (uint64_t)position + row.str().size() > limit){
		cbap_packet_trace_truncated = true;
		cerr << "CBAP_PACKET_TRACE_TRUNCATED" << endl;
		return;
	}
	const string text = row.str();
	fwrite(text.data(), 1, text.size(), cbap_packet_trace_csv);
	cbap_packet_trace_rows++;
}

void SetupCbapPacketTrace(){
	// /dev/null is the explicit production setting for disabling the optional
	// packet-level diagnostic while still satisfying the bounded-trace config
	// contract.  Do not attach trace callbacks (or validate trace-only switch
	// targets) when the output is intentionally discarded.
	if (sim_seed != 1 || cbap_packet_trace_file.empty() ||
			cbap_packet_trace_file == "/dev/null")
		return;
	cbap_packet_trace_csv = fopen(cbap_packet_trace_file.c_str(), "w");
	if (!cbap_packet_trace_csv)
		ConfigError("cannot open CBAP_PACKET_TRACE_FILE");
	fprintf(cbap_packet_trace_csv,
		"timestamp_ns,scenario,subcase,algorithm,seed,batch_id,flow_id,"
		"packet_seq,packet_type,payload_bytes,wire_bytes,sender,receiver,"
		"switch,ingress_port,egress_port,event,queue_before,queue_after,"
		"current_rate,target_rate,local_grant,path_min_grant,admit_rate,"
		"base_rate,credit_remaining,phase,root_id,port_state,"
		"feedback_age\n");
	for (set<pair<uint32_t,uint32_t> >::const_iterator link =
			selected_link_set.begin(); link != selected_link_set.end();
			++link){
		if (link->first >= n.GetN() ||
				link->second >= n.Get(link->first)->GetNDevices())
			ConfigError("packet trace controlled link is invalid");
	}
	set<uint32_t> connectedSwitches;
	for (set<pair<uint32_t,uint32_t> >::const_iterator link =
			selected_link_set.begin(); link != selected_link_set.end();
			++link){
		if (!connectedSwitches.insert(link->first).second)
			continue;
		Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(link->first));
		if (!sw)
			ConfigError("packet trace target is not a switch");
		sw->TraceConnectWithoutContext("EgressDequeue",
			MakeBoundCallback(&CbapPacketTraceDequeue, sw));
	}
}

string CrfmPhase(Ptr<RdmaQueuePair> qp){
	if (!qp || !qp->crfm.enabled || qp->crfm.currentRoundIndex < 0)
		return "WAIT_RELEASE";
	RdmaQueuePair::CrfmRoundState &round =
		qp->crfm.rounds[qp->crfm.currentRoundIndex];
	if (qp->snd_nxt < round.endSeq)
		return "INJECTING";
	if (qp->snd_una < round.endSeq)
		return "WAIT_ACK";
	if ((uint32_t)(qp->crfm.currentRoundIndex + 1) <
			qp->crfm.rounds.size())
		return "OFF";
	return qp->IsFinished() ? "DONE" : "WAIT_ACK";
}

void UpdateRoundPeakQueue(uint64_t queueBytes){
	uint64_t now = Simulator::Now().GetTimeStep();
	for (size_t i = 0; i < experiment_flows.size(); ++i){
		Ptr<RdmaQueuePair> qp = FindExperimentQp(experiment_flows[i]);
		if (!qp || !qp->crfm.enabled)
			continue;
		for (uint32_t r = 0; r < qp->crfm.rounds.size(); ++r){
			RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[r];
			if (now >= round.releaseTimeNs &&
					(round.ackCompletionTimeNs == 0 ||
					 now <= round.ackCompletionTimeNs))
				round.selectedLinkPeakQueue = std::max(
					round.selectedLinkPeakQueue, queueBytes);
		}
	}
}

void LinkTraceTick(){
	uint64_t lim=(uint64_t)crfm_max_trace_file_mb*1024*1024;
	bool record = !bop_multilink_enable ||
		RdmaHw::HasActiveBopMultilinkGroup();
	for(auto l:selected_link_set){
		Ptr<SwitchNode>s=DynamicCast<SwitchNode>(n.Get(l.first)); if(!s)continue;
		Ptr<QbbNetDevice>d=DynamicCast<QbbNetDevice>(s->GetDevice(l.second));
		uint64_t tx=s->GetTxBytes(l.second),ecn=s->GetEcnMarks(l.second),dt=tx-trace_last_tx[l];
		double util=dt*8.0/(crfm_trace_sample_us*1e-6)/d->GetDataRate().GetBitRate();
		uint64_t queue=d->GetQueue()->GetNBytesTotal();
		uint64_t ecnDelta=ecn-trace_last_ecn[l];
		uint64_t pfcDelta=pfc_total_events-pfc_last_sample_events;
		if (record){
			UpdateRoundPeakQueue(queue);
			RdmaHw::ObserveRoundBottleneck(queue, ecnDelta, pfcDelta);
			stringstream z;z<<Simulator::Now().GetSeconds()<<","<<l.first<<":"<<l.second
				<<","<<queue<<","<<util<<","<<dt<<","<<ecnDelta
				<<","<<(d->IsPaused(3)?1:0)<<","
				<<pfcDelta<<"\n";
			DetailedCsvWrite(link_csv,lim,z.str());
		}
		trace_last_tx[l]=tx;trace_last_ecn[l]=ecn;
	}
	pfc_last_sample_events=pfc_total_events;
	Simulator::Schedule(MicroSeconds(crfm_trace_sample_us),&LinkTraceTick);
}

void FlowTraceTick(){
	uint64_t lim=(uint64_t)crfm_max_trace_file_mb*1024*1024;
	for(size_t i=0;i<experiment_flows.size();i++)if(selected_flow_set.count(experiment_flows[i].id)){
		ExperimentFlow &f=experiment_flows[i];Ptr<RdmaQueuePair>q=FindExperimentQp(f);
		stringstream z;z<<Simulator::Now().GetSeconds()<<","<<f.id;
		if(q) z<<","<<q->crfm.currentRoundIndex<<","<<CrfmPhase(q)
			<<","<<q->snd_nxt<<","<<q->snd_una<<","<<q->crfm.releasedBytes
			<<","<<q->m_rate.GetBitRate()<<","
			<<q->crfm.latestFeedbackOriginRound<<","
			<<q->crfm.latestFeedbackClass;
		else z<<",-1,WAIT_RELEASE,0,0,0,0,-1,0";
		z<<"\n";DetailedCsvWrite(selected_csv,lim,z.str());
	}
	Simulator::Schedule(MicroSeconds(std::max((uint64_t)20,
		crfm_trace_sample_us)),&FlowTraceTick);
}

map<uint32_t, int32_t> forced_spines;
FILE *fixed_path_output = NULL;
FILE *port_monitor_output = NULL;
set<pair<uint32_t, uint32_t> > monitored_ports;
map<pair<uint32_t, uint32_t>, uint32_t> monitored_port_peers;
map<pair<uint32_t, uint32_t>, uint64_t> monitored_last_tx;
map<pair<uint32_t, uint32_t>, uint64_t> monitored_last_time;

void ConfigError(const string &message){
	cerr << "CONFIG_ERROR: " << message << endl;
	exit(1);
}

void ReadFixedPaths(){
	if (fixed_path_file.empty())
		return;
	ifstream input(fixed_path_file.c_str());
	if (!input.is_open())
		ConfigError("cannot open " + fixed_path_file);
	uint32_t flow_index;
	int32_t spine_id;
	while (input >> flow_index >> spine_id){
		if (flow_index >= flow_num)
			ConfigError("flow_index out of range in " + fixed_path_file);
		if (spine_id < -1)
			ConfigError("forced_spine_id must be -1 or a node ID");
		if (forced_spines.find(flow_index) != forced_spines.end())
			ConfigError("duplicate flow_index in " + fixed_path_file);
		forced_spines[flow_index] = spine_id;
	}
	if (!input.eof())
		ConfigError("malformed entry in " + fixed_path_file);
}

void RegisterMonitoredPort(Ptr<SwitchNode> sw, Ptr<Node> peer, uint32_t out_if){
	pair<uint32_t, uint32_t> key(sw->GetId(), out_if);
	if (monitored_ports.insert(key).second){
		monitored_port_peers[key] = peer->GetId();
		monitored_last_tx[key] = sw->GetTxBytes(out_if);
		monitored_last_time[key] = Simulator::Now().GetTimeStep();
	}
}

void InstallFixedPath(uint32_t flow_index, const FlowInput &flow, uint16_t sport){
	auto forced = forced_spines.find(flow_index);
	if (forced == forced_spines.end() || forced->second == -1)
		return;
	uint32_t spine_id = forced->second;
	if (spine_id >= n.GetN() || n.Get(spine_id)->GetNodeType() != 1)
		ConfigError("forced_spine_id is not a switch node");

	Ptr<Node> src_host = n.Get(flow.src);
	Ptr<Node> dst_host = n.Get(flow.dst);
	Ptr<Node> src_leaf;
	for (auto link : nbr2if[src_host]){
		if (link.second.up && link.first->GetNodeType() == 1){
			if (src_leaf != 0)
				ConfigError("source host has more than one attached switch");
			src_leaf = link.first;
		}
	}
	if (src_leaf == 0)
		ConfigError("source host has no attached leaf switch");

	auto node_routes = nextHop.find(src_leaf);
	if (node_routes == nextHop.end())
		ConfigError("source leaf has no routing table");
	auto destination_route = node_routes->second.find(dst_host);
	if (destination_route == node_routes->second.end())
		ConfigError("source leaf has no route to destination host");

	Ptr<Node> spine = n.Get(spine_id);
	bool legal_candidate = false;
	for (Ptr<Node> candidate : destination_route->second){
		if (candidate->GetNodeType() == 1){
			auto link = nbr2if[src_leaf].find(candidate);
			if (link != nbr2if[src_leaf].end() && link->second.up)
				RegisterMonitoredPort(DynamicCast<SwitchNode>(src_leaf), candidate, link->second.idx);
		}
		if (candidate == spine)
			legal_candidate = true;
	}
	if (!legal_candidate)
		ConfigError("forced spine is not a legal ECMP next hop");

	auto link = nbr2if[src_leaf].find(spine);
	if (link == nbr2if[src_leaf].end() || !link->second.up)
		ConfigError("source leaf is not connected to forced spine");
	uint32_t out_if = link->second.idx;
	Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(src_leaf);
	if (!sw->AddFixedPathEntry(serverAddress[flow.src], serverAddress[flow.dst], sport, flow.dport, out_if))
		ConfigError("fixed out_if is absent from destination ECMP route");

	if (fixed_path_output != NULL){
		fprintf(fixed_path_output, "%u %u %u %u %u %u %u %u %.9f\n",
			flow_index, flow.src, flow.dst, sport, flow.dport,
			src_leaf->GetId(), spine_id, out_if, flow.start_time);
		fflush(fixed_path_output);
	}
}

void MonitorFixedPathPorts(){
	uint64_t now = Simulator::Now().GetTimeStep();
	for (auto key : monitored_ports){
		Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(key.first));
		uint64_t tx = sw->GetTxBytes(key.second);
		uint64_t delta = tx - monitored_last_tx[key];
		uint64_t elapsed = now - monitored_last_time[key];
		uint64_t throughput = elapsed == 0 ? 0 : delta * 8000000000lu / elapsed;
		Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(key.second));
		fprintf(port_monitor_output, "%lu %u %u %u %lu %lu %u\n", now, key.first,
			monitored_port_peers[key], key.second, delta, throughput, dev->GetQueue()->GetNBytesTotal());
		monitored_last_tx[key] = tx;
		monitored_last_time[key] = now;
	}
	fflush(port_monitor_output);
	Simulator::Schedule(NanoSeconds(port_monitor_interval), &MonitorFixedPathPorts);
}

void ReadFlowInput(){
	if (flow_input.idx < flow_num){
		flowf >> flow_input.src >> flow_input.dst >> flow_input.pg >> flow_input.dport >> flow_input.maxPacketCount >> flow_input.start_time;
		NS_ASSERT(n.Get(flow_input.src)->GetNodeType() == 0 && n.Get(flow_input.dst)->GetNodeType() == 0);
	}
}//读取flow.txt文件中的flow特征
// TEMPORARY (scheme1_sba S1 validation only): applies a fixed
// application-layer rate cap, independent of any CC decision.
// Simulator::Schedule needs a free function (this codebase predates
// lambda support in its Schedule overloads).
void ApplyBackgroundRateCap(uint32_t src, uint32_t dip, uint16_t sport, uint16_t pg){
	Ptr<RdmaDriver> driver = n.Get(src)->GetObject<RdmaDriver>();
	Ptr<RdmaQueuePair> qp = driver->m_rdma->GetQp(dip, sport, pg);
	NS_ASSERT_MSG(qp, "background flow QP not found for cap");
	qp->m_appRateCapBps = UINT64_C(8000000000);
}

void ScheduleFlowInputs(){//开始规划流
	while (flow_input.idx < flow_num && Seconds(flow_input.start_time) == Simulator::Now()){//开始执行流
		uint32_t port = portNumder[flow_input.src][flow_input.dst]++; // get a new port number
		ExperimentFlow ff; ff.id=flow_input.idx;ff.src=flow_input.src;ff.dst=flow_input.dst;ff.pg=flow_input.pg;
		ff.sport=port;ff.dport=flow_input.dport;ff.size=flow_input.maxPacketCount;ff.start=flow_input.start_time;
		experiment_flows.push_back(ff);
		InstallFixedPath(flow_input.idx, flow_input, port);
		if (round_mode){
			auto schedule = round_schedules.find(flow_input.idx);
			if (schedule == round_schedules.end())
				ConfigError("missing round schedule for flow");
			uint64_t total = 0;
			for (uint32_t i = 0; i < schedule->second.size(); ++i)
				total += schedule->second[i].roundBytes;
			if (total != flow_input.maxPacketCount)
				ConfigError("flow total size differs from round byte sum");
			BopFinalValidation::RegisterFlow(flow_input.idx,
				serverAddress[flow_input.src].Get(),
				serverAddress[flow_input.dst].Get(), port,
				flow_input.dport, flow_input.pg, schedule->second);
				Ptr<RdmaDriver> driver =
					n.Get(flow_input.src)->GetObject<RdmaDriver>();
			driver->m_rdma->RegisterRoundSchedule(
				serverAddress[flow_input.dst].Get(), port, flow_input.pg,
				flow_input.idx, schedule->second);
		}
		RdmaClientHelper clientHelper(flow_input.pg, serverAddress[flow_input.src], serverAddress[flow_input.dst], port, flow_input.dport, flow_input.maxPacketCount, has_win?(global_t==1?maxBdp:pairBdp[n.Get(flow_input.src)][n.Get(flow_input.dst)]):0, global_t==1?maxRtt:pairRtt[flow_input.src][flow_input.dst]);
		//这个里面传输的参数就是client的一些特征，pg是优先级组，maxPacketCoun是发送出去的总字节，其他的好理解
		ApplicationContainer appCon = clientHelper.Install(n.Get(flow_input.src));//在install后会在源host上建立一个QP（怎么建立的可以去看文件rdma-client.cc中的void RdmaClient）
		appCon.Start(Time(0));

		// TEMPORARY (scheme1_sba S1 validation only): hard-code an
		// 8Gbps application rate cap on flow 0, the background flow.
		// This proves out RdmaHw::ChangeRate/UpdateNextAvail's new
		// m_appRateCapBps clamp before a real flow-file column exists.
		if (flow_input.idx == 0){
			uint32_t capSrc = flow_input.src;
			uint32_t capDip = serverAddress[flow_input.dst].Get();
			uint16_t capSport = port;
			uint16_t capPg = flow_input.pg;
			Simulator::Schedule(NanoSeconds(1), &ApplyBackgroundRateCap, capSrc, capDip, capSport, capPg);
		}

		// get the next flow input
		flow_input.idx++;
		ReadFlowInput();//也就是说按仿真时间一条条启动，不是一次性启动的
	}

	// schedule the next time to run this function
	if (flow_input.idx < flow_num){
		Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
	}else { // no more flows, close the file
		flowf.close();
	}
}

Ipv4Address node_id_to_ip(uint32_t id){
	return Ipv4Address(0x0b000001 + ((id / 256) * 0x00010000) + ((id % 256) * 0x00000100));
}

uint32_t ip_to_node_id(Ipv4Address ip){
	return (ip.Get() >> 8) & 0xffff;
}

void qp_finish(FILE* fout, Ptr<RdmaQueuePair> q){//一条流/QP发完之后的收尾回调，记录FCT,写结果，清除状态
	uint32_t sid = ip_to_node_id(q->sip), did = ip_to_node_id(q->dip);//从QP的五元组IP反查node ip/一个源节点一个目标节点
	uint64_t base_rtt = pairRtt[sid][did], b = pairBw[sid][did];//第一个base_rtt是这对host的无拥塞往返时延；第二b是路径瓶颈带宽
	uint32_t total_bytes = q->m_size + ((q->m_size-1) / packet_payload_size + 1) * (CustomHeader::GetStaticWholeHeaderSize() - IntHeader::GetStaticSize()); // translate to the minimum bytes required (with header but no INT)
	//m_size为流大小，total_bytes是理想FCT下线上总字节数：payload总大小+头部开销大小（去掉Int(HPCC算法本身在头部添加的)，向上取整
	uint64_t standalone_fct = base_rtt + total_bytes * 8000000000lu / b;
	//理想状态下的FCT（即无排队，无拥塞）
	// sip, dip, sport, dport, size (B), start_time, fct (ns), standalone_fct (ns)
	fprintf(fout, "%08x %08x %u %u %lu %lu %lu %lu\n", q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->m_size, q->startTime.GetTimeStep(), (Simulator::Now() - q->startTime).GetTimeStep(), standalone_fct);
	fflush(fout);
	for(size_t i=0;i<experiment_flows.size();i++) if(experiment_flows[i].sport==q->sport &&
		experiment_flows[i].src==sid && experiment_flows[i].dst==did){
		experiment_flows[i].completed=true;
		experiment_flows[i].qp=q;
		experiment_flows[i].finish=Simulator::Now().GetSeconds();
		if(flow_summary_csv){
			double st=q->crfm.enabled ?
				q->crfm.rounds.front().releaseTimeNs*1e-9 :
				q->startTime.GetSeconds();
			if ((cc_mode == RdmaHw::CC_MODE_CBAP_FULL_SCOPED ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
					cc_mode == RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
					cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC ||
					cc_mode == RdmaHw::CC_MODE_CBAP_SBA_DCQCN) &&
					q->crfm.enabled){
				uint64_t applicationReadyNs = 0;
				if (RdmaHw::GetCbapScopeApplicationReadyNs(
						q->crfm.rounds.front().roundGroupId,
						applicationReadyNs))
					st = applicationReadyNs * 1e-9;
			}
			double fin=Simulator::Now().GetSeconds(),fct=fin-st;
			fprintf(flow_summary_csv,"%s,%s,%u,%u,%08x-%08x-%u-%u,%u,%u,%lu,%.9f,%.9f,%.9f,%lu,1,%.3f\n",
				scenario_name.c_str(),algorithm_name.c_str(),sim_seed,experiment_flows[i].id,
				q->sip.Get(),q->dip.Get(),q->sport,q->m_pg,sid,did,q->m_size,
				st,fin,fct,q->snd_una,q->m_size*8.0/fct);
			fflush(flow_summary_csv);
		}
		break;
	}
	//清空文件

	// remove rxQp from the receiver
	Ptr<Node> dstNode = n.Get(did);
	Ptr<RdmaDriver> rdma = dstNode->GetObject<RdmaDriver> ();//创建对端dstnode对象指针
	rdma->m_rdma->DeleteRxQp(q->sip.Get(), q->m_pg, q->sport);//删除对端该QP的状态信息
}

const char *BopFallbackName(uint32_t value){
	switch (value){
	case RdmaHw::BOP_FALLBACK_NONE: return "none";
	case RdmaHw::BOP_FALLBACK_INITIAL_QUEUE_ZERO:
		return "first_round_queue_zero";
	case RdmaHw::BOP_FALLBACK_NO_VALID_TELEMETRY:
		return "no_valid_telemetry_queue_zero";
	case RdmaHw::BOP_FALLBACK_NOT_BOP: return "not_bop";
	default: return "unknown";
	}
}

const char *BopQcTauSourceName(uint32_t value){
	switch (value){
	case RdmaHw::BOP_QC_TAU_DEFAULT: return "default";
	case RdmaHw::BOP_QC_TAU_EWMA: return "int_feedback_ewma";
	default: return "not_qc";
	}
}

string BopQcFallbackName(uint32_t value){
	if (value == RdmaHw::BOP_QC_FALLBACK_NONE)
		return "none";
	if (value & RdmaHw::BOP_QC_FALLBACK_NOT_QC)
		return "not_qc";
	string result;
	if (value & RdmaHw::BOP_QC_FALLBACK_FIRST_ROUND)
		result = "first_round";
	if (value & RdmaHw::BOP_QC_FALLBACK_NO_QUEUE)
		result += (result.empty() ? "" : "+") +
			string("queue_zero_no_prior_int");
	if (value & RdmaHw::BOP_QC_FALLBACK_DEFAULT_TAU)
		result += (result.empty() ? "" : "+") +
			string("default_tau_no_ewma");
	return result.empty() ? "unknown" : result;
}

string BopQbFallbackName(uint32_t value){
	if (value == RdmaHw::BOP_QB_FALLBACK_NONE)
		return "none";
	if (value & RdmaHw::BOP_QB_FALLBACK_NOT_QB)
		return "not_qb";
	string result;
	if (value & RdmaHw::BOP_QB_FALLBACK_FIRST_ROUND)
		result = "first_round";
	if (value & RdmaHw::BOP_QB_FALLBACK_NO_QUEUE)
		result += (result.empty() ? "" : "+") +
			string("queue_zero_no_prior_int");
	return result.empty() ? "unknown" : result;
}

const char *BopQbMaxFallbackName(uint32_t value){
	switch (value){
	case RdmaHw::BOP_QB_MAX_FALLBACK_NONE:
		return "none";
	case RdmaHw::BOP_QB_MAX_FALLBACK_NO_PRE_RELEASE_QUEUE:
		return "no_valid_pre_release_queue";
	case RdmaHw::BOP_QB_MAX_FALLBACK_NOT_QB_MAX:
		return "not_qb_max";
	default:
		return "unknown";
	}
}

void WriteCrfmSummaries(){
	set<uint32_t> writtenGroups;
	for (size_t i = 0; i < experiment_flows.size(); ++i){
		ExperimentFlow &flow = experiment_flows[i];
		Ptr<RdmaQueuePair> q = FindExperimentQp(flow);
		if (!q || !q->crfm.enabled)
			continue;
		if (q->crfm.currentRoundIndex >= 0)
			q->crfm.rounds[q->crfm.currentRoundIndex].endRate =
				q->m_rate.GetBitRate();
		double startRateSum = 0;
		for (uint32_t r = 0; r < q->crfm.rounds.size(); ++r){
			RdmaQueuePair::CrfmRoundState &round = q->crfm.rounds[r];
			startRateSum += round.startRate;
			double release = round.releaseTimeNs * 1e-9;
			double injection = round.injectionEndTimeNs ?
				round.injectionEndTimeNs * 1e-9 : 0;
			double completion = round.ackCompletionTimeNs ?
				round.ackCompletionTimeNs * 1e-9 : 0;
			uint64_t accountingReleaseNs = round.releaseTimeNs;
			if (cc_mode == RdmaHw::CC_MODE_CBAP_FULL_SCOPED ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
					cc_mode == RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
					cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ||
					cc_mode ==
						RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC ||
					cc_mode == RdmaHw::CC_MODE_CBAP_SBA_DCQCN){
				uint64_t applicationReadyNs = 0;
				if (RdmaHw::GetCbapScopeApplicationReadyNs(
						round.roundGroupId, applicationReadyNs))
					accountingReleaseNs = applicationReadyNs;
			}
			double rct = round.ackCompletionTimeNs ?
				(round.ackCompletionTimeNs-accountingReleaseNs)*1e-9 : 0;
			double loop = round.firstFeedbackTimeNs ?
				(round.firstFeedbackTimeNs-round.releaseTimeNs)*1e-9 : 0;
			uint32_t firstAfterInjection =
				round.firstFeedbackTimeNs && round.injectionEndTimeNs &&
				round.firstFeedbackTimeNs >= round.injectionEndTimeNs;
			fprintf(round_summary_csv,
				"%s,%s,%u,%u,%08x-%08x-%u-%u,%u,%u,%u,%.9f,%.9f,%.9f,%.9f,%lu,%lu,%lu,%lu,%lu,%.9f,%u,%lu,%lu,%lu,%lu,%.9f,%.9f,%u,%u\n",
				scenario_name.c_str(),algorithm_name.c_str(),sim_seed,
				flow.id,q->sip.Get(),q->dip.Get(),q->sport,q->m_pg,
				round.roundId,round.roundGroupId,round.participantCount,
				release,injection,completion,rct,
				round.roundBytes,round.startRate,round.minimumRate,
				round.endRate,round.nextRoundStartRate,loop,
				firstAfterInjection,round.selectedLinkPeakQueue,
				round.startSeq,round.endSeq,round.cnpCount,
				round.dcqcnStartAlpha,round.dcqcnEndAlpha,
				round.dcqcnStartRecoveryStage,
				round.dcqcnEndRecoveryStage);

			double meanRemaining = round.totalFeedback ?
				round.remainingUnsentRatioSum/round.totalFeedback : 0;
			double minRemaining = round.totalFeedback ?
				round.minimumRemainingUnsentRatio : 0;
			double meanRemainingBytes = round.totalFeedback ?
				(double)round.remainingUnsentBytesSum/
				round.totalFeedback : 0;
			uint64_t minRemainingBytes = round.totalFeedback ?
				round.minimumRemainingUnsentBytes : 0;
			double meanLoad = round.normalizedLoadSamples ?
				round.normalizedLoadSum/round.normalizedLoadSamples : 0;
			double lateActionRatio = round.totalFeedback ?
				(double)round.liveRateChangesDuringOff/
				round.totalFeedback : 0;
			fprintf(feedback_summary_csv,
				"%u,%u,%lu,%u,%lu,%lu,%lu,%lu,%lu,%.9f,%.9f,%.9f,%.9f,%.3f,%lu,%.9f,%.9f,%lu,%lu,%lu,%.9f,%.9f\n",
				flow.id,round.roundId,round.totalFeedback,
				round.feedbackBaselineHops,
				round.actionableFeedback,round.lateSameRoundFeedback,
				round.staleOlderRoundFeedback,round.feedbackDuringOff,
				round.liveRateChangesDuringOff,
				round.firstFeedbackTimeNs*1e-9,
				round.lastFeedbackTimeNs*1e-9,
				meanRemaining,minRemaining,meanRemainingBytes,
				minRemainingBytes,round.maximumNormalizedLoad,
				meanLoad,
				round.firstFeedbackRateBefore,round.lastFeedbackRateAfter,
				round.feedbackChangedLiveRate,lateActionRatio,
				meanRemaining);

					if (cc_mode == RdmaHw::CC_MODE_BOP_QC)
						fprintf(flow_plan_csv,
						"%u,%u,%u,%lu,%lu,%lu,%lu,%s,%lu,%lu,%lu,%lu,%u,%lu\n",
						flow.id,round.roundGroupId,round.roundId,
						round.roundBytes,round.bopSelectedRateBps,
						round.bopMaxRateBps,round.bopPhaseOffsetNs,
						round_selected_link_ids.c_str(),
						round.bopQcBaseRateBps,round.bopQcCreditBytes,
						round.bopQcCreditEndSeq,
							round.bopQcBurstRateBps,
							round.bopQcSwitchedToBase ? 1 : 0,
							round.bopQcActualBurstBytes);
					else if (RdmaHw::UsesBopQbCredit(cc_mode))
						fprintf(flow_plan_csv,
							"%u,%u,%u,%lu,%lu,%lu,%lu,%s,%lu,%lu,%lu,%lu,%u,%lu\n",
							flow.id,round.roundGroupId,round.roundId,
							round.roundBytes,round.bopSelectedRateBps,
							round.bopMaxRateBps,round.bopPhaseOffsetNs,
							round_selected_link_ids.c_str(),
							round.bopQbBaseRateBps,round.bopQbCreditBytes,
							round.bopQbCreditEndSeq,
							round.bopQbBurstRateBps,
							round.bopQbSwitchedToBase ? 1 : 0,
							round.bopQbActualBurstBytes);
					else if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX)
						fprintf(flow_plan_csv,
							"%u,%u,%u,%lu,%lu,%lu,%lu,%s,%lu,%lu,%lu,%lu,%lu,%u\n",
							flow.id,round.roundGroupId,round.roundId,
							round.roundBytes,round.bopSelectedRateBps,
							round.bopMaxRateBps,round.bopPhaseOffsetNs,
							round_selected_link_ids.c_str(),
							round.bopQbMaxBaseRateBps,
							round.bopQbMaxCreditBytes,
							round.bopQbMaxCreditEndSeq,
							round.bopQbMaxBurstRateBps,
							round.bopQbMaxActualBurstBytes,
							round.bopQbMaxSwitchedToBase ? 1 : 0);
					else
					fprintf(flow_plan_csv,
						"%u,%u,%u,%lu,%lu,%lu,%lu,%s\n",
						flow.id,round.roundGroupId,round.roundId,
						round.roundBytes,round.bopSelectedRateBps,
						round.bopMaxRateBps,round.bopPhaseOffsetNs,
						round_selected_link_ids.c_str());
				if (writtenGroups.insert(round.roundGroupId).second){
				uint64_t totalBytes = 0;
				for (size_t j = 0; j < experiment_flows.size(); ++j){
					Ptr<RdmaQueuePair> member =
						FindExperimentQp(experiment_flows[j]);
					if (!member || r >= member->crfm.rounds.size())
						continue;
					RdmaQueuePair::CrfmRoundState &candidate =
						member->crfm.rounds[r];
					if (candidate.roundGroupId == round.roundGroupId)
						totalBytes += candidate.roundBytes;
				}
				double groupRct = round.barrierCompletionTimeNs >
					round.commonReleaseTimeNs ?
					(round.barrierCompletionTimeNs -
					 round.commonReleaseTimeNs) * 1e-9 : 0;
				double efficiency = groupRct > 0 ?
					round.bopTStarSeconds / groupRct : 0;
					fprintf(group_round_summary_csv,
					"%s,%s,%u,%u,%u,%.9f,%.9f,%.9f,%lu,%u,%lu,%lu,%lu,%.9f,%.9f,%.9f,%.9f,%.9f,%lu,%lu,%lu,%s\n",
					scenario_name.c_str(),algorithm_name.c_str(),sim_seed,
					round.roundGroupId,round.roundId,
					round.commonReleaseTimeNs*1e-9,
					round.barrierCompletionTimeNs*1e-9,groupRct,
					totalBytes,round.participantCount,
					round.bopResidualQueueBytes,round.bopBottleneckBps,
					round.bopBackgroundBps,round.bopTLineSeconds,
					round.bopTLinkSeconds,round.bopTStarSeconds,
					round.bopTStarSeconds,efficiency,
					round.groupQueueMaxBytes,round.groupEcnMarks,
						round.groupPfcEvents,
						BopFallbackName(round.bopFallbackReason));
					if (bop_qc_group_decisions_csv &&
							cc_mode == RdmaHw::CC_MODE_BOP_QC){
						string fallback =
							BopQcFallbackName(
								round.bopQcFallbackReason);
						fprintf(bop_qc_group_decisions_csv,
							"%s,%u,%u,%u,%lu,%u,%lu,%.6f,%.6f,%s,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.6f,%s\n",
							scenario_name.c_str(),sim_seed,
							round.roundGroupId,round.roundId,totalBytes,
							round.participantCount,
							round.bopResidualQueueBytes,
							round.bopQcQueueSampleAgeUs,
							round.bopQcFeedbackTauUs,
							BopQcTauSourceName(
								round.bopQcTauSource),
							round.bopBottleneckBps,
							round.bopBackgroundBps,
							round.bopQcEcnThresholdBytes,
							round.bopQcPacketMarginBytes,
							round.bopQcQueueRoomBytes,
							round.bopQcBdpCreditBytes,
							round.bopQcGroupCreditBytes,
							round.bopQcTotalAllocatedCreditBytes,
							round.bopTStarSeconds * 1e6,
							fallback.c_str());
					}
					if (bop_qb_group_decisions_csv &&
							RdmaHw::UsesBopQbCredit(cc_mode)){
						string fallback =
							BopQbFallbackName(
								round.bopQbFallbackReason);
						fprintf(bop_qb_group_decisions_csv,
							"%s,%u,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%.6f,%s,%u\n",
							scenario_name.c_str(),sim_seed,
							round.roundGroupId,round.roundId,
							round.participantCount,totalBytes,
							round.bopResidualQueueBytes,
							round.bopQbEcnThresholdBytes,
							round.bopQbQueueTargetBytes,
							round.bopQbPacketMarginBytes,
							round.bopQbQueueRoomBytes,
							round.bopQbGroupCreditBytes,
							round.bopQbTotalAllocatedCreditBytes,
							round.bopTStarSeconds * 1e6,
							fallback.c_str(),
							round.bopQbSafetyBoundValid ? 1 : 0);
					}
					if (cc_mode == RdmaHw::CC_MODE_BOP_QB_PRT &&
							(final_primer_first_flow ==
							 std::numeric_limits<uint32_t>::max() ||
							 flow.id < final_primer_first_flow) &&
							prt_probe_summary_csv){
						fprintf(prt_probe_summary_csv,
							"%s,%u,%u,%u,1,%lu,%lu,%lu,%lu,%u,%u,%lu,%lu,%.9f,%lu,%lu,%ld,%u\n",
							scenario_name.c_str(),sim_seed,
							round.roundGroupId,round.roundId,
							round.prtProbe1SendNs,
							round.prtProbe1QueueSampleNs,
							round.prtProbe1AckNs,
							round.prtDecisionReleaseNs,
							round.prtProbeCountSent,
							round.prtProbeReturnedBeforeRelease,
							round.prtProbe1QueueBytes,
							round.prtProbe2QueueBytes,
							round.prtQueueSlopeBytesPerNs,
							round.prtQueueHatBytes,
							round.prtActualQueueBytes,
							round.prtQueueErrorBytes,
							round.prtFallbackReason);
						if (round.prtProbeCountSent > 1)
							fprintf(prt_probe_summary_csv,
								"%s,%u,%u,%u,2,%lu,%lu,%lu,%lu,%u,%u,%lu,%lu,%.9f,%lu,%lu,%ld,%u\n",
								scenario_name.c_str(),sim_seed,
								round.roundGroupId,round.roundId,
								round.prtProbe2SendNs,
								round.prtProbe2QueueSampleNs,
								round.prtProbe2AckNs,
								round.prtDecisionReleaseNs,
								round.prtProbeCountSent,
								round.prtProbeReturnedBeforeRelease,
								round.prtProbe1QueueBytes,
								round.prtProbe2QueueBytes,
								round.prtQueueSlopeBytesPerNs,
								round.prtQueueHatBytes,
								round.prtActualQueueBytes,
								round.prtQueueErrorBytes,
								round.prtFallbackReason);
					}
					if (cc_mode == RdmaHw::CC_MODE_BOP_QB_PRT &&
							(final_primer_first_flow ==
							 std::numeric_limits<uint32_t>::max() ||
							 flow.id < final_primer_first_flow) &&
							prt_group_decisions_csv)
						fprintf(prt_group_decisions_csv,
							"%s,%u,%u,%u,%u,%lu,%u,%u,%lu,%lu,%ld,%u,%lu,%lu,%lu,%lu,%lu,%s,%lu,%lu,%lu,%u\n",
							scenario_name.c_str(),sim_seed,
							round.roundGroupId,round.roundId,
							round.participantCount,totalBytes,
							round.prtProbeCountSent,
							round.prtProbeReturnedBeforeRelease,
							round.prtQueueHatBytes,
							round.prtActualQueueBytes,
							round.prtQueueErrorBytes,
							round.prtFallbackReason,
							round.prtOriginalBopCreditBytes,
							round.prtCreditBytes,
							round.bopQbQueueTargetBytes,
							round.bopQbPacketMarginBytes,
							round.groupQueueMaxBytes,
							"post_release_residual_work",
							round.prtPrimerEcn,
							round.prtCollectiveEcn,
							round.groupPfcEvents,
							round.bopQbSafetyBoundValid ? 1 : 0);
					if (bop_qb_max_group_decisions_csv &&
							cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX){
						fprintf(bop_qb_max_group_decisions_csv,
							"%s,%u,%u,%u,%u,%lu,%lu,%.9f,%.6f,%lu,%lu,%lu,%lu,%lu,%.6f,%u,%s\n",
							scenario_name.c_str(),sim_seed,
							round.roundGroupId,round.roundId,
							round.participantCount,totalBytes,
							round.bopResidualQueueBytes,
							round.bopQbMaxQueueSampleTimeNs * 1e-9,
							round.bopQbMaxQueueSampleAgeUs,
							round.bopQbMaxEcnThresholdBytes,
							round.bopQbMaxPacketMarginBytes,
							round.bopQbMaxQueueRoomBytes,
							round.bopQbMaxGroupCreditBytes,
							round.bopQbMaxTotalAllocatedCreditBytes,
							round.bopTStarSeconds * 1e6,
							round.bopQbMaxSafetyBoundValid ? 1 : 0,
							BopQbMaxFallbackName(
								round.bopQbMaxFallbackReason));
					}
				}
		}
		double meanStart = q->crfm.rounds.empty() ? 0 :
			startRateSum/q->crfm.rounds.size();
		fprintf(controller_summary_csv,
			"%u,%08x-%08x-%u-%u,%lu,%lu,%lu,%lu,%.3f,%lu,%lu,%.3f\n",
			flow.id,q->sip.Get(),q->dip.Get(),q->sport,q->m_pg,
			(unsigned long)q->crfm.rounds.size(),
			q->crfm.directHpccUpdates,q->crfm.gatedLateUpdates,
			q->crfm.gatedStaleUpdates,q->crfm.rateTotalVariation,
			q->crfm.minimumRate,q->crfm.maximumRate,meanStart);
	}
	fflush(round_summary_csv);
	fflush(feedback_summary_csv);
	fflush(controller_summary_csv);
		fflush(group_round_summary_csv);
		fflush(flow_plan_csv);
		if (bop_qc_group_decisions_csv)
			fflush(bop_qc_group_decisions_csv);
		if (bop_qb_group_decisions_csv)
			fflush(bop_qb_group_decisions_csv);
		if (bop_qb_max_group_decisions_csv)
			fflush(bop_qb_max_group_decisions_csv);
		}

void WriteBopMultilinkSummaries(){
	if (!bop_multilink_enable)
		return;
	if (bop_multilink_group_decisions_csv){
		const vector<RdmaHw::BopMultilinkGroupDecision> &groups =
			RdmaHw::GetBopMultilinkGroupDecisions();
		for (uint32_t i = 0; i < groups.size(); ++i){
			const RdmaHw::BopMultilinkGroupDecision &row = groups[i];
			fprintf(bop_multilink_group_decisions_csv,
				"%s,%s,%u,%u,%u,%u,%lu,%.12f,%.9f,%u,%u,%u,%u\n",
				scenario_name.c_str(), algorithm_name.c_str(), sim_seed,
				row.groupId, row.roundIndex, row.participantCount,
				row.totalRoundBytes, row.alpha,
				row.tStarSeconds * 1e6, row.limitingLinkCount,
				row.formulaValid ? 1 : 0,
				row.capacityValid ? 1 : 0,
				row.creditConstraintValid ? 1 : 0);
		}
		fflush(bop_multilink_group_decisions_csv);
	}
	if (bop_multilink_link_constraints_csv){
		const vector<RdmaHw::BopMultilinkLinkDecision> &links =
			RdmaHw::GetBopMultilinkLinkDecisions();
		for (uint32_t i = 0; i < links.size(); ++i){
			const RdmaHw::BopMultilinkLinkDecision &row = links[i];
			fprintf(bop_multilink_link_constraints_csv,
				"%s,%s,%u,%u,%u,%u,%lu,%lu,%lu,%u,%lu,%lu,%lu,%.9f,%u,%.9f,%u,%u,%u\n",
				scenario_name.c_str(), algorithm_name.c_str(), sim_seed,
				row.groupId, row.roundIndex, row.linkId,
				row.capacityBps, row.queueBytes, row.ecnThresholdBytes,
				row.flowCount, row.workloadBytes, row.queueRoomBytes,
				row.creditSumBytes, row.tLinkSeconds * 1e6,
				row.limitingLink ? 1 : 0, row.tStarSeconds * 1e6,
				row.formulaValid ? 1 : 0,
				row.capacityValid ? 1 : 0,
				row.creditConstraintValid ? 1 : 0);
		}
		fflush(bop_multilink_link_constraints_csv);
	}
}

void WriteFinalReleaseQueueSummary(){
	if (!final_validation_enable)
		return;
	FILE *output = fopen(final_release_queue_file.c_str(), "w");
	if (!output)
		ConfigError("cannot open RELEASE_QUEUE_SUMMARY_FILE");
	fprintf(output,
		"scenario,algorithm,seed,group_id,round_id,"
		"actual_queue_at_release_bytes,estimated_q0_bytes,"
		"q0_error_bytes,q0_error_ratio,queue_sample_age_us,"
		"queue_sample_origin,group_credit_bytes,queue_target_bytes,"
		"actual_queue_max_bytes,ECN,PFC,"
		"safety_bound_using_estimate,safety_bound_using_actual\n");
	set<uint32_t> written;
	for (size_t index = 0; index < experiment_flows.size(); ++index){
		ExperimentFlow &flow = experiment_flows[index];
		if (flow.id >= final_collective_flow_count)
			continue;
		Ptr<RdmaQueuePair> qp = FindExperimentQp(flow);
		if (!qp)
			continue;
		for (uint32_t roundIndex = 0;
				roundIndex < qp->crfm.rounds.size(); ++roundIndex){
			RdmaQueuePair::CrfmRoundState &round =
				qp->crfm.rounds[roundIndex];
			if (!written.insert(round.roundGroupId).second)
				continue;
			fprintf(output,
				"%s,%s,%u,%u,%u,%lu,%lu,%ld,%.9f,%.6f,%s,"
				"%lu,%lu,%lu,%lu,%lu,%u,%u\n",
				scenario_name.c_str(), algorithm_name.c_str(), sim_seed,
				round.roundGroupId, round.roundId,
				round.bopQbActualQueueBytes,
				round.bopQbEstimatedQueueBytes,
				round.bopQbQueueErrorBytes,
				round.bopQbQueueErrorRatio,
				round.bopQbQueueSampleAgeUs,
				BopQ0OriginName(round.bopQbQueueSampleOrigin),
				round.bopQbGroupCreditBytes,
				round.bopQbQueueTargetBytes,
				round.groupQueueMaxBytes, round.groupEcnMarks,
				round.groupPfcEvents,
				round.bopQbSafetyBoundValid ? 1 : 0,
				round.bopQbSafetyBoundUsingActual ? 1 : 0);
		}
	}
	fclose(output);
}

void get_pfc(FILE* fout, Ptr<QbbNetDevice> dev, uint32_t q_index, uint32_t type){
	uint64_t key=((uint64_t)dev->GetNode()->GetId()<<32) |
		((uint64_t)dev->GetIfIndex()<<16) | q_index;
	auto state=pfc_states.find(key);
	uint32_t previous=state==pfc_states.end()?0:state->second;
	if(previous==type)
		return;
	pfc_states[key]=type;
	pfc_total_events++;
	if (pfc_event_rows >= crfm_max_event_rows){
		if (!trace_truncated){
			trace_truncated = true;
			cerr << "LOG_TRUNCATED" << endl;
		}
		return;
	}
	stringstream row;
	row<<Simulator::Now().GetTimeStep()<<","<<dev->GetNode()->GetId()
		<<","<<dev->GetIfIndex()<<","<<q_index<<","<<type<<"\n";
	if (DetailedCsvWrite(fout,
			(uint64_t)crfm_max_trace_file_mb*1024*1024,row.str()))
		pfc_event_rows++;
}//记录PFC事件日志

struct QlenDistribution{
	vector<uint32_t> cnt; // cnt[i] is the number of times that the queue len is i KB

	void add(uint32_t qlen){
		uint32_t kb = qlen / 1000;
		if (cnt.size() < kb+1)
			cnt.resize(kb+1);
		cnt[kb]++;
	}
};//队列长度分布统计，这里传进来的qlen是字节数，然后这个kb就是把字节分桶成KB桶，模拟bucket。
map<uint32_t, map<uint32_t, QlenDistribution> > queue_result;//定义一个全局统计表，即queue_result[交换机ID][端口ID] = 这个端口的队列长度分布统计
void monitor_buffer(FILE* qlen_output, NodeContainer *n){
	for (uint32_t i = 0; i < n->GetN(); i++){
		if (n->Get(i)->GetNodeType() == 1){ // 判断这个node是不是交换机
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n->Get(i));//创建并继承一个交换机节点类的智能指针
			if (queue_result.find(i) == queue_result.end())//检查queue_result中有没有交换机i的记录
				queue_result[i];//如果没有就创建一个
			for (uint32_t j = 1; j < sw->GetNDevices(); j++){//遍历这个交换机上所有的网卡，因为大多数数据网卡都不会放在0上，所以从1开始
				uint32_t size = 0;//统计这个窗口的总排队字节数
				for (uint32_t k = 0; k < SwitchMmu::qCnt; k++)
					size += sw->m_mmu->egress_bytes[j][k];//遍历这个端口所有优先级队列，switchmmu：：qcnt是指的队列数量
				queue_result[i][j].add(size);
			}
		}
	}
	if (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0){//判断是否要将统计结果写入
		fprintf(qlen_output, "time: %lu\n", Simulator::Now().GetTimeStep());
		for (auto &it0 : queue_result)//遍历所有已经统计过的交换机，其中it0.first是交换机id，it0.second是交换机下面的端口map
			for (auto &it1 : it0.second){//遍历这两个交换机的统计
				fprintf(qlen_output, "%u %u", it0.first, it1.first);
				auto &dist = it1.second.cnt;//交换机端口下的长度分布数组
				for (uint32_t i = 0; i < dist.size(); i++)
					fprintf(qlen_output, " %u", dist[i]);
				fprintf(qlen_output, "\n");
			}//再按照bucket写入
		fflush(qlen_output);
	}
	if (Simulator::Now().GetTimeStep() < qlen_mon_end)//这上面说明还没到监控结束时间
		Simulator::Schedule(NanoSeconds(qlen_mon_interval), &monitor_buffer, qlen_output, n);//然后周期性监控
}

void CalculateRoute(Ptr<Node> host){//以host为节点，计算所有节点往这个host的最短路径
	// queue for the BFS.
	vector<Ptr<Node> > q;//队列
	// Distance from the host to each node.
	map<Ptr<Node>, int> dis;//hop
	map<Ptr<Node>, uint64_t> delay;//链路传播延迟
	map<Ptr<Node>, uint64_t> txDelay;//发送延迟
	map<Ptr<Node>, uint64_t> bw;//瓶颈带宽
	// init BFS.
	q.push_back(host);
	dis[host] = 0;
	delay[host] = 0;
	txDelay[host] = 0;
	bw[host] = 0xfffffffffffffffflu;
	// BFS.
	for (int i = 0; i < (int)q.size(); i++){
		Ptr<Node> now = q[i];
		int d = dis[now];
		for (auto it = nbr2if[now].begin(); it != nbr2if[now].end(); it++){
			if (!it->second.up)//如果这个某个邻居节点的端口没有up则跳过
				continue;
			Ptr<Node> next = it->first;//记录下一跳的节点id
			if (dis.find(next) == dis.end()){//如果是第一次访问下一跳；在c++里find函数要是找不到key则会返回end()
				dis[next] = d + 1;//hop + 1
				delay[next] = delay[now] + it->second.delay;//添加链路的传播时延
				txDelay[next] = txDelay[now] + packet_payload_size * 1000000000lu * 8 / it->second.bw;//计算发送时延:数据大小bit/链路速率bit/s
				bw[next] = std::min(bw[now], it->second.bw);//瓶颈带宽
				// we only enqueue switch, because we do not want packets to go through host as middle point
				if (next->GetNodeType() == 1)//也就是说不希望中间的中转节点是host节点，一定得是switch
					q.push_back(next);
			}
			//如果now是next到host的某条最短路径上的下一跳，那就记录：next要去host，可以下一跳走now
			if (d + 1 == dis[next]){
				nextHop[next][host].push_back(now);
			}
		}
	}
		// nextHop[next][host].push_back(now) records that now is a valid
		// next hop for next when routing toward host.
	for (auto it : delay)
		pairDelay[it.first][host] = it.second;
	for (auto it : txDelay)
		pairTxDelay[it.first][host] = it.second;
	for (auto it : bw)
		pairBw[it.first->GetId()][host->GetId()] = it.second;
}//保存本轮的结果

void CalculateRoutes(NodeContainer &n){
	for (int i = 0; i < (int)n.GetN(); i++){
		Ptr<Node> node = n.Get(i);
		if (node->GetNodeType() == 0)
			CalculateRoute(node);
	}
}//遍历所有主机节点

void SetRoutingEntries(){
	//	nextHop[src-node][dst-node] = {nextHop}
	for (auto i = nextHop.begin(); i != nextHop.end(); i++){
		Ptr<Node> node = i->first;//fist指向的是源节点
		auto &table = i->second;//second指向的是dst节点
		for (auto j = table.begin(); j != table.end(); j++){//遍历当前node到所有dst的路由
			Ptr<Node> dst = j->first;//取每一个dst的node
			Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();//接着取ip
			// The next hops towards the dst.
			vector<Ptr<Node> > nexts = j->second;//取下一跳
			for (int k = 0; k < (int)nexts.size(); k++){
				Ptr<Node> next = nexts[k];//遍历每一个下一跳，因为ECMP，所有存在等价路径
				uint32_t interface = nbr2if[node][next].idx;//取得从node到next这条链路中node这一侧的interface即三层接口
				//上面这个的作用就是将下一跳和出发节点的端口绑定
				if (node->GetNodeType() == 1)//如果是交换机则写入交换机路由表，如果host则写入host路由表
					DynamicCast<SwitchNode>(node)->AddTableEntry(dstAddr, interface);
				else{
					node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(dstAddr, interface);
				}
			}
		}
	}
}

// take down the link between a and b, and redo the routing
void TakeDownLink(NodeContainer n, Ptr<Node> a, Ptr<Node> b){
	if (!nbr2if[a][b].up)//如果传入的这两个节点的连接并没有up则返回null
		return;
	// take down link between a and b
	nbr2if[a][b].up = nbr2if[b][a].up = false;//双边链路全部关闭
	nextHop.clear();//清除下一跳关系并重新计算路由
	CalculateRoutes(n);
	for (uint32_t i = 0; i < n.GetN(); i++){//清空所有节点当前以及安装的路由表
		if (n.Get(i)->GetNodeType() == 1)
			DynamicCast<SwitchNode>(n.Get(i))->ClearTable();
		else
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->ClearTable();
	}
	DynamicCast<QbbNetDevice>(a->GetDevice(nbr2if[a][b].idx))->TakeDown();
	DynamicCast<QbbNetDevice>(b->GetDevice(nbr2if[b][a].idx))->TakeDown();//关闭两边的网卡
	// reset routing table
	SetRoutingEntries();//将刚刚新得到的路由表安装到node上

	// redistribute qp on each host
	for (uint32_t i = 0; i < n.GetN(); i++){
		if (n.Get(i)->GetNodeType() == 0)//找到host节点
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->RedistributeQp();
			//重新创造QPQ；在RedistributeQp这个函数中：1.clear了原来每个NIC上的QP分组；2.对原来每一个已有QP重新根据当前QP选择NIC，再加入NIC队列，并通知QP已经重新分配
	}
}

uint64_t get_nic_rate(NodeContainer &n){
	for (uint32_t i = 0; i < n.GetN(); i++)
		if (n.Get(i)->GetNodeType() == 0)//找到主机节点，返回它的device1的链路速率
			return DynamicCast<QbbNetDevice>(n.Get(i)->GetDevice(1))->GetDataRate().GetBitRate();
	return 0;
}

#if 0 // Retired diagnostic source is intentionally outside main_v1.
void SetupShortGapDiagnostics(){
	if (!short_diag_enable)
		return;
	if (scenario_name != "gap_50us" || sim_seed != 1 ||
			!(cc_mode == 1 || cc_mode == RdmaHw::CC_MODE_BOP_QB))
		ConfigError("short-gap diagnostics only support gap_50us seed=1 "
			"with DCQCN or BOP-QB");
	if (!round_mode || selected_link_set.size() != 1)
		ConfigError("short-gap diagnostics require one round bottleneck");
	pair<uint32_t, uint32_t> selected = *selected_link_set.begin();
	if (selected.first != short_diag_bottleneck_node ||
			selected.second != short_diag_bottleneck_if)
		ConfigError("short-gap bottleneck differs from selected link");
	if (short_diag_bottleneck_node >= n.GetN() ||
			n.Get(short_diag_bottleneck_node)->GetNodeType() != 1 ||
			short_diag_bottleneck_if >=
				n.Get(short_diag_bottleneck_node)->GetNDevices())
		ConfigError("short-gap bottleneck device is invalid");
	if (short_diag_max_event_mb == 0 || short_diag_max_event_mb > 16)
		ConfigError("SHORT_DIAG_MAX_EVENT_MB must be in [1,16]");
	if (short_diag_pipeline_file.empty() || short_diag_idle_file.empty() ||
			short_diag_qp_tail_file.empty() || short_diag_meta_file.empty() ||
			short_diag_events_file.empty() ||
			short_diag_topology_sha256.empty() ||
			short_diag_flow_sha256.empty() ||
			short_diag_round_sha256.empty())
		ConfigError("short-gap diagnostics require all outputs and hashes");
	if (cc_mode == RdmaHw::CC_MODE_BOP_QB &&
			std::fabs(bop_qb_queue_fraction - 0.50) > 1e-12)
		ConfigError("short-gap BOP-QB must retain queue fraction 0.5");

	ShortGapPipeline::Config config;
	config.enabled = true;
	config.bottleneckNode = short_diag_bottleneck_node;
	config.bottleneckIf = short_diag_bottleneck_if;
	config.ccMode = cc_mode;
	config.seed = sim_seed;
	config.maxEventBytes =
		(uint64_t)short_diag_max_event_mb * 1024 * 1024;
	config.algorithm = algorithm_name;
	config.scenario = scenario_name;
	config.topologyHash = short_diag_topology_sha256;
	config.flowHash = short_diag_flow_sha256;
	config.roundHash = short_diag_round_sha256;
	config.pipelineFile = short_diag_pipeline_file;
	config.idleFile = short_diag_idle_file;
	config.qpTailFile = short_diag_qp_tail_file;
	config.metaFile = short_diag_meta_file;
	config.eventFile = short_diag_events_file;
	ShortGapPipeline::Configure(config);

	Ptr<QbbNetDevice> bottleneck = DynamicCast<QbbNetDevice>(
		n.Get(short_diag_bottleneck_node)->GetDevice(
			short_diag_bottleneck_if));
	bottleneck->TraceConnectWithoutContext("QbbEnqueue",
		MakeBoundCallback(&ShortGapPipeline::BottleneckEnqueue,
			bottleneck));
	bottleneck->TraceConnectWithoutContext("PhyTxBegin",
		MakeBoundCallback(&ShortGapPipeline::BottleneckTxBegin,
			bottleneck));
	bottleneck->TraceConnectWithoutContext("PhyTxEnd",
		MakeBoundCallback(&ShortGapPipeline::BottleneckTxEnd,
			bottleneck));

	for (uint32_t nodeId = 0; nodeId < n.GetN(); ++nodeId){
		if (n.Get(nodeId)->GetNodeType() != 0)
			continue;
		for (uint32_t deviceId = 1;
				deviceId < n.Get(nodeId)->GetNDevices(); ++deviceId){
			Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(
				n.Get(nodeId)->GetDevice(deviceId));
			if (!device)
				continue;
			device->TraceConnectWithoutContext("RdmaQpDequeue",
				MakeBoundCallback(&ShortGapPipeline::HostQpSend,
					device));
			device->TraceConnectWithoutContext("QbbEnqueue",
				MakeBoundCallback(&ShortGapPipeline::HostEnqueue,
					device));
			device->TraceConnectWithoutContext("MacRx",
				MakeBoundCallback(&ShortGapPipeline::HostMacRx,
					device));
		}
	}
}
#endif

void SetupFinalValidation(){
	if (!final_validation_enable)
		return;
	if (!round_mode || final_collective_flow_count == 0 ||
			final_wire_size_file.empty() ||
			final_release_queue_file.empty())
		ConfigError("final validation requires rounds, collective count, "
			"and both summary outputs");
	if (final_bottleneck_node >= n.GetN() ||
			n.Get(final_bottleneck_node)->GetNodeType() != 1 ||
			final_bottleneck_if >=
				n.Get(final_bottleneck_node)->GetNDevices())
		ConfigError("final-validation bottleneck is invalid");
	if (cc_mode == RdmaHw::CC_MODE_BOP_QB &&
			std::fabs(bop_qb_queue_fraction - 0.50) > 1e-12)
		ConfigError("final BOP-QB queue fraction must remain 0.5");
	if (cc_mode == RdmaHw::CC_MODE_DCQCN_WIRE_EQUALIZED &&
			IntHeader::mode != IntHeader::NONE)
		ConfigError("wire-equalized DCQCN must retain DCQCN INT mode");
	BopFinalValidation::Config config;
	config.enabled = true;
	config.bottleneckNode = final_bottleneck_node;
	config.bottleneckIf = final_bottleneck_if;
	config.collectiveFlowCount = final_collective_flow_count;
	config.packetPayloadBytes = packet_payload_size;
	config.paddingBytes =
		cc_mode == RdmaHw::CC_MODE_DCQCN_WIRE_EQUALIZED ? 42 : 0;
	config.algorithm = algorithm_name;
	config.outputFile = final_wire_size_file;
	BopFinalValidation::Configure(config);
	Ptr<QbbNetDevice> bottleneck = DynamicCast<QbbNetDevice>(
		n.Get(final_bottleneck_node)->GetDevice(final_bottleneck_if));
	bottleneck->TraceConnectWithoutContext("PhyTxBegin",
		MakeBoundCallback(&BopFinalValidation::BottleneckTxBegin,
			bottleneck));
	RdmaHw::SetRoundQueueReadCallback(
		MakeCallback(&ReadFinalValidationQueue));
}

#if 0 // Retired diagnostic source is intentionally outside main_v1.
void SetupPreReleaseAudit(){
	if (!prerelease_audit_enable)
		return;
	if (!final_validation_enable || !round_mode || sim_seed != 1 ||
			!(scenario_name == "residual_64k" ||
			  scenario_name == "residual_160k") ||
			!(cc_mode == RdmaHw::CC_MODE_BOP_QB ||
			  cc_mode == RdmaHw::CC_MODE_BOP_QB_ORACLE_Q0))
		ConfigError("pre-release audit only supports residual_64k/"
			"residual_160k seed=1 with BOP-QB or Oracle-q0");
	if (prerelease_audit_bottleneck_node != final_bottleneck_node ||
			prerelease_audit_bottleneck_if != final_bottleneck_if ||
			prerelease_audit_collective_flow_count !=
				final_collective_flow_count ||
			prerelease_audit_primer_first_flow !=
				final_primer_first_flow)
		ConfigError("pre-release audit identity differs from final validation");
	if (prerelease_audit_primer_first_flow !=
			prerelease_audit_collective_flow_count ||
			prerelease_audit_max_event_mb == 0 ||
			prerelease_audit_max_event_mb > 32)
		ConfigError("invalid pre-release audit primer boundary/event limit");
	if (std::fabs(bop_qb_queue_fraction - 0.50) > 1e-12)
		ConfigError("pre-release audit must retain BOP-QB fraction 0.5");
	if (prerelease_audit_timeline_file.empty() ||
			prerelease_audit_residual_file.empty() ||
			prerelease_audit_queue_file.empty() ||
			prerelease_audit_ecn_file.empty() ||
			prerelease_audit_meta_file.empty() ||
			prerelease_audit_topology_sha256.empty() ||
			prerelease_audit_flow_sha256.empty() ||
			prerelease_audit_round_sha256.empty())
		ConfigError("pre-release audit requires outputs and hashes");
	Ptr<QbbNetDevice> bottleneck = DynamicCast<QbbNetDevice>(
		n.Get(prerelease_audit_bottleneck_node)->GetDevice(
			prerelease_audit_bottleneck_if));
	if (!bottleneck)
		ConfigError("pre-release audit bottleneck is invalid");
	PreReleaseResidualAudit::Config config;
	config.enabled = true;
	config.bottleneckNode = prerelease_audit_bottleneck_node;
	config.bottleneckIf = prerelease_audit_bottleneck_if;
	config.seed = sim_seed;
	config.collectiveFlowCount =
		prerelease_audit_collective_flow_count;
	config.primerFirstFlow = prerelease_audit_primer_first_flow;
	config.maxEventBytes =
		(uint64_t)prerelease_audit_max_event_mb * 1024 * 1024;
	config.scenario = scenario_name;
	config.algorithm = algorithm_name;
	config.topologyHash = prerelease_audit_topology_sha256;
	config.flowHash = prerelease_audit_flow_sha256;
	config.roundHash = prerelease_audit_round_sha256;
	config.timelineFile = prerelease_audit_timeline_file;
	config.residualFile = prerelease_audit_residual_file;
	config.queueFile = prerelease_audit_queue_file;
	config.ecnFile = prerelease_audit_ecn_file;
	config.metaFile = prerelease_audit_meta_file;
	PreReleaseResidualAudit::Configure(config, bottleneck);
	bottleneck->TraceConnectWithoutContext("QbbEnqueue",
		MakeBoundCallback(&PreReleaseResidualAudit::BottleneckEnqueue,
			bottleneck));
	bottleneck->TraceConnectWithoutContext("QbbDequeue",
		MakeBoundCallback(&PreReleaseResidualAudit::BottleneckDequeue,
			bottleneck));
	bottleneck->TraceConnectWithoutContext("PhyTxEnd",
		MakeBoundCallback(&PreReleaseResidualAudit::BottleneckTxEnd,
			bottleneck));
	for (uint32_t nodeId = 0; nodeId < n.GetN(); ++nodeId){
		if (n.Get(nodeId)->GetNodeType() != 0)
			continue;
		for (uint32_t deviceId = 1;
				deviceId < n.Get(nodeId)->GetNDevices(); ++deviceId){
			Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(
				n.Get(nodeId)->GetDevice(deviceId));
			if (device)
				device->TraceConnectWithoutContext("RdmaQpDequeue",
					MakeBoundCallback(
						&PreReleaseResidualAudit::HostSend,
						device));
		}
	}
}
#endif

int main(int argc, char *argv[])
{
	clock_t begint, endt;//记录运行耗时
	begint = clock();
#ifndef PGO_TRAINING
	if (argc > 1)
#else
	if (true)
#endif//判断是否有指定配置文件
	{
		//Read the configuration file
		std::ifstream conf;
#ifndef PGO_TRAINING
		conf.open(argv[1]);
#else
		conf.open(PATH_TO_PGO_CONFIG);
#endif
		while (!conf.eof())//是否文件末尾
		{
			std::string key;
			conf >> key;
			if(key.compare("SIM_SEED")==0) conf>>sim_seed;
			else if(key.compare("PFC_RUNTIME_ENABLE")==0)
				conf>>pfc_runtime_enable;
			else if(key.compare("PFC_SEMANTIC_AUDIT_ENABLE")==0)
				conf>>pfc_semantic_audit_enable;
			else if(key.compare("PFC_AUDIT_NODE")==0)
				conf>>pfc_audit_node;
			else if(key.compare("PFC_AUDIT_IF")==0)
				conf>>pfc_audit_if;
			else if(key.compare("PFC_AUDIT_PRIORITY")==0)
				conf>>pfc_audit_priority;
			else if(key.compare("PFC_EVENT_TRACE_FILE")==0)
				conf>>pfc_event_trace_file;
			else if(key.compare("PFC_SEMANTIC_SUMMARY_FILE")==0)
				conf>>pfc_semantic_summary_file;
			else if(key.compare("CBAP_ENABLE")==0) conf>>cbap_enable;
			else if(key.compare("CBAP_LINK_FILE")==0) conf>>cbap_link_file;
			else if(key.compare("CBAP_PATH_FILE")==0) conf>>cbap_path_file;
			else if(key.compare("CBAP_CONTROL_EPOCH_US")==0)
				conf>>cbap_control_epoch_us;
			else if(key.compare("CBAP_PLANNING_DELAY_US")==0)
				conf>>cbap_planning_delay_us;
			else if(key.compare("CBAP_CONTROL_DELAY_US")==0)
				conf>>cbap_control_delay_us;
			else if(key.compare("CBAP_RHO")==0) conf>>cbap_rho;
			else if(key.compare("CBAP_EPSILON_RATE")==0)
				conf>>cbap_epsilon_rate;
			else if(key.compare("CBAP_PRIORITY")==0)
				conf>>cbap_priority;
			else if(key.compare("CBAP_MAX_WIRE_PACKET_BYTES")==0)
				conf>>cbap_max_wire_packet_bytes;
			else if(key.compare("CBAP_SUMMARY_BYTES")==0)
				conf>>cbap_summary_bytes;
			else if(key.compare("CBAP_GRANT_BYTES")==0)
				conf>>cbap_grant_bytes;
			else if(key.compare("CBAP_PORT_SUMMARY_FILE")==0)
				conf>>cbap_port_summary_file;
			else if(key.compare("CBAP_ADMISSION_FILE")==0)
				conf>>cbap_admission_file;
			else if(key.compare("CBAP_RATE_TRANSITION_FILE")==0)
				conf>>cbap_rate_transition_file;
			else if(key.compare("CBAP_APPLIED_RATE_AUDIT_FILE")==0)
				conf>>cbap_applied_rate_audit_file;
			else if(key.compare("CBAP_INCREASE_AUDIT_FILE")==0)
				conf>>cbap_increase_audit_file;
			else if(key.compare("CBAP_INCREASE_POLICY")==0)
				conf>>cbap_increase_policy;
			else if(key.compare("CBAP_INCREASE_FRACTION")==0)
				conf>>cbap_increase_fraction;
			else if(key.compare("CBAP_INCREASE_ABSOLUTE_BPS")==0)
				conf>>cbap_increase_absolute_bps;
			else if(key.compare("CBAP_VERSION")==0)
				conf>>cbap_version;
			else if(key.compare("CBAP_FLOW_STATE_FILE")==0)
				conf>>cbap_flow_state_file;
			else if(key.compare("CBAP_CONTROL_OVERHEAD_FILE")==0)
				conf>>cbap_control_overhead_file;
			else if(key.compare("CBAP_PACKET_TRACE_FILE")==0)
				conf>>cbap_packet_trace_file;
			else if(key.compare("CBAP_PACKET_TRACE_MAX_MB")==0)
				conf>>cbap_packet_trace_max_mb;
			else if(key.compare("CBAP_TX_EVENT_FILE")==0)
				conf>>cbap_tx_event_file;
			else if(key.compare("CBAP_SCOPE_SUMMARY_FILE")==0)
				conf>>cbap_scope_summary_file;
			else if(key.compare("CBAP_SCOPE_LINK_FILE")==0)
				conf>>cbap_scope_link_file;
			else if(key.compare("CBAP_HANDOFF_SUMMARY_FILE")==0)
				conf>>cbap_handoff_summary_file;
			else if(key.compare("CBAP_HANDOFF_FLOW_FILE")==0)
				conf>>cbap_handoff_flow_file;
			else if(key.compare("CBAP_CONTROLLER_OWNERSHIP_FILE")==0)
				conf>>cbap_controller_ownership_file;
			else if(key.compare("CBAP_CONTROL_MESSAGE_FILE")==0)
				conf>>cbap_control_message_file;
			else if(key.compare("CBAP_ENVELOPE_LINK_FILE")==0)
				conf>>cbap_envelope_link_file;
			else if(key.compare("CBAP_ENVELOPE_FLOW_FILE")==0)
				conf>>cbap_envelope_flow_file;
			else if(key.compare("CBAP_INCUMBENT_PROGRESS_FILE")==0)
				conf>>cbap_incumbent_progress_file;
			else if(key.compare("CBAP_V20_BATCH_FILE")==0)
				conf>>cbap_v20_batch_file;
			else if(key.compare("CBAP_V20_FLOW_FILE")==0)
				conf>>cbap_v20_flow_file;
			else if(key.compare("CBAP_SBA_EVENT_FILE")==0)
				conf>>cbap_sba_event_file;
			else if(key.compare("CBAP_SBA_LEASE_US")==0)
				conf>>cbap_sba_lease_us;
			else if(key.compare("CBAP_BUDGET_Q_LOW_FRACTION")==0)
				conf>>cbap_budget_q_low_fraction;
			else if(key.compare("CBAP_BUDGET_Q_HIGH_FRACTION")==0)
				conf>>cbap_budget_q_high_fraction;
			else if(key.compare("CBAP_MAX_DRAIN_RATIO")==0)
				conf>>cbap_max_drain_ratio;
			else if(key.compare("CBAP_OLD_BATCH_WEIGHT")==0)
				conf>>cbap_old_batch_weight;
			else if(key.compare("CBAP_NEW_BATCH_WEIGHT")==0)
				conf>>cbap_new_batch_weight;
			else if(key.compare("CBAP_MIGRATION_ENABLE")==0)
				conf>>cbap_migration_enable;
			else if(key.compare("CBAP_MIGRATION_RELEASE_RATIO")==0)
				conf>>cbap_migration_release_ratio;
			else if(key.compare("CBAP_MIGRATION_DECAY_BASE")==0)
				conf>>cbap_migration_decay_base;
			else if(key.compare("CBAP_MIGRATION_RISE_BASE")==0)
				conf>>cbap_migration_rise_base;
			else if(key.compare("CBAP_MIGRATION_RISE_SKEW")==0)
				conf>>cbap_migration_rise_skew;
			else if(key.compare("CBAP_MIGRATION_MAX_RTT")==0)
				conf>>cbap_migration_max_rtt;
			else if(key.compare("CBAP_QUEUE_TARGET_FRACTION")==0)
				conf>>cbap_queue_target_fraction;
			else if(key.compare("CBAP_SCOPE_POLICY")==0)
				conf>>cbap_scope_policy;
			else if(key.compare("CBAP_SCOPE_BASE_CC")==0)
				conf>>cbap_scope_base_cc;
			else if(key.compare("CBAP_RATE_FLOOR_POLICY")==0)
				conf>>cbap_rate_floor_policy;
			else if(key.compare("CBAP_RATEFLOOR_SEMANTIC_ZERO_TEST")==0)
				conf>>cbap_ratefloor_semantic_zero_test;
			else if(key.compare("CBAP_RATEFLOOR_SEMANTIC_ZERO_FLOW")==0)
				conf>>cbap_ratefloor_semantic_zero_flow;
			else if(key.compare("CBAP_RATEFLOOR_SEMANTIC_ZERO_START_EPOCH")==0)
				conf>>cbap_ratefloor_semantic_zero_start_epoch;
			else if(key.compare("CBAP_RATEFLOOR_SEMANTIC_ZERO_END_EPOCH")==0)
				conf>>cbap_ratefloor_semantic_zero_end_epoch;
			else if(key.compare("CBAP_HANDOFF_ENABLE")==0)
				conf>>cbap_handoff_enable;
			else if(key.compare("CBAP_HANDOFF_STABLE_EPOCHS")==0)
				conf>>cbap_handoff_stable_epochs;
			else if(key.compare("CBAP_HANDOFF_BASE_CC")==0)
				conf>>cbap_handoff_base_cc;
			else if(key.compare("CBAP_HANDOFF_DIAGNOSTIC_FORCE_ROOT")==0)
				conf>>cbap_handoff_diagnostic_force_root;
			else if(key.compare("CBAP_HANDOFF_DIAGNOSTIC_RECOVERY_UNTIL_EPOCH")==0)
				conf>>cbap_handoff_diagnostic_recovery_until_epoch;
			else if(key.compare("CBAP_DELEGATION_DIAGNOSTIC_FORCE_STALE_EPOCHS")==0)
				conf>>cbap_delegation_diagnostic_force_stale_epochs;
			else if(key.compare("CBAP_TX_TRACE_TRACKING_PACKETS")==0)
				conf>>cbap_tx_trace_tracking_packets;
			else if(key.compare("ROUND_SCHEDULE_FILE")==0) conf>>round_schedule_file;
			else if(key.compare("ROUND_MODE")==0) conf>>round_mode;
			else if(key.compare("ROUND_TRACE_SELECTED_FLOWS")==0) conf>>round_selected_flow_ids;
			else if(key.compare("ROUND_TRACE_SELECTED_LINKS")==0) conf>>round_selected_link_ids;
			else if(key.compare("CRFM_TRACE_SAMPLE_US")==0) conf>>crfm_trace_sample_us;
			else if(key.compare("CRFM_MAX_TRACE_FILE_MB")==0) conf>>crfm_max_trace_file_mb;
			else if(key.compare("CRFM_MAX_TRACE_TOTAL_MB")==0) conf>>crfm_max_trace_total_mb;
			else if(key.compare("CRFM_MIN_FREE_GB")==0) conf>>crfm_min_free_gb;
			else if(key.compare("CRFM_MAX_EVENT_ROWS")==0) conf>>crfm_max_event_rows;
			else if(key.compare("CRFM_DEBUG")==0) conf>>crfm_debug;
			else if(key.compare("BOP_RHO")==0) conf>>bop_rho;
			else if(key.compare("BOP_BACKGROUND_BPS")==0) conf>>bop_background_bps;
				else if(key.compare("BOP_PHASE_STAGGER")==0) conf>>bop_phase_stagger;
					else if(key.compare("BOP_PACKET_BYTES")==0) conf>>bop_packet_bytes;
					else if(key.compare("BOP_BOTTLENECK_BPS")==0) conf>>bop_bottleneck_bps;
					else if(key.compare("BOP_MULTILINK_ENABLE")==0) conf>>bop_multilink_enable;
					else if(key.compare("BOP_MULTILINK_LINK_FILE")==0) conf>>bop_multilink_link_file;
					else if(key.compare("BOP_MULTILINK_PATH_FILE")==0) conf>>bop_multilink_path_file;
					else if(key.compare("BOP_MULTILINK_GROUP_FILE")==0) conf>>bop_multilink_group_file;
					else if(key.compare("BOP_MULTILINK_GROUP_DECISIONS_FILE")==0) conf>>bop_multilink_group_decisions_file;
					else if(key.compare("BOP_MULTILINK_LINK_CONSTRAINTS_FILE")==0) conf>>bop_multilink_link_constraints_file;
				else if(key.compare("BOP_QC_BDP_FACTOR")==0) conf>>bop_qc_bdp_factor;
				else if(key.compare("BOP_QC_DEFAULT_TAU_US")==0) conf>>bop_qc_default_tau_us;
				else if(key.compare("BOP_QC_TAU_EWMA_ALPHA")==0) conf>>bop_qc_tau_ewma_alpha;
					else if(key.compare("BOP_QC_QUEUE_LIMIT_MODE")==0) conf>>bop_qc_queue_limit_mode;
					else if(key.compare("BOP_QC_PACKET_MARGIN")==0) conf>>bop_qc_packet_margin;
					else if(key.compare("BOP_QC_ENABLE_PHASE_STAGGER")==0) conf>>bop_qc_enable_phase_stagger;
					else if(key.compare("BOP_QB_QUEUE_FRACTION")==0) conf>>bop_qb_queue_fraction;
					else if(key.compare("BOP_QB_PACKET_MARGIN")==0) conf>>bop_qb_packet_margin;
					else if(key.compare("BOP_QB_ENABLE_PHASE_STAGGER")==0) conf>>bop_qb_enable_phase_stagger;
					else if(key.compare("BOP_QB_MAX_PACKET_MARGIN")==0) conf>>bop_qb_max_packet_margin;
					else if(key.compare("BOP_QB_MAX_ENABLE_PHASE_STAGGER")==0) conf>>bop_qb_max_enable_phase_stagger;
				else if(key.compare("FLOW_SUMMARY_FILE")==0) conf>>flow_summary_file;
			else if(key.compare("ROUND_SUMMARY_FILE")==0) conf>>round_summary_file;
			else if(key.compare("FEEDBACK_SUMMARY_FILE")==0) conf>>feedback_summary_file;
			else if(key.compare("LINK_TIMESERIES_FILE")==0) conf>>link_timeseries_file;
			else if(key.compare("SELECTED_FLOW_TIMESERIES_FILE")==0) conf>>selected_flow_timeseries_file;
			else if(key.compare("CONTROLLER_SUMMARY_FILE")==0) conf>>controller_summary_file;
				else if(key.compare("GROUP_ROUND_SUMMARY_FILE")==0) conf>>group_round_summary_file;
					else if(key.compare("FLOW_PLAN_FILE")==0) conf>>flow_plan_file;
					else if(key.compare("BOP_QC_GROUP_DECISIONS_FILE")==0) conf>>bop_qc_group_decisions_file;
					else if(key.compare("BOP_QB_GROUP_DECISIONS_FILE")==0) conf>>bop_qb_group_decisions_file;
					else if(key.compare("BOP_QB_MAX_GROUP_DECISIONS_FILE")==0) conf>>bop_qb_max_group_decisions_file;
					else if(key.compare("PRT_PROBE_SUMMARY_FILE")==0) conf>>prt_probe_summary_file;
					else if(key.compare("PRT_GROUP_DECISIONS_FILE")==0) conf>>prt_group_decisions_file;
			else if(key.compare("ALGORITHM")==0) conf>>algorithm_name;
			else if(key.compare("SCENARIO")==0) conf>>scenario_name;
			else if(key.compare("SHORT_DIAG_ENABLE")==0)
				conf>>short_diag_enable;
			else if(key.compare("SHORT_DIAG_BOTTLENECK_NODE")==0)
				conf>>short_diag_bottleneck_node;
			else if(key.compare("SHORT_DIAG_BOTTLENECK_IF")==0)
				conf>>short_diag_bottleneck_if;
			else if(key.compare("SHORT_DIAG_MAX_EVENT_MB")==0)
				conf>>short_diag_max_event_mb;
			else if(key.compare("SHORT_DIAG_PIPELINE_FILE")==0)
				conf>>short_diag_pipeline_file;
			else if(key.compare("SHORT_DIAG_IDLE_FILE")==0)
				conf>>short_diag_idle_file;
			else if(key.compare("SHORT_DIAG_QP_TAIL_FILE")==0)
				conf>>short_diag_qp_tail_file;
			else if(key.compare("SHORT_DIAG_META_FILE")==0)
				conf>>short_diag_meta_file;
			else if(key.compare("SHORT_DIAG_EVENTS_FILE")==0)
				conf>>short_diag_events_file;
			else if(key.compare("SHORT_DIAG_TOPOLOGY_SHA256")==0)
				conf>>short_diag_topology_sha256;
			else if(key.compare("SHORT_DIAG_FLOW_SHA256")==0)
				conf>>short_diag_flow_sha256;
			else if(key.compare("SHORT_DIAG_ROUND_SHA256")==0)
				conf>>short_diag_round_sha256;
			else if(key.compare("FINAL_VALIDATION_ENABLE")==0)
				conf>>final_validation_enable;
			else if(key.compare("FINAL_BOTTLENECK_NODE")==0)
				conf>>final_bottleneck_node;
			else if(key.compare("FINAL_BOTTLENECK_IF")==0)
				conf>>final_bottleneck_if;
			else if(key.compare("FINAL_COLLECTIVE_FLOW_COUNT")==0)
				conf>>final_collective_flow_count;
			else if(key.compare("FINAL_PRIMER_FIRST_FLOW")==0)
				conf>>final_primer_first_flow;
			else if(key.compare("WIRE_SIZE_SUMMARY_FILE")==0)
				conf>>final_wire_size_file;
			else if(key.compare("RELEASE_QUEUE_SUMMARY_FILE")==0)
				conf>>final_release_queue_file;
			else if(key.compare("PRERELEASE_AUDIT_ENABLE")==0)
				conf>>prerelease_audit_enable;
			else if(key.compare("PRERELEASE_AUDIT_BOTTLENECK_NODE")==0)
				conf>>prerelease_audit_bottleneck_node;
			else if(key.compare("PRERELEASE_AUDIT_BOTTLENECK_IF")==0)
				conf>>prerelease_audit_bottleneck_if;
			else if(key.compare("PRERELEASE_AUDIT_COLLECTIVE_FLOW_COUNT")==0)
				conf>>prerelease_audit_collective_flow_count;
			else if(key.compare("PRERELEASE_AUDIT_PRIMER_FIRST_FLOW")==0)
				conf>>prerelease_audit_primer_first_flow;
			else if(key.compare("PRERELEASE_AUDIT_MAX_EVENT_MB")==0)
				conf>>prerelease_audit_max_event_mb;
			else if(key.compare("PRERELEASE_AUDIT_TIMELINE_FILE")==0)
				conf>>prerelease_audit_timeline_file;
			else if(key.compare("PRERELEASE_AUDIT_RESIDUAL_FILE")==0)
				conf>>prerelease_audit_residual_file;
			else if(key.compare("PRERELEASE_AUDIT_QUEUE_FILE")==0)
				conf>>prerelease_audit_queue_file;
			else if(key.compare("PRERELEASE_AUDIT_ECN_FILE")==0)
				conf>>prerelease_audit_ecn_file;
			else if(key.compare("PRERELEASE_AUDIT_META_FILE")==0)
				conf>>prerelease_audit_meta_file;
			else if(key.compare("PRERELEASE_AUDIT_TOPOLOGY_SHA256")==0)
				conf>>prerelease_audit_topology_sha256;
			else if(key.compare("PRERELEASE_AUDIT_FLOW_SHA256")==0)
				conf>>prerelease_audit_flow_sha256;
			else if(key.compare("PRERELEASE_AUDIT_ROUND_SHA256")==0)
				conf>>prerelease_audit_round_sha256;

			//std::cout << conf.cur << "\n";

			else if (key.compare("ENABLE_QCN") == 0)//QCN是否打开
			{
				uint32_t v;
				conf >> v;
				enable_qcn = v;
				if (enable_qcn)
					std::cout << "ENABLE_QCN\t\t\t" << "Yes" << "\n";
				else
					std::cout << "ENABLE_QCN\t\t\t" << "No" << "\n";
			}
			else if (key.compare("USE_DYNAMIC_PFC_THRESHOLD") == 0)
			{
				uint32_t v;
				conf >> v;
				use_dynamic_pfc_threshold = v;
				if (use_dynamic_pfc_threshold)
					std::cout << "USE_DYNAMIC_PFC_THRESHOLD\t" << "Yes" << "\n";
				else
					std::cout << "USE_DYNAMIC_PFC_THRESHOLD\t" << "No" << "\n";
			}
			else if (key.compare("CLAMP_TARGET_RATE") == 0)
			{
				uint32_t v;
				conf >> v;
				clamp_target_rate = v;
				if (clamp_target_rate)
					std::cout << "CLAMP_TARGET_RATE\t\t" << "Yes" << "\n";
				else
					std::cout << "CLAMP_TARGET_RATE\t\t" << "No" << "\n";
			}
			else if (key.compare("PAUSE_TIME") == 0)
			{
				double v;
				conf >> v;
				pause_time = v;
				std::cout << "PAUSE_TIME\t\t\t" << pause_time << "\n";
			}
			else if (key.compare("DATA_RATE") == 0)
			{
				std::string v;
				conf >> v;
				data_rate = v;
				std::cout << "DATA_RATE\t\t\t" << data_rate << "\n";
			}
			else if (key.compare("LINK_DELAY") == 0)
			{
				std::string v;
				conf >> v;
				link_delay = v;
				std::cout << "LINK_DELAY\t\t\t" << link_delay << "\n";
			}
			else if (key.compare("PACKET_PAYLOAD_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				packet_payload_size = v;
				std::cout << "PACKET_PAYLOAD_SIZE\t\t" << packet_payload_size << "\n";
			}
			else if (key.compare("L2_CHUNK_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_chunk_size = v;
				std::cout << "L2_CHUNK_SIZE\t\t\t" << l2_chunk_size << "\n";
			}
			else if (key.compare("L2_ACK_INTERVAL") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_ack_interval = v;
				std::cout << "L2_ACK_INTERVAL\t\t\t" << l2_ack_interval << "\n";
			}
			else if (key.compare("L2_BACK_TO_ZERO") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_back_to_zero = v;
				if (l2_back_to_zero)
					std::cout << "L2_BACK_TO_ZERO\t\t\t" << "Yes" << "\n";
				else
					std::cout << "L2_BACK_TO_ZERO\t\t\t" << "No" << "\n";
			}
			else if (key.compare("TOPOLOGY_FILE") == 0)
			{
				std::string v;
				conf >> v;
				topology_file = v;
				std::cout << "TOPOLOGY_FILE\t\t\t" << topology_file << "\n";
			}
			else if (key.compare("FLOW_FILE") == 0)
			{
				std::string v;
				conf >> v;
				flow_file = v;
				std::cout << "FLOW_FILE\t\t\t" << flow_file << "\n";
			}
			else if (key.compare("FIXED_PATH_FILE") == 0)
			{
				conf >> fixed_path_file;
				std::cout << "FIXED_PATH_FILE\t\t" << fixed_path_file << "\n";
			}
			else if (key.compare("FIXED_PATH_OUTPUT_FILE") == 0)
			{
				conf >> fixed_path_output_file;
				std::cout << "FIXED_PATH_OUTPUT_FILE\t" << fixed_path_output_file << "\n";
			}
			else if (key.compare("PORT_MONITOR_OUTPUT_FILE") == 0)
			{
				conf >> port_monitor_output_file;
				std::cout << "PORT_MONITOR_OUTPUT_FILE\t" << port_monitor_output_file << "\n";
			}
			else if (key.compare("PORT_MONITOR_INTERVAL_NS") == 0)
			{
				conf >> port_monitor_interval;
				std::cout << "PORT_MONITOR_INTERVAL_NS\t" << port_monitor_interval << "\n";
			}
			else if (key.compare("TRACE_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_file = v;
				std::cout << "TRACE_FILE\t\t\t" << trace_file << "\n";
			}
			else if (key.compare("TRACE_OUTPUT_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_output_file = v;
				if (argc > 2)
				{
					trace_output_file = trace_output_file + std::string(argv[2]);
				}
				std::cout << "TRACE_OUTPUT_FILE\t\t" << trace_output_file << "\n";
			}
			else if (key.compare("SIMULATOR_STOP_TIME") == 0)
			{
				double v;
				conf >> v;
				simulator_stop_time = v;
				std::cout << "SIMULATOR_STOP_TIME\t\t" << simulator_stop_time << "\n";
			}
			else if (key.compare("ALPHA_RESUME_INTERVAL") == 0)
			{
				double v;
				conf >> v;
				alpha_resume_interval = v;
				std::cout << "ALPHA_RESUME_INTERVAL\t\t" << alpha_resume_interval << "\n";
			}
			else if (key.compare("RP_TIMER") == 0)
			{
				double v;
				conf >> v;
				rp_timer = v;
				std::cout << "RP_TIMER\t\t\t" << rp_timer << "\n";
			}
			else if (key.compare("EWMA_GAIN") == 0)
			{
				double v;
				conf >> v;
				ewma_gain = v;
				std::cout << "EWMA_GAIN\t\t\t" << ewma_gain << "\n";
			}
			else if (key.compare("FAST_RECOVERY_TIMES") == 0)
			{
				uint32_t v;
				conf >> v;
				fast_recovery_times = v;
				std::cout << "FAST_RECOVERY_TIMES\t\t" << fast_recovery_times << "\n";
			}
			else if (key.compare("RATE_AI") == 0)
			{
				std::string v;
				conf >> v;
				rate_ai = v;
				std::cout << "RATE_AI\t\t\t\t" << rate_ai << "\n";
			}
			else if (key.compare("RATE_HAI") == 0)
			{
				std::string v;
				conf >> v;
				rate_hai = v;
				std::cout << "RATE_HAI\t\t\t" << rate_hai << "\n";
			}
			else if (key.compare("ERROR_RATE_PER_LINK") == 0)
			{
				double v;
				conf >> v;
				error_rate_per_link = v;
				std::cout << "ERROR_RATE_PER_LINK\t\t" << error_rate_per_link << "\n";
			}
			else if (key.compare("CC_MODE") == 0){
				conf >> cc_mode;
				std::cout << "CC_MODE\t\t" << cc_mode << '\n';
			}else if (key.compare("RATE_DECREASE_INTERVAL") == 0){
				double v;
				conf >> v;
				rate_decrease_interval = v;
				std::cout << "RATE_DECREASE_INTERVAL\t\t" << rate_decrease_interval << "\n";
			}else if (key.compare("MIN_RATE") == 0){
				conf >> min_rate;
				std::cout << "MIN_RATE\t\t" << min_rate << "\n";
			}else if (key.compare("FCT_OUTPUT_FILE") == 0){
				conf >> fct_output_file;
				std::cout << "FCT_OUTPUT_FILE\t\t" << fct_output_file << '\n';
			}else if (key.compare("HAS_WIN") == 0){
				conf >> has_win;
				std::cout << "HAS_WIN\t\t" << has_win << "\n";
			}else if (key.compare("GLOBAL_T") == 0){
				conf >> global_t;
				std::cout << "GLOBAL_T\t\t" << global_t << '\n';
			}else if (key.compare("MI_THRESH") == 0){
				conf >> mi_thresh;
				std::cout << "MI_THRESH\t\t" << mi_thresh << '\n';
			}else if (key.compare("VAR_WIN") == 0){
				uint32_t v;
				conf >> v;
				var_win = v;
				std::cout << "VAR_WIN\t\t" << v << '\n';
			}else if (key.compare("FAST_REACT") == 0){
				uint32_t v;
				conf >> v;
				fast_react = v;
				std::cout << "FAST_REACT\t\t" << v << '\n';
			}else if (key.compare("U_TARGET") == 0){
				conf >> u_target;
				std::cout << "U_TARGET\t\t" << u_target << '\n';
			}else if (key.compare("INT_MULTI") == 0){
				conf >> int_multi;
				std::cout << "INT_MULTI\t\t\t\t" << int_multi << '\n';
			}else if (key.compare("RATE_BOUND") == 0){
				uint32_t v;
				conf >> v;
				rate_bound = v;
				std::cout << "RATE_BOUND\t\t" << rate_bound << '\n';
			}else if (key.compare("ACK_HIGH_PRIO") == 0){
				conf >> ack_high_prio;
				std::cout << "ACK_HIGH_PRIO\t\t" << ack_high_prio << '\n';
			}else if (key.compare("DCTCP_RATE_AI") == 0){
				conf >> dctcp_rate_ai;
				std::cout << "DCTCP_RATE_AI\t\t\t\t" << dctcp_rate_ai << "\n";
			}else if (key.compare("PFC_OUTPUT_FILE") == 0){
				conf >> pfc_output_file;
				std::cout << "PFC_OUTPUT_FILE\t\t\t\t" << pfc_output_file << '\n';
			}else if (key.compare("LINK_DOWN") == 0){
				conf >> link_down_time >> link_down_A >> link_down_B;
				std::cout << "LINK_DOWN\t\t\t\t" << link_down_time << ' '<< link_down_A << ' ' << link_down_B << '\n';
			}else if (key.compare("ENABLE_TRACE") == 0){
				conf >> enable_trace;
				std::cout << "ENABLE_TRACE\t\t\t\t" << enable_trace << '\n';
			}else if (key.compare("KMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmax[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("KMIN_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMIN_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmin[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("PMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "PMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					double p;
					conf >> rate >> p;
					rate2pmax[rate] = p;
					std::cout << ' ' << rate << ' ' << p;
				}
				std::cout<<'\n';
			}else if (key.compare("BUFFER_SIZE") == 0){
				conf >> buffer_size;
				std::cout << "BUFFER_SIZE\t\t\t\t" << buffer_size << '\n';
			}else if (key.compare("QLEN_MON_FILE") == 0){
				conf >> qlen_mon_file;
				std::cout << "QLEN_MON_FILE\t\t\t\t" << qlen_mon_file << '\n';
			}else if (key.compare("QLEN_MON_START") == 0){
				conf >> qlen_mon_start;
				std::cout << "QLEN_MON_START\t\t\t\t" << qlen_mon_start << '\n';
			}else if (key.compare("QLEN_MON_END") == 0){
				conf >> qlen_mon_end;
				std::cout << "QLEN_MON_END\t\t\t\t" << qlen_mon_end << '\n';
			}else if (key.compare("MULTI_RATE") == 0){
				int v;
				conf >> v;
				multi_rate = v;
				std::cout << "MULTI_RATE\t\t\t\t" << multi_rate << '\n';
			}else if (key.compare("SAMPLE_FEEDBACK") == 0){
				int v;
				conf >> v;
				sample_feedback = v;
				std::cout << "SAMPLE_FEEDBACK\t\t\t\t" << sample_feedback << '\n';
			}else if(key.compare("PINT_LOG_BASE") == 0){
				conf >> pint_log_base;
				std::cout << "PINT_LOG_BASE\t\t\t\t" << pint_log_base << '\n';
			}else if (key.compare("PINT_PROB") == 0){
				conf >> pint_prob;
				std::cout << "PINT_PROB\t\t\t\t" << pint_prob << '\n';
			}
			fflush(stdout);
		}
		conf.close();//关闭配置文件
	}
	else//若是没写配置文件但是又PGO_TRAINING
		{
			std::cout << "Error: require a config file\n";
		fflush(stdout);
			return 1;
		}
	if (round_mode){
			if (round_schedule_file.empty())
				ConfigError("ROUND_SCHEDULE_FILE is required when ROUND_MODE=1");
					if (!(cc_mode == 0 || cc_mode == 1 ||
							cc_mode == 3 || cc_mode == 7 ||
							cc_mode == 8 ||
							(cc_mode >= 11 && cc_mode <= 30)))
					ConfigError("ROUND_MODE CC_MODE is not registered");
		if (crfm_trace_sample_us < 10)
			ConfigError("CRFM_TRACE_SAMPLE_US must be at least 10");
				if ((cc_mode == RdmaHw::CC_MODE_BOP ||
						cc_mode == RdmaHw::CC_MODE_BOP_QC ||
						cc_mode == RdmaHw::CC_MODE_BOP_QB ||
						cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX ||
						cc_mode == RdmaHw::CC_MODE_BOP_QB_ORACLE_Q0 ||
						cc_mode == RdmaHw::CC_MODE_BOP_QB_PRT) &&
					(!(bop_rho > 0 && bop_rho <= 1) ||
					 bop_bottleneck_bps <= bop_background_bps ||
					 bop_packet_bytes == 0))
				ConfigError("invalid BOP parameter or bottleneck capacity");
			if (cc_mode == RdmaHw::CC_MODE_BOP_QC &&
					(!std::isfinite(bop_qc_bdp_factor) ||
					 bop_qc_bdp_factor < 0 ||
					 !std::isfinite(bop_qc_default_tau_us) ||
					 bop_qc_default_tau_us <= 0 ||
					 !std::isfinite(bop_qc_tau_ewma_alpha) ||
					 bop_qc_tau_ewma_alpha <= 0 ||
					 bop_qc_tau_ewma_alpha > 1 ||
					 bop_qc_queue_limit_mode != 1 ||
						 bop_packet_bytes < packet_payload_size))
					ConfigError("invalid BOP-QC parameter");
				if (RdmaHw::UsesBopQbCredit(cc_mode) &&
						(!std::isfinite(bop_qb_queue_fraction) ||
						 bop_qb_queue_fraction <= 0 ||
						 bop_qb_queue_fraction > 1 ||
						 bop_packet_bytes < packet_payload_size))
					ConfigError("invalid BOP-QB parameter");
				if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX &&
						bop_packet_bytes < packet_payload_size)
					ConfigError("invalid BOP-QB-Max parameter");
				}else if (cc_mode >= 11 && cc_mode <= 30){
				ConfigError("CRFM CC_MODE requires ROUND_MODE=1");
			}
	if (cbap_enable){
		if (!RdmaHw::IsCbapMode(cc_mode) || !round_mode ||
				cbap_control_epoch_us == 0 ||
				cbap_planning_delay_us == 0 ||
				cbap_control_delay_us == 0 ||
				!(cbap_rho > 0 && cbap_rho <= 1) ||
				!(cbap_epsilon_rate > 0) ||
				cbap_priority >= QbbNetDevice::qCnt ||
				cbap_max_wire_packet_bytes < packet_payload_size ||
				cbap_tx_trace_tracking_packets == 0 ||
				cbap_increase_policy >
					RdmaHw::CBAP_INCREASE_ADAPTIVE_V11 ||
				!std::isfinite(cbap_increase_fraction) ||
				std::fabs(cbap_increase_fraction - 0.10) > 1e-12 ||
				cbap_increase_absolute_bps != UINT64_C(2000000000) ||
				cbap_scope_policy >
					RdmaHw::CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION ||
				cbap_scope_base_cc != 1 ||
				cbap_rate_floor_policy >
					RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING ||
				!(cbap_queue_target_fraction == 0.0 ||
				  std::fabs(cbap_queue_target_fraction - 0.125) < 1e-12 ||
				  std::fabs(cbap_queue_target_fraction - 0.25) < 1e-12 ||
				  std::fabs(cbap_queue_target_fraction - 0.5) < 1e-12 ||
				  std::fabs(cbap_queue_target_fraction - 0.75) < 1e-12) ||
				(cc_mode == RdmaHw::CC_MODE_CBAP_FULL_SCOPED &&
				 cbap_rate_floor_policy !=
					RdmaHw::CBAP_RATE_FLOOR_ONE_PACKET_PER_EPOCH_LEGACY) ||
				(cc_mode ==
					RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX &&
				 cbap_rate_floor_policy !=
					RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING) ||
				(cc_mode == RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF &&
				 cbap_rate_floor_policy !=
					RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING) ||
				(cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION &&
				 cbap_rate_floor_policy !=
					RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING) ||
				((cc_mode == RdmaHw::CC_MODE_CBAP_FULL_SCOPED ||
				  cc_mode ==
					RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
				  cc_mode == RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
				  cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION) &&
				 cbap_scope_policy !=
					RdmaHw::CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION) ||
				(cc_mode != RdmaHw::CC_MODE_CBAP_FULL_SCOPED &&
				 cc_mode !=
					RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX &&
				 cc_mode != RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF &&
				 cc_mode != RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION &&
				 cbap_scope_policy != RdmaHw::CBAP_SCOPE_ALWAYS) ||
				(cbap_ratefloor_semantic_zero_test &&
				 (cc_mode !=
					RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
				  cbap_ratefloor_semantic_zero_start_epoch == 0 ||
				  cbap_ratefloor_semantic_zero_end_epoch <=
					cbap_ratefloor_semantic_zero_start_epoch)) ||
				(cc_mode ==
					RdmaHw::CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX &&
				 cbap_applied_rate_audit_file.empty()) ||
				(cbap_handoff_enable != (cc_mode ==
					RdmaHw::CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
					cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION)) ||
				(cbap_handoff_enable &&
				 (cbap_handoff_stable_epochs != 2 ||
				  cbap_handoff_base_cc != 1 ||
				  cbap_handoff_summary_file.empty() ||
				  cbap_handoff_flow_file.empty() ||
				  cbap_controller_ownership_file.empty() ||
				  cbap_control_message_file.empty())) ||
				(cc_mode == RdmaHw::CC_MODE_CBAP_FULL_GUARDED_DELEGATION &&
				 (cbap_envelope_link_file.empty() ||
				  cbap_envelope_flow_file.empty() ||
				  cbap_incumbent_progress_file.empty())) ||
				((cc_mode ==
					RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ||
				  cc_mode ==
					RdmaHw::CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC) &&
				 (cbap_v20_batch_file.empty() || cbap_v20_flow_file.empty() ||
					  cbap_rate_floor_policy !=
						RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING)) ||
				(cc_mode == RdmaHw::CC_MODE_CBAP_SBA_DCQCN &&
				 (cbap_sba_event_file.empty() ||
				  cbap_rate_floor_policy !=
					RdmaHw::CBAP_RATE_FLOOR_EXACT_GRANT_PACING ||
				  cbap_scope_policy != RdmaHw::CBAP_SCOPE_ALWAYS ||
				  cbap_handoff_enable ||
				  cbap_sba_lease_us == 0)) ||
				cbap_version.empty())
			ConfigError("invalid CBAP mode or configuration");
	}else if (RdmaHw::IsCbapMode(cc_mode)){
		ConfigError("CBAP CC_MODE requires CBAP_ENABLE=1");
	}
	if (sim_seed == 1 && (cbap_packet_trace_file.empty() ||
			cbap_packet_trace_max_mb == 0 ||
			cbap_packet_trace_max_mb > 256))
		ConfigError("seed=1 requires bounded CBAP packet trace");


	bool dynamicth = use_dynamic_pfc_threshold;//将全局变量转成一个bool

	Config::SetDefault("ns3::QbbNetDevice::PauseTime", UintegerValue(pause_time));//设置PFC暂停时间
	Config::SetDefault("ns3::QbbNetDevice::QcnEnabled", BooleanValue(enable_qcn));//配置是否启用QCN
	Config::SetDefault("ns3::QbbNetDevice::DynamicThreshold", BooleanValue(dynamicth));//配置是否使用动态PFC阈值

	// set int_multi
	IntHop::multi = int_multi;//HPCC算法中IntHop指的是INT每跳信息结构。里面包含每个交换机hop的一些状态
	// IntHeader::mode，这边就是根据拥塞模式选择IntHeader的格式，比如mode==7，也就是timely模式，主要是基于RTT，所以内部放一个时间戳TS
	if (cc_mode == 7) // timely, use timestamp
		IntHeader::mode = IntHeader::TS;
	else if (RdmaHw::UsesHpccTelemetryMode(cc_mode)) // HPCC-family modes use full INT
		IntHeader::mode = IntHeader::NORMAL;
	else if (cc_mode == 10) // hpcc-pint，往头部加入压缩的字段
		IntHeader::mode = IntHeader::PINT;
	else // others, no extra header，不添加额外头
		IntHeader::mode = IntHeader::NONE;

	// Set Pint
	if (cc_mode == 10){
		Pint::set_log_base(pint_log_base);//设置对数量化底数，也就是上面配置的，用意就是将网络负载什么的信息编码成一个较小的整数，底数越接近1，需要的bit越多
		IntHeader::pint_bytes = Pint::get_n_bytes();//计算占用的字节bit
		printf("PINT bits: %d bytes: %d\n", Pint::get_n_bits(), Pint::get_n_bytes());
	}

	SeedManager::SetSeed(sim_seed);

	topof.open(topology_file.c_str());
	flowf.open(flow_file.c_str());
	tracef.open(trace_file.c_str());
	uint32_t node_num, switch_num, link_num, trace_num;
	topof >> node_num >> switch_num >> link_num;
	flowf >> flow_num;
	tracef >> trace_num;
	ReadFixedPaths();
	ReadBopMultilinkInputs();
	ReadCbapInputs();
	ReadRoundSchedule();


	//n.Create(node_num);
	//在拓扑中读取数据在创建节点，比如说开头是5 3 4，意思是5个节点，3个switch，4条链路
	std::vector<uint32_t> node_type(node_num, 0);//创建一个长度为node_num的数组，初始化为0
	for (uint32_t i = 0; i < switch_num; i++)
	{
		uint32_t sid;
		topof >> sid;
		node_type[sid] = 1;
	}
	uint64_t bopQcEcnThresholdBytes = 0;
	uint64_t bopQbEcnThresholdBytes = 0;
	uint64_t bopQbMaxEcnThresholdBytes = 0;
	if (cc_mode == RdmaHw::CC_MODE_BOP_QC){
		auto threshold = rate2kmin.find(bop_bottleneck_bps);
		if (threshold == rate2kmin.end())
			ConfigError("BOP-QC bottleneck has no KMIN_MAP entry");
		bopQcEcnThresholdBytes = (uint64_t)threshold->second * 1000;
		if (bopQcEcnThresholdBytes == 0)
			ConfigError("BOP-QC ECN threshold must be positive");
	}
	if (RdmaHw::UsesBopQbCredit(cc_mode)){
		auto threshold = rate2kmin.find(bop_bottleneck_bps);
		if (threshold == rate2kmin.end())
			ConfigError("BOP-QB bottleneck has no KMIN_MAP entry");
		bopQbEcnThresholdBytes = (uint64_t)threshold->second * 1000;
		if (bopQbEcnThresholdBytes == 0)
			ConfigError("BOP-QB ECN threshold must be positive");
	}
	if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX){
		auto threshold = rate2kmin.find(bop_bottleneck_bps);
		if (threshold == rate2kmin.end())
			ConfigError("BOP-QB-Max bottleneck has no KMIN_MAP entry");
		bopQbMaxEcnThresholdBytes =
			(uint64_t)threshold->second * 1000;
		if (bopQbMaxEcnThresholdBytes == 0)
			ConfigError("BOP-QB-Max ECN threshold must be positive");
	}
	for (uint32_t i = 0; i < node_num; i++){
		if (node_type[i] == 0)//创建主机host
			n.Add(CreateObject<Node>());
		else{//创建switch
			Ptr<SwitchNode> sw = CreateObject<SwitchNode>();
			n.Add(sw);
			sw->SetAttribute("EcnEnabled", BooleanValue(enable_qcn));//switch中是否打开QCN
			sw->SetAttribute("PfcEnabled", BooleanValue(pfc_runtime_enable));
		}
	}


	NS_LOG_INFO("Create nodes.");

	InternetStackHelper internet;
	internet.Install(n);

	//
	// Assign IP to each server
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0){ // is server
			serverAddress.resize(i + 1);
			serverAddress[i] = node_id_to_ip(i);
		}
	}

	NS_LOG_INFO("Create channels.");

	//
	// Explicitly create the channels required by the topology.
	//

	Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();//错误模型，作用是让包按一定概率被认为出错丢掉，控制丢包率
	Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();//均匀随机数发生器
	rem->SetRandomVariable(uv);//将生成的随机数交给错误模型使用，也就是说后面每一个包是否出错会通过这个随机数模型决定
	uv->SetStream(50);//随机数编号，即若是上述出错率为0.1，随机数 < 0.1那这样包就会出错，反之正常
	rem->SetAttribute("ErrorRate", DoubleValue(error_rate_per_link));//设置错误率
	rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));//设置错误单位，按照bit来

	pfc_csv = fopen(pfc_output_file.c_str(), "w");
	if (pfc_csv == NULL)
		ConfigError("cannot open PFC_OUTPUT_FILE");
	fprintf(pfc_csv, "time_ns,node_id,if_index,q_index,event_type\n");
	if (pfc_semantic_audit_enable){
		pfc_semantic_csv = fopen(pfc_event_trace_file.c_str(), "w");
		if (!pfc_semantic_csv)
			ConfigError("cannot open PFC_EVENT_TRACE_FILE");
		fprintf(pfc_semantic_csv,
			"timestamp_ns,node_id,device_id,port_id,priority_or_pg,"
			"queue_bytes,pfc_threshold_bytes,event_type,pause_quanta,"
			"pause_duration_ns,sender_paused,packet_owner\n");
	}

	QbbHelper qbb;//这个Helper用来创建NetDevice，Channel，队列，还有PFC/QCN相关功能，意思差不多就是安装了一个Qbb队列，所以Qbb差不多就是一个支持很多功能的网卡链路模型
	Ipv4AddressHelper ipv4;
	for (uint32_t i = 0; i < link_num; i++)//开始构造链路
	{
		uint32_t src, dst;//读取一条链路
		std::string data_rate, link_delay;//链路速率，传播时延，包错误率
		double error_rate;
		topof >> src >> dst >> data_rate >> link_delay >> error_rate;

		Ptr<Node> snode = n.Get(src), dnode = n.Get(dst);

		qbb.SetDeviceAttribute("DataRate", StringValue(data_rate));
		qbb.SetChannelAttribute("Delay", StringValue(link_delay));

		if (error_rate > 0)//配置错误模型
		{
			Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
			Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
			rem->SetRandomVariable(uv);
			uv->SetStream(50);
			rem->SetAttribute("ErrorRate", DoubleValue(error_rate));
			rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
		}
		else//也就是说内部这个error_rate是一个局部变量，如果局部变量为0，则使用在for之前的时候创建的那个全局变量的概率
		{
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
		}

		fflush(stdout);

		// Assigne server IP
		// Note: this should be before the automatic assignment below (ipv4.Assign(d)),
		// because we want our IP to be the primary IP (first in the IP address list),
		// so that the global routing is based on our IP
		NetDeviceContainer d = qbb.Install(snode, dnode);//安装链路
		if (snode->GetNodeType() == 0){
			Ptr<Ipv4> ipv4 = snode->GetObject<Ipv4>();
			ipv4->AddInterface(d.Get(0));
			ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[src], Ipv4Mask(0xff000000)));
		}
		if (dnode->GetNodeType() == 0){
			Ptr<Ipv4> ipv4 = dnode->GetObject<Ipv4>();
			ipv4->AddInterface(d.Get(1));
			ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[dst], Ipv4Mask(0xff000000)));
		}

		//给这两个节点设置IP（serverAddress[i] = node_id_to_ip(i);）

		// used to create a graph of the topology
		nbr2if[snode][dnode].idx = DynamicCast<QbbNetDevice>(d.Get(0))->GetIfIndex();
		nbr2if[snode][dnode].up = true;
		nbr2if[snode][dnode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(0))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[snode][dnode].bw = DynamicCast<QbbNetDevice>(d.Get(0))->GetDataRate().GetBitRate();
		nbr2if[dnode][snode].idx = DynamicCast<QbbNetDevice>(d.Get(1))->GetIfIndex();
		nbr2if[dnode][snode].up = true;
		nbr2if[dnode][snode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(1))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[dnode][snode].bw = DynamicCast<QbbNetDevice>(d.Get(1))->GetDataRate().GetBitRate();
		//建立拓扑邻接表的信息
		// This is just to set up the connectivity between nodes. The IP addresses are useless
		char ipstring[16];
		sprintf(ipstring, "10.%d.%d.0", i / 254 + 1, i % 254 + 1);
		ipv4.SetBase(ipstring, "255.255.255.0");
		ipv4.Assign(d);
		//给这条链路分配普通IP即不同的/24网段

		// setup PFC trace
		DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_csv, DynamicCast<QbbNetDevice>(d.Get(0))));
		//这个表示当d.Get(0)这个QbbNetDevice触发QbbPfc trace事件的时候调用get_pfc函数，然后写入pfc_file这里，下面的则是这条链路另外一端如果触发也一样写入
		DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_csv, DynamicCast<QbbNetDevice>(d.Get(1))));
		if (pfc_semantic_audit_enable){
			DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext(
				"PfcSemantic", MakeBoundCallback(&DevicePfcSemantic,
					DynamicCast<QbbNetDevice>(d.Get(0))));
			DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext(
				"PfcSemantic", MakeBoundCallback(&DevicePfcSemantic,
					DynamicCast<QbbNetDevice>(d.Get(1))));
		}
	}
		// The simulation uses host serverAddress values for RDMA flows and
		// separate 10.x.x.0/24 addresses for point-to-point connectivity.
	nic_rate = get_nic_rate(n);

	// config switch
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 1){ // is switch
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));//把普通的node指针转化成switch指针
			if (pfc_semantic_audit_enable)
				sw->TraceConnectWithoutContext("PfcSemantic",
					MakeBoundCallback(&SwitchPfcSemantic, sw));
			uint32_t shift = 3; // 设置PFC动态阈值的超参数alpha
			for (uint32_t j = 1; j < sw->GetNDevices(); j++){//遍历switch上所有真实的端口
				Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(j));//给端口创建网卡
				// 配置ECN
				uint64_t rate = dev->GetDataRate().GetBitRate();
				NS_ASSERT_MSG(rate2kmin.find(rate) != rate2kmin.end(), "must set kmin for each link speed");
				NS_ASSERT_MSG(rate2kmax.find(rate) != rate2kmax.end(), "must set kmax for each link speed");
				NS_ASSERT_MSG(rate2pmax.find(rate) != rate2pmax.end(), "must set pmax for each link speed");
				sw->m_mmu->ConfigEcn(j, rate2kmin[rate], rate2kmax[rate], rate2pmax[rate]);//将上面的那些参数写入switch MMU中
				// 配置PFC
				uint64_t delay = DynamicCast<QbbChannel>(dev->GetChannel())->GetDelay().GetTimeStep();//取出这个网卡连接的channel的delay
				uint32_t headroom = rate * delay / 8 / 1000000000 * 3;//配置headroom，所以headroom ≈ 3 * 带宽 * 单向传播时延；增益带宽时延积
				sw->m_mmu->ConfigHdrm(j, headroom);//写入

				// set pfc alpha, proportional to link bw
				sw->m_mmu->pfc_a_shift[j] = shift;//即2的三次方=8；故threshold阈值 = 剩余共享 buffer / 8
				while (rate > nic_rate && sw->m_mmu->pfc_a_shift[j] > 0){//当NIC速率大于host速率则开始减少shift这个参数，nic速率也要减半
					sw->m_mmu->pfc_a_shift[j]--;
					rate /= 2;
				}
			}
			sw->m_mmu->ConfigNPort(sw->GetNDevices()-1);//-1是因为dev0一般是loopback
			sw->m_mmu->ConfigBufferSize(buffer_size* 1024 * 1024);//配置交换机总buffer大小，文件中的buffersize单位是MB
			sw->m_mmu->node_id = sw->GetId();
		}
	}
	if (pfc_semantic_audit_enable){
		Ptr<SwitchNode> auditSwitch =
			DynamicCast<SwitchNode>(n.Get(pfc_audit_node));
		NS_ASSERT_MSG(auditSwitch &&
			pfc_audit_if < auditSwitch->GetNDevices(),
			"PFC semantic audit target is invalid");
		Ptr<QbbNetDevice> auditDevice = DynamicCast<QbbNetDevice>(
			auditSwitch->GetDevice(pfc_audit_if));
		NS_ASSERT_MSG(auditDevice,
			"PFC semantic audit target is not QbbNetDevice");
		auditDevice->TraceConnectWithoutContext("QbbEnqueue",
			MakeBoundCallback(&PfcAuditQueueEvent, auditDevice));
		auditDevice->TraceConnectWithoutContext("QbbDequeue",
			MakeBoundCallback(&PfcAuditQueueEvent, auditDevice));
	}

	#if ENABLE_QP
	FILE *fct_output = fopen(fct_output_file.c_str(), "w");
	//
	// install RDMA driver
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0){ // is server
			// create RdmaHw
			Ptr<RdmaHw> rdmaHw = CreateObject<RdmaHw>();//创建RDMA硬件对象，其可以维护QP,选择NIC，发送RDMA包，处理ACK/NACK/CNP，执行拥塞控制算法
			rdmaHw->SetAttribute("ClampTargetRate", BooleanValue(clamp_target_rate));
			rdmaHw->SetAttribute("AlphaResumInterval", DoubleValue(alpha_resume_interval));
			rdmaHw->SetAttribute("RPTimer", DoubleValue(rp_timer));
			rdmaHw->SetAttribute("FastRecoveryTimes", UintegerValue(fast_recovery_times));
			rdmaHw->SetAttribute("EwmaGain", DoubleValue(ewma_gain));
			rdmaHw->SetAttribute("RateAI", DataRateValue(DataRate(rate_ai)));
			rdmaHw->SetAttribute("RateHAI", DataRateValue(DataRate(rate_hai)));
			rdmaHw->SetAttribute("L2BackToZero", BooleanValue(l2_back_to_zero));
			rdmaHw->SetAttribute("L2ChunkSize", UintegerValue(l2_chunk_size));
			rdmaHw->SetAttribute("L2AckInterval", UintegerValue(l2_ack_interval));
			rdmaHw->SetAttribute("CcMode", UintegerValue(cc_mode));
			rdmaHw->SetAttribute("RateDecreaseInterval", DoubleValue(rate_decrease_interval));
			rdmaHw->SetAttribute("MinRate", DataRateValue(DataRate(min_rate)));
			rdmaHw->SetAttribute("Mtu", UintegerValue(packet_payload_size));
			rdmaHw->SetAttribute("MiThresh", UintegerValue(mi_thresh));
			rdmaHw->SetAttribute("VarWin", BooleanValue(var_win));
			rdmaHw->SetAttribute("FastReact", BooleanValue(fast_react));
			rdmaHw->SetAttribute("MultiRate", BooleanValue(multi_rate));
			rdmaHw->SetAttribute("SampleFeedback", BooleanValue(sample_feedback));
			rdmaHw->SetAttribute("TargetUtil", DoubleValue(u_target));
			rdmaHw->SetAttribute("RateBound", BooleanValue(rate_bound));
			rdmaHw->SetAttribute("RoundMode", BooleanValue(round_mode));
			rdmaHw->SetAttribute("BopRho", DoubleValue(bop_rho));
			rdmaHw->SetAttribute("BopBackgroundBps", UintegerValue(bop_background_bps));
			rdmaHw->SetAttribute("BopPhaseStagger", BooleanValue(bop_phase_stagger));
				rdmaHw->SetAttribute("BopPacketBytes", UintegerValue(bop_packet_bytes));
				rdmaHw->SetAttribute("BopBottleneckBps", UintegerValue(bop_bottleneck_bps));
				rdmaHw->SetAttribute("BopMultilinkEnable", BooleanValue(bop_multilink_enable));
			if (cc_mode == RdmaHw::CC_MODE_BOP_QC){
				rdmaHw->SetAttribute("BopQcBdpFactor", DoubleValue(bop_qc_bdp_factor));
				rdmaHw->SetAttribute("BopQcDefaultTauUs", DoubleValue(bop_qc_default_tau_us));
				rdmaHw->SetAttribute("BopQcTauEwmaAlpha", DoubleValue(bop_qc_tau_ewma_alpha));
				rdmaHw->SetAttribute("BopQcQueueLimitMode", UintegerValue(bop_qc_queue_limit_mode));
				rdmaHw->SetAttribute("BopQcPacketMargin", UintegerValue(bop_qc_packet_margin));
				rdmaHw->SetAttribute("BopQcEnablePhaseStagger", BooleanValue(bop_qc_enable_phase_stagger));
				rdmaHw->SetAttribute("BopQcEcnThresholdBytes", UintegerValue(bopQcEcnThresholdBytes));
			}
			if (RdmaHw::UsesBopQbCredit(cc_mode)){
				rdmaHw->SetAttribute("BopQbQueueFraction", DoubleValue(bop_qb_queue_fraction));
				rdmaHw->SetAttribute("BopQbPacketMargin", UintegerValue(bop_qb_packet_margin));
				rdmaHw->SetAttribute("BopQbEnablePhaseStagger", BooleanValue(bop_qb_enable_phase_stagger));
				rdmaHw->SetAttribute("BopQbEcnThresholdBytes", UintegerValue(bopQbEcnThresholdBytes));
			}
			if (final_validation_enable)
				rdmaHw->SetAttribute("FinalPrimerFirstFlow",
					UintegerValue(final_primer_first_flow));
			if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX){
				rdmaHw->SetAttribute("BopQbMaxPacketMargin", UintegerValue(bop_qb_max_packet_margin));
				rdmaHw->SetAttribute("BopQbMaxEnablePhaseStagger", BooleanValue(bop_qb_max_enable_phase_stagger));
				rdmaHw->SetAttribute("BopQbMaxEcnThresholdBytes", UintegerValue(bopQbMaxEcnThresholdBytes));
			}
			rdmaHw->SetAttribute("DctcpRateAI", DataRateValue(DataRate(dctcp_rate_ai)));
			rdmaHw->SetPintSmplThresh(pint_prob);
			// create and install RdmaDriver
			Ptr<RdmaDriver> rdma = CreateObject<RdmaDriver>();//创建RDMA驱动对象
			Ptr<Node> node = n.Get(i);
			rdma->SetNode(node);
			rdma->SetRdmaHw(rdmaHw);

			node->AggregateObject (rdma);//node聚合RDMA
			rdma->Init();
			rdma->TraceConnectWithoutContext("QpComplete", MakeBoundCallback (qp_finish, fct_output));
		}
	}
	#endif

	// set ACK priority on hosts
	if (ack_high_prio)
		RdmaEgressQueue::ack_q_idx = 0;
	else
		RdmaEgressQueue::ack_q_idx = 3;

	// setup routing
	CalculateRoutes(n);
	SetRoutingEntries();
	ParseIdSets();
	SetupCbapPacketTrace();
	if(selected_flow_set.size()>4)
		ConfigError("ROUND_TRACE_SELECTED_FLOWS permits at most four flows");
		if(round_mode && !bop_multilink_enable &&
				selected_link_set.size()!=1)
			ConfigError("ROUND_TRACE_SELECTED_LINKS must select exactly one bottleneck");
		if(round_mode && bop_multilink_enable &&
				selected_link_set.empty())
			ConfigError("BOP multilink mode requires controlled links");
	SetupFinalValidation();
		if (round_mode && (flow_summary_file.empty() ||
			round_summary_file.empty() || feedback_summary_file.empty() ||
			controller_summary_file.empty() || link_timeseries_file.empty() ||
			selected_flow_timeseries_file.empty() ||
			group_round_summary_file.empty() || flow_plan_file.empty()))
			ConfigError("ROUND_MODE requires all CRFM output files");
		if (cc_mode == RdmaHw::CC_MODE_BOP_QC &&
				bop_qc_group_decisions_file.empty())
			ConfigError("BOP-QC requires BOP_QC_GROUP_DECISIONS_FILE");
		if (RdmaHw::UsesBopQbCredit(cc_mode) &&
				bop_qb_group_decisions_file.empty())
			ConfigError("BOP-QB requires BOP_QB_GROUP_DECISIONS_FILE");
		if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX &&
				bop_qb_max_group_decisions_file.empty())
			ConfigError("BOP-QB-Max requires BOP_QB_MAX_GROUP_DECISIONS_FILE");
			if (cc_mode == RdmaHw::CC_MODE_BOP_QB_PRT &&
					(prt_probe_summary_file.empty() ||
					 prt_group_decisions_file.empty()))
				ConfigError("BOP-QB-PRT requires both PRT output files");
			if (bop_multilink_enable && cc_mode == RdmaHw::CC_MODE_BOP_QB &&
					(bop_multilink_group_decisions_file.empty() ||
					 bop_multilink_link_constraints_file.empty()))
				ConfigError("BOP multilink mode requires both decision outputs");
	if(!flow_summary_file.empty()){
		flow_summary_csv=fopen(flow_summary_file.c_str(),"w");
		if(!flow_summary_csv)ConfigError("cannot open FLOW_SUMMARY_FILE");
		fprintf(flow_summary_csv,"scenario,algorithm,seed,flow_id,qp_id,src,dst,total_size_bytes,start_time,finish_time,fct,acked_bytes,completed,flow_goodput\n");
	}
	if(!round_summary_file.empty()){
		round_summary_csv=fopen(round_summary_file.c_str(),"w");
		if(!round_summary_csv)ConfigError("cannot open ROUND_SUMMARY_FILE");
		fprintf(round_summary_csv,"scenario,algorithm,seed,flow_id,qp_id,round_id,round_group_id,participant_count,release_time,injection_end_time,ack_completion_time,round_completion_time,round_bytes,start_rate,minimum_rate,end_rate,next_round_start_rate,feedback_loop_delay,first_feedback_after_injection,selected_link_peak_queue,round_start_seq,round_end_seq,cnp_count,dcqcn_start_alpha,dcqcn_end_alpha,dcqcn_start_recovery_stage,dcqcn_end_recovery_stage\n");
	}
	if(!feedback_summary_file.empty()){
		feedback_summary_csv=fopen(feedback_summary_file.c_str(),"w");
		if(!feedback_summary_csv)ConfigError("cannot open FEEDBACK_SUMMARY_FILE");
		fprintf(feedback_summary_csv,"flow_id,round_id,total_feedback,int_hop_count,actionable_feedback,late_same_round_feedback,stale_older_round_feedback,feedback_during_off,live_rate_changes_during_off,first_feedback_time,last_feedback_time,mean_remaining_unsent_ratio,min_remaining_unsent_ratio,mean_remaining_unsent_bytes,min_remaining_unsent_bytes,max_normalized_load,mean_normalized_load,first_rate_before,last_rate_after,feedback_changed_live_rate,late_action_ratio,actionable_byte_ratio\n");
	}
	if(!controller_summary_file.empty()){
		controller_summary_csv=fopen(controller_summary_file.c_str(),"w");
		if(!controller_summary_csv)ConfigError("cannot open CONTROLLER_SUMMARY_FILE");
		fprintf(controller_summary_csv,"flow_id,qp_id,total_rounds,direct_hpcc_updates,gated_late_updates,gated_stale_updates,rate_total_variation,minimum_rate,maximum_rate,mean_round_start_rate\n");
	}
	if(!group_round_summary_file.empty()){
		group_round_summary_csv=fopen(group_round_summary_file.c_str(),"w");
		if(!group_round_summary_csv)ConfigError("cannot open GROUP_ROUND_SUMMARY_FILE");
		fprintf(group_round_summary_csv,"scenario,algorithm,seed,group_id,round_id,common_release_time,barrier_completion_time,group_rct,total_round_bytes,participant_count,residual_queue_bytes,bottleneck_capacity_bps,background_bps,T_line,T_link,T_star,theoretical_lower_bound,lower_bound_efficiency,group_queue_max_bytes,group_ecn_marks,group_pfc_events,fallback_reason\n");
	}
		if(!flow_plan_file.empty()){
		flow_plan_csv=fopen(flow_plan_file.c_str(),"w");
		if(!flow_plan_csv)ConfigError("cannot open FLOW_PLAN_FILE");
				if (cc_mode == RdmaHw::CC_MODE_BOP_QC)
					fprintf(flow_plan_csv,"flow_id,group_id,round_id,round_bytes,selected_rate_bps,max_rate_bps,phase_offset_ns,path_or_bottleneck_id,bop_base_rate_bps,qc_credit_bytes,qc_credit_end_seq,burst_rate_bps,switched_to_base,actual_burst_bytes\n");
				else if (RdmaHw::UsesBopQbCredit(cc_mode))
					fprintf(flow_plan_csv,"flow_id,group_id,round_id,round_bytes,selected_rate_bps,max_rate_bps,phase_offset_ns,path_or_bottleneck_id,qb_base_rate_bps,qb_credit_bytes,qb_credit_end_seq,qb_burst_rate_bps,qb_switched_to_base,qb_actual_burst_bytes\n");
				else if (cc_mode == RdmaHw::CC_MODE_BOP_QB_MAX)
					fprintf(flow_plan_csv,"flow_id,group_id,round_id,round_bytes,selected_rate_bps,max_rate_bps,phase_offset_ns,path_or_bottleneck_id,qb_max_base_rate_bps,qb_max_credit_bytes,qb_max_credit_end_seq,qb_max_burst_rate_bps,qb_max_actual_burst_bytes,qb_max_switched_to_base\n");
				else
				fprintf(flow_plan_csv,"flow_id,group_id,round_id,round_bytes,selected_rate_bps,max_rate_bps,phase_offset_ns,path_or_bottleneck_id\n");
		}
		if(!bop_qc_group_decisions_file.empty()){
			bop_qc_group_decisions_csv =
				fopen(bop_qc_group_decisions_file.c_str(),"w");
			if(!bop_qc_group_decisions_csv)
				ConfigError("cannot open BOP_QC_GROUP_DECISIONS_FILE");
			fprintf(bop_qc_group_decisions_csv,"scenario,seed,group_id,round_id,total_round_bytes,participant_count,residual_queue_bytes,queue_sample_age_us,feedback_tau_us,tau_source,bottleneck_capacity_bps,background_bps,ecn_threshold_bytes,packet_margin_bytes,queue_room_bytes,bdp_credit_bytes,group_credit_bytes,total_allocated_credit_bytes,T_star_us,fallback_reason\n");
		}
		if(!bop_qb_group_decisions_file.empty()){
			bop_qb_group_decisions_csv =
				fopen(bop_qb_group_decisions_file.c_str(),"w");
			if(!bop_qb_group_decisions_csv)
				ConfigError("cannot open BOP_QB_GROUP_DECISIONS_FILE");
			fprintf(bop_qb_group_decisions_csv,"scenario,seed,group_id,round_id,participant_count,total_round_bytes,residual_queue_bytes,ecn_threshold_bytes,queue_target_bytes,packet_margin_bytes,queue_room_bytes,group_credit_bytes,total_allocated_credit_bytes,T_star_us,fallback_reason,safety_bound_valid\n");
		}
			if(!bop_qb_max_group_decisions_file.empty()){
			bop_qb_max_group_decisions_csv =
				fopen(bop_qb_max_group_decisions_file.c_str(),"w");
			if(!bop_qb_max_group_decisions_csv)
				ConfigError("cannot open BOP_QB_MAX_GROUP_DECISIONS_FILE");
				fprintf(bop_qb_max_group_decisions_csv,"scenario,seed,group_id,round_id,participant_count,total_group_round_bytes,residual_queue_bytes,queue_sample_time,queue_sample_age_us,ecn_threshold_bytes,packet_margin_bytes,queue_room_bytes,group_credit_bytes,total_allocated_credit_bytes,T_star_us,safety_bound_valid,fallback_reason\n");
			}
			if(!bop_multilink_group_decisions_file.empty()){
				bop_multilink_group_decisions_csv =
					fopen(bop_multilink_group_decisions_file.c_str(),"w");
				if(!bop_multilink_group_decisions_csv)
					ConfigError("cannot open BOP_MULTILINK_GROUP_DECISIONS_FILE");
				fprintf(bop_multilink_group_decisions_csv,
					"scenario,algorithm,seed,group_id,round_id,participant_count,total_round_bytes,alpha,T_star_us,limiting_link_count,formula_valid,capacity_valid,credit_constraint_valid\n");
			}
			if(!bop_multilink_link_constraints_file.empty()){
				bop_multilink_link_constraints_csv =
					fopen(bop_multilink_link_constraints_file.c_str(),"w");
				if(!bop_multilink_link_constraints_csv)
					ConfigError("cannot open BOP_MULTILINK_LINK_CONSTRAINTS_FILE");
				fprintf(bop_multilink_link_constraints_csv,
					"scenario,algorithm,seed,group_id,round_id,link_id,capacity_bps,q0_bytes,ecn_threshold_bytes,flow_count,workload_bytes,queue_room_bytes,credit_sum_bytes,T_link_us,limiting_link,T_star_us,formula_valid,capacity_valid,credit_constraint_valid\n");
			}
		if(!prt_probe_summary_file.empty()){
			prt_probe_summary_csv=fopen(prt_probe_summary_file.c_str(),"w");
			if(!prt_probe_summary_csv)
				ConfigError("cannot open PRT_PROBE_SUMMARY_FILE");
			fprintf(prt_probe_summary_csv,"scenario,seed,group_id,round_id,probe_id,probe_send_time_ns,queue_sample_time_ns,probe_ack_time_ns,release_time_ns,probe_count_sent,returned_before_release,q1_bytes,q2_bytes,slope_bytes_per_ns,q_hat_bytes,actual_q0_bytes,q_error_bytes,fallback_code\n");
		}
		if(!prt_group_decisions_file.empty()){
			prt_group_decisions_csv=fopen(prt_group_decisions_file.c_str(),"w");
			if(!prt_group_decisions_csv)
				ConfigError("cannot open PRT_GROUP_DECISIONS_FILE");
			fprintf(prt_group_decisions_csv,"scenario,seed,group_id,round_id,participant_count,total_round_bytes,probe_count_sent,returned_before_release,q_hat_bytes,actual_q0_bytes,q_error_bytes,fallback_code,original_bop_credit_bytes,prt_credit_bytes,queue_target_bytes,packet_margin_bytes,queue_peak_bytes,audit_type,primer_ecn,collective_ecn,pfc_events,safety_bound_valid\n");
		}
	if(!link_timeseries_file.empty()){
		link_csv=fopen(link_timeseries_file.c_str(),"w");
		if(!link_csv)ConfigError("cannot open LINK_TIMESERIES_FILE");
		fprintf(link_csv,"time,link_id,queue_bytes,utilization,tx_bytes_delta,ecn_marks_delta,pfc_paused,pfc_event_delta\n");
	}
	if(!selected_flow_timeseries_file.empty()){
		selected_csv=fopen(selected_flow_timeseries_file.c_str(),"w");
		if(!selected_csv)ConfigError("cannot open SELECTED_FLOW_TIMESERIES_FILE");
		fprintf(selected_csv,"time,flow_id,round_id,phase,snd_nxt,snd_una,released_bytes,current_rate,feedback_origin_round,feedback_class\n");
	}
	if (!fixed_path_file.empty()){
		if (!fixed_path_output_file.empty()){
			fixed_path_output = fopen(fixed_path_output_file.c_str(), "w");
			if (fixed_path_output == NULL)
				ConfigError("cannot open " + fixed_path_output_file);
			fprintf(fixed_path_output, "flow_index src dst sport dport src_leaf forced_spine out_if start_time\n");
		}
	}
	if (!port_monitor_output_file.empty()){
		if (fixed_path_file.empty())
			ConfigError("port monitor requires FIXED_PATH_FILE");
		if (port_monitor_interval == 0)
			ConfigError("PORT_MONITOR_INTERVAL_NS must be positive");
		port_monitor_output = fopen(port_monitor_output_file.c_str(), "w");
		if (port_monitor_output == NULL)
			ConfigError("cannot open " + port_monitor_output_file);
		fprintf(port_monitor_output, "time_ns node_id peer_id if_index tx_delta_bytes throughput_bps queue_bytes\n");
	}

	//
	// get BDP and delay
	//
	maxRtt = maxBdp = 0;
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() != 0)//非host节点不行
			continue;
		for (uint32_t j = 0; j < node_num; j++){
			if (n.Get(j)->GetNodeType() != 0)
				continue;
			uint64_t delay = pairDelay[n.Get(i)][n.Get(j)];//获取两个host的传输delay
			uint64_t txDelay = pairTxDelay[n.Get(i)][n.Get(j)];//发送delay
			uint64_t rtt = delay * 2 + txDelay;//计算rtt
			uint64_t bw = pairBw[i][j];
			uint64_t bdp = rtt * bw / 1000000000/8; 
			pairBdp[n.Get(i)][n.Get(j)] = bdp;
			pairRtt[i][j] = rtt;
			if (bdp > maxBdp)
				maxBdp = bdp;
			if (rtt > maxRtt)
				maxRtt = rtt;
		}
	}//获取所有host之间的RTT与带宽时延积
	printf("maxRtt=%lu maxBdp=%lu\n", maxRtt, maxBdp);

	//
	// setup switch CC，选择交换机的CC算法以及最大RTT
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 1){ // switch
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
			sw->SetAttribute("CcMode", UintegerValue(cc_mode));
			sw->SetAttribute("MaxRtt", UintegerValue(maxRtt));
		}
	}
		// RdmaDriver::Init connects each host QbbNetDevice with RdmaHw and
		// registers callbacks for receive, send completion, next-packet fetch,
		// link-down handling, and QP completion logging.
	//
	// add trace
	//

	NodeContainer trace_nodes;
	for (uint32_t i = 0; i < trace_num; i++)//这个for主要是读取需要trace的节点，每次读一个节点编号nid
	{
		uint32_t nid;
		tracef >> nid;
		if (nid >= n.GetN()){
			continue;
		}
		trace_nodes = NodeContainer(trace_nodes, n.Get(nid));//将节点id加入到容器中
	}

	FILE *trace_output = fopen(trace_output_file.c_str(), "w");
	if (enable_trace)
		qbb.EnableTracing(trace_output, trace_nodes);//绑定trace回调，也就是将tracenode中的节点开始trace

	// dump link speed to trace file
	{
		SimSetting sim_setting;
		for (auto i: nbr2if){
			for (auto j : i.second){
				uint16_t node = i.first->GetId();
				uint8_t intf = j.second.idx;
				uint64_t bps = DynamicCast<QbbNetDevice>(i.first->GetDevice(j.second.idx))->GetDataRate().GetBitRate();
				sim_setting.port_speed[node][intf] = bps;
			}
		}
		sim_setting.win = maxBdp;
		sim_setting.Serialize(trace_output);
	}

	Ipv4GlobalRoutingHelper::PopulateRoutingTables();

	NS_LOG_INFO("Create Applications.");

	Time interPacketInterval = Seconds(0.0000005 / 2);

	// maintain port number for each host，即初始化每一队host的端口号
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0)
			for (uint32_t j = 0; j < node_num; j++){
				if (n.Get(j)->GetNodeType() == 0)
					portNumder[i][j] = 10000; // each host pair use port number from 10000
			}
	}

	flow_input.idx = 0;//读取flow并开始调度启动
	if (flow_num > 0){
		ReadFlowInput();
		Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
	}

	topof.close();
	tracef.close();

	// schedule link down，文件中还设置了链路断开事件，也就是说可以在这里将链路断开
	if (link_down_time > 0){
		Simulator::Schedule(Seconds(2) + MicroSeconds(link_down_time), &TakeDownLink, n, n.Get(link_down_A), n.Get(link_down_B));
	}

	// schedule buffer monitor
	FILE* qlen_output = fopen(qlen_mon_file.c_str(), "w");
	Simulator::Schedule(NanoSeconds(qlen_mon_start), &monitor_buffer, qlen_output, &n);
	if (port_monitor_output != NULL)
		Simulator::Schedule(NanoSeconds(port_monitor_interval), &MonitorFixedPathPorts);
	if(link_csv)
		Simulator::Schedule(MicroSeconds(crfm_trace_sample_us),&LinkTraceTick);
	if(selected_csv)
		Simulator::Schedule(MicroSeconds(std::max((uint64_t)20,
			crfm_trace_sample_us)),&FlowTraceTick);
	if (cbap_enable){
		RdmaHw::SetCbapPortReadCallback(
			MakeCallback(&ReadCbapPort));
		RdmaHw::StartCbapCoordinator();
	}

	//
	// Now, do the actual simulation.
	//启动仿真
	std::cout << "Running Simulation.\n";
	fflush(stdout);
	NS_LOG_INFO("Run Simulation.");
	Simulator::Stop(Seconds(simulator_stop_time));
	Simulator::Run();
	if (round_mode)
		WriteCrfmSummaries();
	WriteBopMultilinkSummaries();
	WriteCbapSummaries();
	if (final_validation_enable){
		BopFinalValidation::WriteOutputs();
		WriteFinalReleaseQueueSummary();
	}
	WritePfcSemanticSummary();
	Simulator::Destroy();
	NS_LOG_INFO("Done.");
	fclose(trace_output);
	if (fixed_path_output != NULL)
		fclose(fixed_path_output);
	if (port_monitor_output != NULL)
		fclose(port_monitor_output);
	if(flow_summary_csv)fclose(flow_summary_csv);
	if(round_summary_csv)fclose(round_summary_csv);
	if(feedback_summary_csv)fclose(feedback_summary_csv);
	if(controller_summary_csv)fclose(controller_summary_csv);
	if(group_round_summary_csv)fclose(group_round_summary_csv);
		if(flow_plan_csv)fclose(flow_plan_csv);
		if(bop_qc_group_decisions_csv)fclose(bop_qc_group_decisions_csv);
		if(bop_qb_group_decisions_csv)fclose(bop_qb_group_decisions_csv);
		if(bop_qb_max_group_decisions_csv)fclose(bop_qb_max_group_decisions_csv);
		if(bop_multilink_group_decisions_csv)fclose(bop_multilink_group_decisions_csv);
		if(bop_multilink_link_constraints_csv)fclose(bop_multilink_link_constraints_csv);
		if(prt_probe_summary_csv)fclose(prt_probe_summary_csv);
		if(prt_group_decisions_csv)fclose(prt_group_decisions_csv);
	if(link_csv)fclose(link_csv);
	if(selected_csv)fclose(selected_csv);
	if(pfc_csv)fclose(pfc_csv);
	if(pfc_semantic_csv)fclose(pfc_semantic_csv);
	if(cbap_packet_trace_csv)fclose(cbap_packet_trace_csv);

	endt = clock();
	std::cout << (double)(endt - begint) / CLOCKS_PER_SEC << "\n";

}
