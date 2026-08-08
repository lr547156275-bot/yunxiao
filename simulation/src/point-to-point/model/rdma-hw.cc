#include <ns3/simulator.h>
#include <ns3/seq-ts-header.h>
#include <ns3/udp-header.h>
#include <ns3/ipv4-header.h>
#include "ns3/ppp-header.h"
#include "ns3/boolean.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/data-rate.h"
#include "ns3/pointer.h"
#include "rdma-hw.h"
#include "ppp-header.h"
#include "qbb-header.h"
#include "cn-header.h"
#include "wire-padding-header.h"
#include "prt-probe-tag.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace ns3{

std::map<uint32_t, RdmaHw::RoundGroupRuntime> RdmaHw::s_roundGroups;
RdmaHw::RoundQueueReadCallback RdmaHw::s_roundQueueRead;
bool RdmaHw::s_bopMultilinkConfigured = false;
std::map<uint32_t, RdmaHw::BopMultilinkLink>
	RdmaHw::s_bopMultilinkLinks;
std::map<uint32_t, std::vector<uint32_t> >
	RdmaHw::s_bopMultilinkFlowPaths;
std::map<uint32_t, RdmaHw::BopMultilinkObservation>
	RdmaHw::s_bopMultilinkObservations;
std::map<uint32_t, int64_t>
	RdmaHw::s_bopMultilinkGroupPredecessors;
std::map<uint32_t, uint32_t>
	RdmaHw::s_bopMultilinkGroupSuccessors;
std::vector<RdmaHw::BopMultilinkGroupDecision>
	RdmaHw::s_bopMultilinkGroupDecisions;
std::vector<RdmaHw::BopMultilinkLinkDecision>
	RdmaHw::s_bopMultilinkLinkDecisions;
RdmaHw::CbapConfig RdmaHw::s_cbapConfig;
bool RdmaHw::s_cbapStarted = false;
uint32_t RdmaHw::s_cbapEpoch = 0;
RdmaHw::CbapPortReadCallback RdmaHw::s_cbapPortRead;
std::map<uint32_t, RdmaHw::CbapLinkRuntime> RdmaHw::s_cbapLinks;
std::map<uint32_t, std::vector<uint32_t> > RdmaHw::s_cbapFlowPaths;
std::set<uint32_t> RdmaHw::s_cbapSbaMigrationPlanned;
std::set<uint32_t> RdmaHw::s_cbapSbaMigrationActiveSet;
bool RdmaHw::s_cbapSbaMigrationReplanPending = false;
std::map<uint32_t, RdmaHw::CbapFlowRuntime> RdmaHw::s_cbapFlows;
std::map<uint32_t, RdmaHw::CbapScopeBaseFlowRuntime>
	RdmaHw::s_cbapScopeBaseFlows;
std::map<uint32_t, RdmaHw::CbapV20BatchRuntime>
	RdmaHw::s_cbapV20Batches;
CbapSbaController RdmaHw::s_cbapSbaController;
std::vector<RdmaHw::CbapV20BatchRecord>
	RdmaHw::s_cbapV20BatchRecords;
std::vector<RdmaHw::CbapV20FlowRecord>
	RdmaHw::s_cbapV20FlowRecords;
std::vector<RdmaHw::CbapPortRecord> RdmaHw::s_cbapPortRecords;
std::vector<RdmaHw::CbapAdmissionRecord> RdmaHw::s_cbapAdmissionRecords;
std::vector<RdmaHw::CbapRateRecord> RdmaHw::s_cbapRateRecords;
std::vector<RdmaHw::CbapAppliedRateAuditRecord>
	RdmaHw::s_cbapAppliedRateAuditRecords;
std::vector<RdmaHw::CbapIncreaseRecord> RdmaHw::s_cbapIncreaseRecords;
std::vector<RdmaHw::CbapFlowRecord> RdmaHw::s_cbapFlowRecords;
std::vector<RdmaHw::CbapTxRecord> RdmaHw::s_cbapTxRecords;
uint64_t RdmaHw::s_cbapSummaryMessages = 0;
uint64_t RdmaHw::s_cbapGrantMessages = 0;
std::vector<RdmaHw::CbapScopeBatchRecord>
	RdmaHw::s_cbapScopeBatchRecords;
std::vector<RdmaHw::CbapScopeLinkRecord>
	RdmaHw::s_cbapScopeLinkRecords;
std::map<uint32_t, RdmaHw::CbapHandoffBatchRecord>
	RdmaHw::s_cbapHandoffBatches;
std::vector<RdmaHw::CbapHandoffFlowRecord>
	RdmaHw::s_cbapHandoffFlowRecords;
std::vector<RdmaHw::CbapControllerOwnershipRecord>
	RdmaHw::s_cbapControllerOwnershipRecords;
std::vector<RdmaHw::CbapControlMessageRecord>
	RdmaHw::s_cbapControlMessageRecords;
std::vector<RdmaHw::CbapEnvelopeLinkRecord>
	RdmaHw::s_cbapEnvelopeLinkRecords;
std::vector<RdmaHw::CbapEnvelopeFlowRecord>
	RdmaHw::s_cbapEnvelopeFlowRecords;
std::map<uint64_t, uint64_t> RdmaHw::s_cbapEnvelopeLastBudget;
uint64_t RdmaHw::s_cbapLogicalEnvelopeUpdates = 0;
uint64_t RdmaHw::s_cbapLogicalEnvelopeBytes = 0;
std::map<uint32_t, uint64_t> RdmaHw::s_cbapBatchGrantMessages;
std::map<uint32_t, uint64_t> RdmaHw::s_cbapBatchActiveSummaries;
std::map<uint32_t, uint64_t> RdmaHw::s_cbapBatchMonitoringSummaries;

RdmaHw::CbapHandoffBatchRecord::CbapHandoffBatchRecord()
	: batchId(0), applicationReadyNs(0), networkReleaseNs(0),
	  trackingEnterNs(0), firstStableEpochNs(0), handoffCandidateNs(0),
	  handoffExecuteNs(0), handoffOccurred(false),
	  noHandoffReason("not_evaluated"), stableEpochCount(0),
	  measuredRttNs(0), minimumTrackingTimeNs(0), activeFlowCount(0),
	  remainingBytesTotal(0), remainingFraction(0),
	  queueBytesAtHandoff(0), queueGradientAtHandoff(0),
	  appliedRateSumBefore(0), dcqcnRateSumAfterInit(0),
	  maxPerFlowRateJumpBps(0), firstDcqcnRateUpdateNs(0),
	  firstDcqcnCnpNs(0), grantsBeforeHandoff(0),
	  grantsAfterHandoff(0), controlBytesBeforeHandoff(0),
	  controlBytesAfterHandoff(0), shadowHandoffCandidateNs(0),
	  shadowRemainingBytes(0), shadowRemainingFraction(0),
	  shadowQueueBytes(0), shadowRateSumBps(0),
	  shadowControlledAfterCandidateNs(0) {}

RdmaHw::CbapHandoffFlowRecord::CbapHandoffFlowRecord()
	: flowId(0), batchId(0), phaseBefore(0), phaseAfter(0),
	  remainingBytes(0), cbapAppliedRateBefore(0),
	  dcqcnCurrentRateAfter(0), dcqcnTargetRateAfter(0), alphaAfter(0),
	  nextTxBeforeNs(0), nextTxAfterNs(0), firstTxAfterHandoffNs(0),
	  packetGapRequiredNs(0), packetGapActualNs(0),
	  catchupBurstDetected(false) {}

RdmaHw::CbapV20BatchRecord::CbapV20BatchRecord()
	: batchId(0), linkId(0), classification(CBAP_V20_C2_COMPLEX),
	  classificationReason("not_evaluated"), riskyLinkCount(0),
	  blindWindowNs(0), queue0Bytes(0), queueTargetBytes(0),
	  effectiveCapacityBps(0), blindWorkBytes(0),
	  serviceAndBufferBytes(0), excessBytes(0), startupBudgetBps(0),
	  admissionAggregateBps(0), actualAppliedAggregateBps(0),
	  firstFreshFeedbackNs(0), leaseExpiryNs(0), handoffNs(0),
	  handoffReason("not_evaluated"), baseCc("unknown"),
	  postHandoffCbapWriteCount(0), catchUpBurst(false),
	  capacityViolation(false), pacingViolation(false),
	  preReleaseCausal(true) {}

RdmaHw::CbapV20FlowRecord::CbapV20FlowRecord()
	: batchId(0), flowId(0), classification(CBAP_V20_C2_COMPLEX),
	  startupGrantBps(0), pathMinGrantBps(0), appliedRateBps(0),
	  packetGapNs(0), firstFreshFeedbackNs(0),
	  handoffInitialRateBps(0), postHandoffOwner("CBAP"),
	  postHandoffCbapWriteCount(0), catchUpBurst(false) {}

bool RdmaHw::IsDcqcnMode(uint32_t mode)
{
	return mode == 1 || mode == CC_MODE_DCQCN_WIRE_EQUALIZED ||
		mode == CC_MODE_CBAP_INIT_ONLY ||
		mode == CC_MODE_CBAP_FULL_SCOPED ||
		mode == CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
		mode == CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
		mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION ||
		mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ||
		mode == CC_MODE_CBAP_SBA_DCQCN;
}

bool RdmaHw::IsCbapV20Mode(uint32_t mode)
{
	return mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ||
		mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC;
}

bool RdmaHw::IsBopQbMode(uint32_t mode)
{
	return mode == CC_MODE_BOP_QB || mode == CC_MODE_BOP_QB_ORACLE_Q0;
}

bool RdmaHw::UsesBopQbCredit(uint32_t mode)
{
	return IsBopQbMode(mode) || mode == CC_MODE_BOP_QB_PRT;
}

bool RdmaHw::UsesHpccTelemetryMode(uint32_t mode)
{
	return mode == 3 ||
		(mode >= CC_MODE_HPCC_ROUND_RESET && mode <= CC_MODE_BOP_QB_MAX) ||
		mode == CC_MODE_BOP_QB_ORACLE_Q0 ||
		mode == CC_MODE_BOP_QB_PRT ||
		mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC ||
		mode == CC_MODE_CBAP_SBA_HPCC;
}

// SBA startup admission and capacity migration are shared by both post-handoff
// controllers; only the handoff target differs.
bool RdmaHw::IsCbapSbaMode(uint32_t mode)
{
	return mode == CC_MODE_CBAP_SBA_DCQCN || mode == CC_MODE_CBAP_SBA_HPCC;
}

bool RdmaHw::IsCbapMode(uint32_t mode)
{
	return mode >= CC_MODE_CBAP_INDEPENDENT &&
		mode <= CC_MODE_CBAP_SBA_HPCC;
}

void RdmaHw::ConfigureBopMultilink(
		bool enabled,
		const std::vector<BopMultilinkLink> &links,
		const std::map<uint32_t, std::vector<uint32_t> > &flowPaths,
		const std::map<uint32_t, int64_t> &groupPredecessors)
{
	s_bopMultilinkConfigured = enabled;
	s_bopMultilinkLinks.clear();
	s_bopMultilinkFlowPaths = flowPaths;
	s_bopMultilinkObservations.clear();
	s_bopMultilinkGroupPredecessors = groupPredecessors;
	s_bopMultilinkGroupSuccessors.clear();
	s_bopMultilinkGroupDecisions.clear();
	s_bopMultilinkLinkDecisions.clear();
	for (uint32_t i = 0; i < links.size(); ++i) {
		NS_ASSERT_MSG(links[i].capacityBps > links[i].backgroundBps &&
				links[i].ecnThresholdBytes > 0,
				"invalid BOP multilink link definition");
		NS_ASSERT_MSG(s_bopMultilinkLinks.insert(
				std::make_pair(links[i].linkId, links[i])).second,
				"duplicate BOP multilink link id");
	}
	for (std::map<uint32_t, std::vector<uint32_t> >::const_iterator path =
			flowPaths.begin(); path != flowPaths.end(); ++path) {
		NS_ASSERT_MSG(!path->second.empty(),
				"BOP multilink flow path is empty");
		for (uint32_t i = 0; i < path->second.size(); ++i)
			NS_ASSERT_MSG(s_bopMultilinkLinks.count(path->second[i]) == 1,
					"BOP multilink path references an unknown link");
	}
	for (std::map<uint32_t, int64_t>::const_iterator group =
			groupPredecessors.begin(); group != groupPredecessors.end();
			++group) {
		if (group->second < 0)
			continue;
		uint32_t predecessor = (uint32_t)group->second;
		NS_ASSERT_MSG(groupPredecessors.count(predecessor) == 1,
				"BOP multilink predecessor is unknown");
		NS_ASSERT_MSG(s_bopMultilinkGroupSuccessors.insert(
				std::make_pair(predecessor, group->first)).second,
				"BOP multilink group dependency is not a chain");
	}
}

const std::vector<RdmaHw::BopMultilinkGroupDecision> &
RdmaHw::GetBopMultilinkGroupDecisions()
{
	return s_bopMultilinkGroupDecisions;
}

const std::vector<RdmaHw::BopMultilinkLinkDecision> &
RdmaHw::GetBopMultilinkLinkDecisions()
{
	return s_bopMultilinkLinkDecisions;
}

bool RdmaHw::HasActiveBopMultilinkGroup()
{
	if (!s_bopMultilinkConfigured)
		return false;
	uint64_t now = Simulator::Now().GetTimeStep();
	for (std::map<uint32_t, RoundGroupRuntime>::const_iterator group =
			s_roundGroups.begin(); group != s_roundGroups.end(); ++group)
		if (group->second.planned && !group->second.barrierComplete &&
				now >= group->second.earliestReleaseNs)
			return true;
	return false;
}

void RdmaHw::ConfigureCbap(const CbapConfig &config,
		const std::vector<BopMultilinkLink> &links,
		const std::map<uint32_t, std::vector<uint32_t> > &flowPaths)
{
	s_cbapConfig = config;
	s_cbapStarted = false;
	s_cbapEpoch = 0;
	s_cbapLinks.clear();
	s_cbapFlowPaths = flowPaths;
	s_cbapSbaMigrationPlanned.clear();
	s_cbapFlows.clear();
	s_cbapScopeBaseFlows.clear();
	s_cbapV20Batches.clear();
	s_cbapSbaController.Reset();
	s_cbapV20BatchRecords.clear();
	s_cbapV20FlowRecords.clear();
	s_cbapPortRecords.clear();
	s_cbapAdmissionRecords.clear();
	s_cbapRateRecords.clear();
	s_cbapAppliedRateAuditRecords.clear();
	s_cbapIncreaseRecords.clear();
	s_cbapFlowRecords.clear();
	s_cbapTxRecords.clear();
	s_cbapScopeBatchRecords.clear();
	s_cbapScopeLinkRecords.clear();
	s_cbapHandoffBatches.clear();
	s_cbapHandoffFlowRecords.clear();
	s_cbapControllerOwnershipRecords.clear();
	s_cbapControlMessageRecords.clear();
	s_cbapEnvelopeLinkRecords.clear();
	s_cbapEnvelopeFlowRecords.clear();
	s_cbapEnvelopeLastBudget.clear();
	s_cbapLogicalEnvelopeUpdates = 0;
	s_cbapLogicalEnvelopeBytes = 0;
	s_cbapBatchGrantMessages.clear();
	s_cbapBatchActiveSummaries.clear();
	s_cbapBatchMonitoringSummaries.clear();
	s_cbapSummaryMessages = 0;
	s_cbapGrantMessages = 0;
	if (!config.enabled)
		return;
	NS_ASSERT_MSG(config.controlEpochNs > 0 &&
			config.planningDelayNs > 0 &&
			config.controlDelayNs > 0 &&
			config.rho > 0 && config.rho <= 1 &&
			config.epsilonRate > 0 &&
			config.maxWirePacketBytes > 0 &&
			config.increasePolicy <= CBAP_INCREASE_ADAPTIVE_V11 &&
			config.scopePolicy <=
				CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION &&
			config.rateFloorPolicy <=
				CBAP_RATE_FLOOR_EXACT_GRANT_PACING &&
			config.scopeBaseCc == 1 &&
			(!config.handoffEnabled ||
			 (config.handoffStableEpochsRequired == 2 &&
			  config.handoffBaseCc == 1)) &&
			(!config.rateFloorSemanticZeroTest ||
			 (config.rateFloorPolicy == CBAP_RATE_FLOOR_EXACT_GRANT_PACING &&
			  config.rateFloorSemanticZeroStartEpoch > 0 &&
			  config.rateFloorSemanticZeroEndEpoch >
				config.rateFloorSemanticZeroStartEpoch)) &&
			(config.queueTargetFraction == 0.0 ||
			 std::fabs(config.queueTargetFraction - 0.125) < 1e-12 ||
			 std::fabs(config.queueTargetFraction - 0.25) < 1e-12 ||
			 std::fabs(config.queueTargetFraction - 0.5) < 1e-12 ||
			 std::fabs(config.queueTargetFraction - 0.75) < 1e-12) &&
			std::fabs(config.increaseFraction - 0.10) < 1e-12 &&
			config.increaseAbsoluteBps == UINT64_C(2000000000),
			"invalid CBAP configuration");
	for (uint32_t i = 0; i < links.size(); ++i){
		NS_ASSERT_MSG(links[i].capacityBps > links[i].backgroundBps &&
				links[i].ecnThresholdBytes > 0,
				"invalid CBAP controlled link");
		CbapLinkRuntime runtime;
		runtime.config = links[i];
		runtime.previousEffectiveCapacityBps =
			(uint64_t)std::floor(config.rho *
				links[i].capacityBps - links[i].backgroundBps);
		runtime.plannerCapacityBps = runtime.previousEffectiveCapacityBps;
		NS_ASSERT_MSG(s_cbapLinks.insert(std::make_pair(
				links[i].linkId, runtime)).second,
				"duplicate CBAP link id");
	}
	NS_ASSERT_MSG(!s_cbapLinks.empty(), "CBAP requires controlled links");
	for (std::map<uint32_t, std::vector<uint32_t> >::const_iterator path =
			flowPaths.begin(); path != flowPaths.end(); ++path){
		NS_ASSERT_MSG(!path->second.empty(), "CBAP flow path is empty");
		for (uint32_t i = 0; i < path->second.size(); ++i)
			NS_ASSERT_MSG(s_cbapLinks.count(path->second[i]) == 1,
				"CBAP path references unknown link");
	}
}

void RdmaHw::SetCbapPortReadCallback(CbapPortReadCallback callback)
{
	s_cbapPortRead = callback;
}

void RdmaHw::StartCbapCoordinator()
{
	if (!s_cbapConfig.enabled || s_cbapStarted)
		return;
	NS_ASSERT_MSG(!s_cbapPortRead.IsNull(),
			"CBAP port snapshot callback is not installed");
	s_cbapStarted = true;
	Simulator::Schedule(NanoSeconds(s_cbapConfig.controlEpochNs),
		&RdmaHw::CbapEpochTick);
}

const std::vector<RdmaHw::CbapPortRecord> &
RdmaHw::GetCbapPortRecords()
{
	return s_cbapPortRecords;
}

const std::vector<RdmaHw::CbapAdmissionRecord> &
RdmaHw::GetCbapAdmissionRecords()
{
	return s_cbapAdmissionRecords;
}

const std::vector<RdmaHw::CbapRateRecord> &
RdmaHw::GetCbapRateRecords()
{
	return s_cbapRateRecords;
}

const std::vector<RdmaHw::CbapAppliedRateAuditRecord> &
RdmaHw::GetCbapAppliedRateAuditRecords()
{
	return s_cbapAppliedRateAuditRecords;
}

const std::vector<RdmaHw::CbapIncreaseRecord> &
RdmaHw::GetCbapIncreaseRecords()
{
	return s_cbapIncreaseRecords;
}

const std::vector<RdmaHw::CbapFlowRecord> &
RdmaHw::GetCbapFlowRecords()
{
	return s_cbapFlowRecords;
}

const std::vector<RdmaHw::CbapTxRecord> &
RdmaHw::GetCbapTxRecords()
{
	return s_cbapTxRecords;
}

uint64_t RdmaHw::GetCbapSummaryMessageCount()
{
	return s_cbapSummaryMessages;
}

uint64_t RdmaHw::GetCbapGrantMessageCount()
{
	return s_cbapGrantMessages;
}

const std::vector<RdmaHw::CbapScopeBatchRecord> &
RdmaHw::GetCbapScopeBatchRecords()
{
	return s_cbapScopeBatchRecords;
}

const std::vector<RdmaHw::CbapScopeLinkRecord> &
RdmaHw::GetCbapScopeLinkRecords()
{
	return s_cbapScopeLinkRecords;
}

const std::vector<RdmaHw::CbapHandoffBatchRecord> &
RdmaHw::GetCbapHandoffBatchRecords()
{
	static std::vector<CbapHandoffBatchRecord> rows;
	rows.clear();
	for (std::map<uint32_t, CbapHandoffBatchRecord>::const_iterator row =
			s_cbapHandoffBatches.begin(); row != s_cbapHandoffBatches.end(); ++row)
		rows.push_back(row->second);
	return rows;
}

const std::vector<RdmaHw::CbapHandoffFlowRecord> &
RdmaHw::GetCbapHandoffFlowRecords()
{
	return s_cbapHandoffFlowRecords;
}

const std::vector<RdmaHw::CbapControllerOwnershipRecord> &
RdmaHw::GetCbapControllerOwnershipRecords()
{
	return s_cbapControllerOwnershipRecords;
}

const std::vector<RdmaHw::CbapControlMessageRecord> &
RdmaHw::GetCbapControlMessageRecords()
{
	return s_cbapControlMessageRecords;
}

const std::vector<RdmaHw::CbapEnvelopeLinkRecord> &
RdmaHw::GetCbapEnvelopeLinkRecords()
{
	return s_cbapEnvelopeLinkRecords;
}

const std::vector<RdmaHw::CbapEnvelopeFlowRecord> &
RdmaHw::GetCbapEnvelopeFlowRecords()
{
	return s_cbapEnvelopeFlowRecords;
}

const std::vector<RdmaHw::CbapV20BatchRecord> &
RdmaHw::GetCbapV20BatchRecords()
{
	return s_cbapV20BatchRecords;
}

const std::vector<RdmaHw::CbapV20FlowRecord> &
RdmaHw::GetCbapV20FlowRecords()
{
	return s_cbapV20FlowRecords;
}

const std::vector<CbapSbaController::EventRecord> &
RdmaHw::GetCbapSbaEventRecords()
{
	return s_cbapSbaController.GetEvents();
}

std::vector<RdmaHw::CbapIncumbentRecord>
RdmaHw::GetCbapIncumbentRecords()
{
	std::vector<CbapIncumbentRecord> rows;
	uint64_t now = Simulator::Now().GetTimeStep();
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator it =
			s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it){
		if (!it->second.qp)
			continue;
		Ptr<RdmaQueuePair> qp = it->second.qp;
		CbapIncumbentRecord r = {};
		r.timeNs = now; r.flowId = it->first; r.batchId = it->second.batchId;
		r.sizeBytes = qp->m_size; r.sentBytes = qp->snd_nxt;
		r.ackedBytes = qp->snd_una;
		r.remainingBytes = qp->m_size > qp->snd_una ? qp->m_size - qp->snd_una : 0;
		r.currentRateBps = qp->m_rate.GetBitRate();
		r.targetRateBps = qp->cbap.targetRateBps;
		r.protectionFloorBps = qp->cbap.protectionFloorBps;
		r.timeBelow90TargetNs = qp->cbap.timeBelow90TargetNs;
		r.timeBelow80TargetNs = qp->cbap.timeBelow80TargetNs;
		r.timeBelow50TargetNs = qp->cbap.timeBelow50TargetNs;
		r.finished = it->second.finished || qp->IsFinished();
		rows.push_back(r);
	}
	for (std::map<uint32_t, CbapScopeBaseFlowRuntime>::const_iterator it =
			s_cbapScopeBaseFlows.begin(); it != s_cbapScopeBaseFlows.end(); ++it){
		if (!it->second.qp)
			continue;
		Ptr<RdmaQueuePair> qp = it->second.qp;
		CbapIncumbentRecord r = {};
		r.timeNs = now; r.flowId = it->first; r.batchId = 0;
		r.sizeBytes = qp->m_size; r.sentBytes = qp->snd_nxt;
		r.ackedBytes = qp->snd_una;
		r.remainingBytes = qp->m_size > qp->snd_una ? qp->m_size - qp->snd_una : 0;
		r.currentRateBps = qp->m_rate.GetBitRate();
		r.targetRateBps = it->second.protectionFloorBps;
		r.protectionFloorBps = it->second.protectionFloorBps;
		r.finished = qp->IsFinished();
		rows.push_back(r);
	}
	return rows;
}

bool RdmaHw::GetCbapScopeApplicationReadyNs(uint32_t batchId,
		uint64_t &applicationReadyNs)
{
	for (std::vector<CbapScopeBatchRecord>::const_reverse_iterator row =
			s_cbapScopeBatchRecords.rbegin();
			row != s_cbapScopeBatchRecords.rend(); ++row)
		if (row->batchId == batchId){
			applicationReadyNs = row->applicationReadyNs;
			return true;
		}
	std::map<uint32_t, CbapV20BatchRuntime>::const_iterator v20 =
		s_cbapV20Batches.find(batchId);
	std::map<uint32_t, RoundGroupRuntime>::const_iterator group =
		s_roundGroups.find(batchId);
	if (v20 != s_cbapV20Batches.end() && group != s_roundGroups.end()){
		applicationReadyNs = group->second.applicationReadyNs;
		return true;
	}
	const std::vector<CbapSbaController::EventRecord> &sba =
		s_cbapSbaController.GetEvents();
	for (uint32_t i = 0; i < sba.size(); ++i)
		if (sba[i].batchId == batchId && group != s_roundGroups.end()) {
			applicationReadyNs = group->second.applicationReadyNs;
			return true;
		}
	return false;
}

void RdmaHw::SetRoundQueueReadCallback(RoundQueueReadCallback callback)
{
	s_roundQueueRead = callback;
}

RdmaHw::RoundGroupRuntime::RoundGroupRuntime()
	: participantCount(0), roundIndex(0), ackCompleted(0), barrierNs(0),
	  commonReleaseNs(0), applicationReadyNs(0), earliestReleaseNs(0),
	  planScheduled(false),
	  planned(false), barrierComplete(false), queueMaxBytes(0),
	  ecnMarks(0), pfcEvents(0), prtProbeCountSent(0),
	  prtRttHatNs(0), prtPrimerEcn(0), prtCollectiveEcn(0)
{
}

std::map<uint32_t, uint64_t> RdmaHw::ComputeCbapProgressiveFill(
		const std::vector<uint32_t> &flowIds,
		const std::map<uint32_t, uint64_t> &linkCapacity,
		const std::map<uint32_t, uint64_t> &initialRates)
{
	std::map<uint32_t, long double> rates;
	std::set<uint32_t> active;
	for (uint32_t i = 0; i < flowIds.size(); ++i){
		uint32_t flowId = flowIds[i];
		std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.find(flowId);
		NS_ASSERT_MSG(flow != s_cbapFlows.end() && flow->second.qp,
			"progressive filling references unknown CBAP flow");
		std::map<uint32_t, uint64_t>::const_iterator initial =
			initialRates.find(flowId);
		rates[flowId] = initial == initialRates.end() ?
			0 : initial->second;
		if (rates[flowId] + 0.5L <
				flow->second.qp->m_max_rate.GetBitRate())
			active.insert(flowId);
	}
	for (uint32_t iteration = 0;
			!active.empty() && iteration <= flowIds.size(); ++iteration){
		long double step = std::numeric_limits<long double>::max();
		std::map<uint32_t, long double> linkSteps;
		for (std::map<uint32_t, uint64_t>::const_iterator capacity =
				linkCapacity.begin(); capacity != linkCapacity.end();
				++capacity){
			uint32_t count = 0;
			long double used = 0;
			for (uint32_t i = 0; i < flowIds.size(); ++i){
				uint32_t flowId = flowIds[i];
				const std::vector<uint32_t> &path =
					s_cbapFlowPaths[flowId];
				if (std::find(path.begin(), path.end(),
						capacity->first) == path.end())
					continue;
				used += rates[flowId];
				if (active.count(flowId))
					count++;
			}
			if (count == 0)
				continue;
			long double remaining = std::max(0.0L,
				(long double)capacity->second - used);
			linkSteps[capacity->first] = remaining / count;
			step = std::min(step, linkSteps[capacity->first]);
		}
		std::map<uint32_t, long double> maxSteps;
		for (std::set<uint32_t>::const_iterator flowId = active.begin();
				flowId != active.end(); ++flowId){
			long double maximum =
				s_cbapFlows[*flowId].qp->m_max_rate.GetBitRate();
			maxSteps[*flowId] = std::max(0.0L,
				maximum - rates[*flowId]);
			step = std::min(step, maxSteps[*flowId]);
		}
		if (!std::isfinite((double)step) || step <= 0.5L)
			break;
		for (std::set<uint32_t>::const_iterator flowId = active.begin();
				flowId != active.end(); ++flowId)
			rates[*flowId] += step;
		std::set<uint32_t> frozen;
		for (std::set<uint32_t>::const_iterator flowId = active.begin();
				flowId != active.end(); ++flowId){
			if (maxSteps[*flowId] <= step + 0.5L)
				frozen.insert(*flowId);
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[*flowId];
			for (uint32_t hop = 0; hop < path.size(); ++hop)
				if (linkSteps.count(path[hop]) &&
						linkSteps[path[hop]] <= step + 0.5L)
					frozen.insert(*flowId);
		}
		if (frozen.empty())
			break;
		for (std::set<uint32_t>::const_iterator flowId = frozen.begin();
				flowId != frozen.end(); ++flowId)
			active.erase(*flowId);
	}
	std::map<uint32_t, uint64_t> result;
	for (uint32_t i = 0; i < flowIds.size(); ++i){
		uint32_t flowId = flowIds[i];
		uint64_t maximum =
			s_cbapFlows[flowId].qp->m_max_rate.GetBitRate();
		result[flowId] = std::min(maximum,
			(uint64_t)std::floor(std::max(1.0L, rates[flowId])));
	}
	return result;
}

uint64_t RdmaHw::CbapPacketGapNs(uint32_t wireBytes, uint64_t rateBps)
{
	NS_ASSERT_MSG(wireBytes > 0 && rateBps > 0,
		"exact CBAP pacing requires positive bytes and rate");
	long double gap = (long double)wireBytes * 8.0e9L / rateBps;
	NS_ASSERT_MSG(std::isfinite((double)gap) && gap > 0,
		"non-finite exact CBAP packet gap");
	if (gap >= std::numeric_limits<uint64_t>::max())
		return std::numeric_limits<uint64_t>::max();
	return std::max((uint64_t)1, (uint64_t)std::ceil(gap));
}

void RdmaHw::RecordCbapAppliedRateAudit()
{
	const uint64_t legacyFloor = (uint64_t)std::ceil(
		(long double)8 * s_cbapConfig.maxWirePacketBytes * 1e9L /
		s_cbapConfig.controlEpochNs);
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		CbapAppliedRateAuditRecord row = {};
		bool hasActiveControlledFlow = false;
		row.linkId = link->first;
		row.epoch = s_cbapEpoch;
		row.capacityBps = link->second.config.capacityBps;
		row.rhoCapacityBps = (uint64_t)std::floor(
			s_cbapConfig.rho * link->second.config.capacityBps);
		row.effectiveCapacityBps = link->second.plannerCapacityBps;
		row.backgroundRateBps = link->second.config.backgroundBps;
		row.legacyFloorRateBps = legacyFloor;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow){
			if (!flow->second.active || flow->second.finished ||
					!flow->second.qp || flow->second.qp->cbap.handedOff)
				continue;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
			if (std::find(path.begin(), path.end(), link->first) == path.end())
				continue;
			hasActiveControlledFlow = true;
			Ptr<RdmaQueuePair> qp = flow->second.qp;
			uint64_t planner = qp->cbap.phase ==
					RdmaQueuePair::CBAP_ADMISSION_HOLD ?
				qp->cbap.admitRateBps : qp->cbap.targetRateBps;
			uint64_t requested = qp->cbap.requestedRateBps;
			uint64_t applied = qp->cbap.zeroGrantPaused ? 0 :
				qp->m_rate.GetBitRate();
			row.plannerGrantSumBps += planner;
			row.targetRateSumBps += requested;
			row.appliedRateSumBps += applied;
			row.actualTxRateSumBps += qp->cbap.recentActualRateBps[1];
			if (requested > 0 && requested < legacyFloor)
				row.flowsBelowLegacyFloor++;
			if (requested > 0 && requested < legacyFloor &&
					applied > requested){
				row.floorClampCount++;
				row.rateClampDeltaSumBps += applied - requested;
			}
			if (requested == 0)
				row.zeroGrantFlowCount++;
			if (qp->cbap.zeroGrantPaused)
				row.pausedZeroGrantCount++;
		}
		uint64_t tolerance = std::max((uint64_t)1,
			(uint64_t)std::ceil(1e-9L * row.capacityBps));
		row.appliedCapacityExcessBps = row.appliedRateSumBps >
			row.effectiveCapacityBps ? row.appliedRateSumBps -
			row.effectiveCapacityBps : 0;
		row.appliedCapacityViolation = row.appliedCapacityExcessBps >
			tolerance;
		row.actualArrivalExcessBps = row.actualTxRateSumBps >
			row.effectiveCapacityBps ? row.actualTxRateSumBps -
			row.effectiveCapacityBps : 0;
		// An idle link cannot have an applied-rate violation.  Avoid retaining
		// one row per link and epoch outside the controlled-work window; on a
		// Clos topology those idle rows otherwise dominate disk and memory.
		if (hasActiveControlledFlow)
			s_cbapAppliedRateAuditRecords.push_back(row);
	}
}

void RdmaHw::CbapEpochTick()
{
	if (!s_cbapConfig.enabled || !s_cbapStarted)
		return;
	// Stop periodic controller work only after every flow declared by the
	// fixed-path input has registered and completed.  This preserves future
	// releases and multi-round QPs, while avoiding an O(links * flows) idle
	// loop until SIMULATOR_STOP_TIME after the final ACK.
	if (!s_cbapFlowPaths.empty() &&
			s_cbapFlows.size() == s_cbapFlowPaths.size()){
		bool allConfiguredFlowsFinished = true;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
			if (!flow->second.finished){
				allConfiguredFlowsFinished = false;
				break;
			}
		if (allConfiguredFlowsFinished){
			s_cbapStarted = false;
			return;
		}
	}
	s_cbapEpoch++;
	uint64_t now = Simulator::Now().GetTimeStep();
	EvaluateCbapSbaReadmission(now, "control_tick");
	EvaluateCbapSbaLease(now);
	// Migration replan is driven by the active set, not by a one-shot
	// per-batch flag: a new batch arriving, a migrating flow finishing,
	// or any other churn all change the set and trigger a recompute on
	// the next epoch.  Planning cannot happen at PlanCbapSbaBatch time
	// because the flows are not active yet and carry no real rate.
	if (s_cbapConfig.migrationEnabled) {
		std::set<uint32_t> liveFlows;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
				s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
			if (flow->second.active && !flow->second.finished &&
					flow->second.qp && flow->second.qp->cbap.sbaEnabled)
				liveFlows.insert(flow->first);
		if (s_cbapSbaMigrationReplanPending) {
			s_cbapSbaMigrationReplanPending = false;
			ReplanCbapSbaMigrationTargets(now, "deadline_lapsed");
		} else if (liveFlows != s_cbapSbaMigrationActiveSet) {
			const char *why = liveFlows.size() >
					s_cbapSbaMigrationActiveSet.size() ?
				"active_set_grew" : "active_set_shrank";
			ReplanCbapSbaMigrationTargets(now, why);
		}
	}
	EvaluateCbapSbaMigration(now);
	for (std::map<uint32_t, CbapFlowRuntime>::iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow){
		if (!flow->second.active || flow->second.finished ||
				!flow->second.qp)
			continue;
		Ptr<RdmaQueuePair> qp = flow->second.qp;
		uint64_t delta = qp->snd_nxt >= qp->cbap.lastEpochSndNxt ?
			qp->snd_nxt - qp->cbap.lastEpochSndNxt : 0;
		qp->cbap.recentActualRateBps[0] =
			qp->cbap.recentActualRateBps[1];
		qp->cbap.recentActualRateBps[1] =
			(uint64_t)((long double)delta * 8.0e9L /
				s_cbapConfig.controlEpochNs);
		qp->cbap.lastEpochSndNxt = qp->snd_nxt;
		if (qp->cbap.incumbentAuditLastNs > 0 &&
				qp->cbap.targetRateBps > 0 &&
				now > qp->cbap.incumbentAuditLastNs){
			uint64_t elapsed = now - qp->cbap.incumbentAuditLastNs;
			uint64_t rate = qp->m_rate.GetBitRate();
			if (rate * 100 < qp->cbap.targetRateBps * 90)
				qp->cbap.timeBelow90TargetNs += elapsed;
			if (rate * 100 < qp->cbap.targetRateBps * 80)
				qp->cbap.timeBelow80TargetNs += elapsed;
			if (rate * 100 < qp->cbap.targetRateBps * 50)
				qp->cbap.timeBelow50TargetNs += elapsed;
		}
		qp->cbap.incumbentAuditLastNs = now;
	}
	RecordCbapAppliedRateAudit();
	for (std::map<uint32_t, CbapLinkRuntime>::iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		CbapPortSnapshot snapshot = s_cbapPortRead(link->first);
		NS_ASSERT_MSG(snapshot.valid && snapshot.linkId == link->first,
			"CBAP port callback returned invalid link snapshot");
		Simulator::Schedule(NanoSeconds(s_cbapConfig.controlDelayNs),
			&RdmaHw::DeliverCbapPortSummary, link->first, snapshot);
	}
	Simulator::Schedule(NanoSeconds(s_cbapConfig.controlDelayNs + 1),
		&RdmaHw::RecomputeCbapTracking);
	Simulator::Schedule(NanoSeconds(s_cbapConfig.controlEpochNs),
		&RdmaHw::CbapEpochTick);
}

void RdmaHw::DeliverCbapPortSummary(uint32_t linkId,
		CbapPortSnapshot snapshot)
{
	CbapLinkRuntime &runtime = s_cbapLinks[linkId];
	CbapPortRecord record = {};
	record.sampleTimeNs = snapshot.timestampNs;
	record.deliveryTimeNs = Simulator::Now().GetTimeStep();
	record.linkId = linkId;
	record.switchId = snapshot.switchId;
	record.egressPort = snapshot.egressPort;
	record.capacityBps = snapshot.capacityBps;
	record.queueBytes = snapshot.queueBytes;
	record.previousQueueBytes = runtime.initialized ?
		runtime.previousRaw.queueBytes : snapshot.queueBytes;
	record.inputBytesDelta = runtime.initialized &&
		snapshot.ingressBytes >= runtime.previousRaw.ingressBytes ?
		snapshot.ingressBytes - runtime.previousRaw.ingressBytes : 0;
	record.outputBytesDelta = runtime.initialized &&
		snapshot.txBytes >= runtime.previousRaw.txBytes ?
		snapshot.txBytes - runtime.previousRaw.txBytes : 0;
	record.ecnMarksDelta = runtime.initialized &&
		snapshot.ecnMarks >= runtime.previousRaw.ecnMarks ?
		snapshot.ecnMarks - runtime.previousRaw.ecnMarks : 0;
	uint64_t pauseNow = snapshot.pfcPauseEvents +
		snapshot.pfcResumeEvents;
	uint64_t pauseBefore = runtime.initialized ?
		runtime.previousRaw.pfcPauseEvents +
		runtime.previousRaw.pfcResumeEvents : pauseNow;
	record.pfcEventsDelta = pauseNow >= pauseBefore ?
		pauseNow - pauseBefore : 0;
	record.pauseDurationDeltaNs = runtime.initialized &&
		snapshot.pfcPauseDurationNs >=
			runtime.previousRaw.pfcPauseDurationNs ?
		snapshot.pfcPauseDurationNs -
			runtime.previousRaw.pfcPauseDurationNs : 0;
	record.arrivalRateBps = (double)record.inputBytesDelta * 8e9 /
		s_cbapConfig.controlEpochNs;
	record.serviceRateBps = (double)record.outputBytesDelta * 8e9 /
		s_cbapConfig.controlEpochNs;
	record.queueGradientBytesPerSecond =
		((int64_t)record.queueBytes -
		 (int64_t)record.previousQueueBytes) * 1e9 /
		(double)s_cbapConfig.controlEpochNs;
	record.localPaused = snapshot.localPaused;
	record.downstreamPaused = snapshot.downstreamPaused;
	record.stale = !runtime.initialized;
	uint64_t qEcn = runtime.config.ecnThresholdBytes;
	uint64_t qLow = (uint64_t)std::floor(0.25 * qEcn);
	uint64_t qTarget = (uint64_t)std::floor(0.50 * qEcn);
	uint64_t qHigh = (uint64_t)std::floor(0.80 * qEcn);
	double gradientThreshold =
		s_cbapConfig.epsilonRate * snapshot.capacityBps / 8.0;
	bool overload = record.arrivalRateBps >
		(s_cbapConfig.rho + s_cbapConfig.epsilonRate) *
		snapshot.capacityBps;
	bool growing = record.queueBytes >= qTarget &&
		record.queueGradientBytesPerSecond > gradientThreshold;
	runtime.overloadEpochs = overload ?
		runtime.overloadEpochs + 1 : 0;
	runtime.growthEpochs = growing ? runtime.growthEpochs + 1 : 0;
	bool localRoot = !snapshot.downstreamPaused &&
		(runtime.overloadEpochs >= 2 || runtime.growthEpochs >= 2 ||
		 record.queueBytes >= qHigh);
	bool simultaneous = snapshot.downstreamPaused &&
		(runtime.overloadEpochs >= 2 || runtime.growthEpochs >= 2 ||
		 record.queueBytes >= qHigh);
	record.rootReason = record.queueBytes >= qHigh ? 3 :
		(runtime.overloadEpochs >= 2 ? 1 :
		 (runtime.growthEpochs >= 2 ? 2 : 0));
	record.rootId = 0;
	if (!runtime.initialized){
		record.portState = CBAP_PORT_MIXED_OR_UNCERTAIN;
	}else if (simultaneous){
		record.portState = CBAP_PORT_MIXED_OR_UNCERTAIN;
	}else if (localRoot){
		record.portState = CBAP_PORT_ROOT_CONGESTED;
		record.rootId = linkId;
		if (runtime.rootDetectTimeNs == 0)
			runtime.rootDetectTimeNs = record.deliveryTimeNs;
	}else if (snapshot.downstreamPaused){
		record.portState = CBAP_PORT_PROPAGATED;
		for (std::map<uint32_t, CbapLinkRuntime>::const_iterator candidate =
				s_cbapLinks.begin(); candidate != s_cbapLinks.end();
				++candidate)
			if (candidate->second.initialized &&
					candidate->second.latest.portState ==
						CBAP_PORT_ROOT_CONGESTED){
				record.rootId = candidate->first;
				break;
			}
	}else if (record.queueBytes < qLow &&
			record.queueGradientBytesPerSecond <= gradientThreshold){
		record.portState = CBAP_PORT_CLEAR;
	}else if (record.queueBytes >= qLow &&
			record.queueBytes < qTarget &&
			std::fabs(record.queueGradientBytesPerSecond) <=
				gradientThreshold){
		record.portState = CBAP_PORT_STABLE;
	}else{
		record.portState = CBAP_PORT_MIXED_OR_UNCERTAIN;
	}
	runtime.clearStableEpochs =
		record.portState == CBAP_PORT_CLEAR ||
		record.portState == CBAP_PORT_STABLE ?
			runtime.clearStableEpochs + 1 : 0;
	// Scheme-1 batch-to-batch reclaim redesign (dynamic per-link
	// budget): a RED-style three-region tolerance band on queue
	// occupancy, applied to the NEW-FLOW ADMISSION BUDGET (not to
	// existing flows' ECN rate reduction, which DCQCN still owns).
	// Independent of rho and of the portState qLow/qTarget/qHigh
	// classification thresholds above.
	//   Q <  Qmin          -> full residual capacity
	//   Qmin <= Q < Qmax   -> continuous linear decay toward the floor
	//   Q >= Qmax          -> floor; stop releasing extra capacity
	// The decay is continuous at both boundaries (0 at Qmin, exactly
	// maxDrainRatio at Qmax), so there is no step discontinuity.
	uint64_t budgetQMin = (uint64_t)std::floor(
		s_cbapConfig.budgetQLowFraction * qEcn);
	uint64_t budgetQMax = (uint64_t)std::floor(
		s_cbapConfig.budgetQHighFraction * qEcn);
	long double decayFraction;
	if (record.queueBytes < budgetQMin)
		decayFraction = 0.0L;
	else if (budgetQMax > budgetQMin && record.queueBytes < budgetQMax)
		decayFraction = s_cbapConfig.maxDrainRatio *
			(long double)(record.queueBytes - budgetQMin) /
			(long double)(budgetQMax - budgetQMin);
	else
		decayFraction = s_cbapConfig.maxDrainRatio;
	long double effective =
		(long double)snapshot.capacityBps * (1.0L - decayFraction) -
		runtime.config.backgroundBps;
	effective = std::max(0.0L, effective);
	if (record.portState == CBAP_PORT_MIXED_OR_UNCERTAIN)
		effective = std::min(effective,
			(long double)runtime.previousEffectiveCapacityBps);
	record.effectiveCapacityBps =
		(uint64_t)std::floor(effective);
	runtime.previousEffectiveCapacityBps =
		record.effectiveCapacityBps;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow){
		const std::vector<uint32_t> &path =
			s_cbapFlowPaths[flow->first];
		if (std::find(path.begin(), path.end(), linkId) == path.end())
			continue;
		if (flow->second.active && !flow->second.finished &&
				flow->second.qp && !flow->second.qp->cbap.handedOff)
			record.activeControlledFlows++;
		else if (flow->second.planned && !flow->second.active &&
				!flow->second.finished)
			record.pendingControlledFlows++;
	}
	runtime.previousRaw = snapshot;
	runtime.latest = record;
	runtime.initialized = true;
	// Preserve every observation that can affect or describe controlled
	// work, while omitting the unbounded all-link idle tail after completion.
	if (record.activeControlledFlows > 0 ||
			record.pendingControlledFlows > 0)
		s_cbapPortRecords.push_back(record);
	s_cbapSummaryMessages++;
	std::set<uint32_t> activeBatches;
	std::set<uint32_t> monitoringBatches;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow){
		if (!flow->second.active || flow->second.finished || !flow->second.qp)
			continue;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
		if (std::find(path.begin(), path.end(), linkId) == path.end())
			continue;
		if (flow->second.qp->cbap.handedOff)
			monitoringBatches.insert(flow->second.batchId);
		else
			activeBatches.insert(flow->second.batchId);
	}
	for (std::set<uint32_t>::const_iterator batch = activeBatches.begin();
			batch != activeBatches.end(); ++batch)
		s_cbapBatchActiveSummaries[*batch]++;
	for (std::set<uint32_t>::const_iterator batch = monitoringBatches.begin();
			batch != monitoringBatches.end(); ++batch)
		if (!activeBatches.count(*batch))
			s_cbapBatchMonitoringSummaries[*batch]++;
	EvaluateCbapSbaReadmission(record.deliveryTimeNs, "telemetry_update");
}

/*
 * The v1.2 scope predicate is deliberately outside PlanCbapBatch().  That
 * function remains the single implementation of the frozen Full-v1.1
 * allocation, credit, and tracking policy.  This routine performs a
 * read-only counterfactual at application_ready and either enters the
 * frozen planner or schedules the group on the original DCQCN path.
 */
void RdmaHw::PlanScopedCbapBatch(uint32_t groupId)
{
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.planScheduled && !group.planned,
		"scoped CBAP decision callback executed out of order");
	NS_ASSERT_MSG(Simulator::Now().GetTimeStep() ==
		group.applicationReadyNs,
		"scoped CBAP decision did not run at application_ready");
	NS_ASSERT_MSG(s_cbapConfig.scopePolicy ==
		CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION,
		"scoped CBAP mode requires structural scope policy");

	std::vector<uint32_t> pending;
	std::map<uint32_t, Ptr<RdmaQueuePair> > pendingQp;
	std::set<uint32_t> usedLinks;
	for (uint32_t i = 0; i < group.members.size(); ++i){
		RoundGroupMember &member = group.members[i];
		NS_ASSERT_MSG(member.hw->m_cc_mode == CC_MODE_CBAP_FULL_SCOPED ||
				member.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
				member.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
				member.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_GUARDED_DELEGATION,
			"mixed algorithm in scoped CBAP batch");
		uint32_t flowId = member.qp->crfm.flowId;
		NS_ASSERT_MSG(s_cbapFlowPaths.count(flowId),
			"scoped CBAP flow lacks an explicit path");
		pending.push_back(flowId);
		pendingQp[flowId] = member.qp;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[flowId];
		usedLinks.insert(path.begin(), path.end());
	}

	std::vector<uint32_t> incumbents;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
		if (flow->second.active && !flow->second.finished)
			incumbents.push_back(flow->first);
	std::vector<uint32_t> baseIncumbents;
	for (std::map<uint32_t, CbapScopeBaseFlowRuntime>::const_iterator flow =
			s_cbapScopeBaseFlows.begin();
			flow != s_cbapScopeBaseFlows.end(); ++flow)
		if (flow->second.qp &&
				flow->second.qp->crfm.currentRoundIndex >= 0 &&
				flow->second.qp->snd_una <
					flow->second.qp->crfm.releasedBytes)
			baseIncumbents.push_back(flow->first);

	std::map<uint32_t, uint64_t> effective;
	std::map<uint32_t, uint64_t> queue;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		effective[link->first] = link->second.initialized ?
			link->second.latest.effectiveCapacityBps :
			link->second.previousEffectiveCapacityBps;
		queue[link->first] = link->second.initialized ?
			link->second.latest.queueBytes : 0;
	}
	std::map<uint32_t, uint64_t> candidateFloor;
	for (uint32_t i = 0; i < incumbents.size(); ++i){
		Ptr<RdmaQueuePair> qp = s_cbapFlows[incumbents[i]].qp;
		uint64_t measured = (qp->cbap.recentActualRateBps[0] +
			qp->cbap.recentActualRateBps[1]) / 2;
		if (measured == 0)
			measured = qp->m_rate.GetBitRate();
		candidateFloor[incumbents[i]] =
			(uint64_t)std::floor(0.90L * measured);
	}
	for (uint32_t i = 0; i < baseIncumbents.size(); ++i)
		candidateFloor[baseIncumbents[i]] = (uint64_t)std::floor(
			0.90L * s_cbapScopeBaseFlows[baseIncumbents[i]].qp->
			m_rate.GetBitRate());
	std::map<uint32_t, double> linkScale;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		long double sum = 0;
		for (uint32_t i = 0; i < incumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[incumbents[i]];
			if (std::find(path.begin(), path.end(), link->first) !=
					path.end())
				sum += candidateFloor[incumbents[i]];
		}
		for (uint32_t i = 0; i < baseIncumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[baseIncumbents[i]];
			if (std::find(path.begin(), path.end(), link->first) !=
					path.end())
				sum += candidateFloor[baseIncumbents[i]];
		}
		linkScale[link->first] = sum > effective[link->first] && sum > 0 ?
			(double)((long double)effective[link->first] / sum) : 1.0;
	}
	std::map<uint32_t, uint64_t> floor;
	for (uint32_t i = 0; i < incumbents.size(); ++i){
		double scale = 1.0;
		const std::vector<uint32_t> &path =
			s_cbapFlowPaths[incumbents[i]];
		for (uint32_t hop = 0; hop < path.size(); ++hop)
			scale = std::min(scale, linkScale[path[hop]]);
		floor[incumbents[i]] = (uint64_t)std::floor(
			candidateFloor[incumbents[i]] * scale);
	}
	for (uint32_t i = 0; i < baseIncumbents.size(); ++i){
		double scale = 1.0;
		const std::vector<uint32_t> &path =
			s_cbapFlowPaths[baseIncumbents[i]];
		for (uint32_t hop = 0; hop < path.size(); ++hop)
			scale = std::min(scale, linkScale[path[hop]]);
		floor[baseIncumbents[i]] = (uint64_t)std::floor(
			candidateFloor[baseIncumbents[i]] * scale);
	}
	std::map<uint32_t, uint64_t> admitCapacity = effective;
	std::map<uint32_t, uint64_t> scopeBaseCapacity;
	for (std::map<uint32_t, uint64_t>::iterator capacity =
			admitCapacity.begin(); capacity != admitCapacity.end();
			++capacity){
		uint64_t used = 0;
		for (uint32_t i = 0; i < incumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[incumbents[i]];
			if (std::find(path.begin(), path.end(), capacity->first) !=
					path.end())
				used += floor[incumbents[i]];
		}
		for (uint32_t i = 0; i < baseIncumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[baseIncumbents[i]];
			if (std::find(path.begin(), path.end(), capacity->first) !=
					path.end())
				used += floor[baseIncumbents[i]];
		}
		capacity->second = used < capacity->second ?
			capacity->second - used : 0;
		scopeBaseCapacity[capacity->first] = capacity->second;
		uint32_t count = 0;
		uint64_t horizon = 0;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), capacity->first) ==
					path.end())
				continue;
			count++;
			horizon = std::max(horizon,
				pendingQp[pending[i]]->m_baseRtt +
				s_cbapConfig.controlDelayNs);
		}
		uint64_t margin = (uint64_t)count *
			s_cbapConfig.maxWirePacketBytes;
		uint64_t target = (uint64_t)std::floor(0.50 *
			s_cbapLinks[capacity->first].config.ecnThresholdBytes);
		uint64_t room = queue[capacity->first] < target &&
			margin < target - queue[capacity->first] ?
			target - queue[capacity->first] - margin : 0;
		long double temporary = (long double)8 * room * 1e9L /
			std::max((uint64_t)1, horizon);
		uint64_t queueRate = temporary >
			std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(temporary);
		capacity->second = capacity->second <=
			std::numeric_limits<uint64_t>::max() - queueRate ?
			capacity->second + queueRate :
			std::numeric_limits<uint64_t>::max();
	}

	std::map<uint32_t, uint64_t> independentRate;
	for (uint32_t i = 0; i < pending.size(); ++i){
		uint64_t rate = pendingQp[pending[i]]->m_max_rate.GetBitRate();
		const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
		for (uint32_t hop = 0; hop < path.size(); ++hop){
			uint32_t linkId = path[hop];
			uint64_t target = (uint64_t)std::floor(0.50 *
				s_cbapLinks[linkId].config.ecnThresholdBytes);
			uint64_t margin = s_cbapConfig.maxWirePacketBytes;
			uint64_t room = queue[linkId] < target &&
				margin < target - queue[linkId] ?
				target - queue[linkId] - margin : 0;
			uint64_t horizon = std::max((uint64_t)1,
				pendingQp[pending[i]]->m_baseRtt +
				s_cbapConfig.controlDelayNs);
			long double temporary = (long double)8 * room * 1e9L /
				horizon;
			uint64_t queueRate = temporary >
				std::numeric_limits<uint64_t>::max() ?
				std::numeric_limits<uint64_t>::max() :
				(uint64_t)std::floor(temporary);
			uint64_t localAdmit = scopeBaseCapacity[linkId] <=
				std::numeric_limits<uint64_t>::max() - queueRate ?
				scopeBaseCapacity[linkId] + queueRate :
				std::numeric_limits<uint64_t>::max();
			rate = std::min(rate, localAdmit);
		}
		independentRate[pending[i]] = std::max((uint64_t)1, rate);
	}

	bool enabled = false;
	uint32_t triggerCount = 0;
	uint32_t maximumPending = 0;
	double maximumRatio = 0;
	for (std::set<uint32_t>::const_iterator linkId = usedLinks.begin();
			linkId != usedLinks.end(); ++linkId){
		uint32_t count = 0;
		uint64_t aggregate = 0;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), *linkId) == path.end())
				continue;
			count++;
			aggregate = aggregate <=
				std::numeric_limits<uint64_t>::max() -
				independentRate[pending[i]] ?
				aggregate + independentRate[pending[i]] :
				std::numeric_limits<uint64_t>::max();
		}
		uint64_t capacity = admitCapacity[*linkId];
		uint64_t tolerance = std::max((uint64_t)1,
			(uint64_t)std::ceil(1e-9 *
			s_cbapLinks[*linkId].config.capacityBps));
		bool linkEnabled = count >= 2 && aggregate > capacity &&
			aggregate - capacity > tolerance;
		if (linkEnabled){
			enabled = true;
			triggerCount++;
		}
		maximumPending = std::max(maximumPending, count);
		double ratio = (double)aggregate /
			std::max((uint64_t)1, capacity);
		maximumRatio = std::max(maximumRatio, ratio);
		const CbapLinkRuntime &runtime = s_cbapLinks[*linkId];
		CbapScopeLinkRecord row = {};
		row.batchId = groupId;
		row.applicationReadyNs = group.applicationReadyNs;
		row.newestSummarySampleNs = runtime.initialized ?
			runtime.latest.sampleTimeNs : 0;
		row.newestSummaryDeliveryNs = runtime.initialized ?
			runtime.latest.deliveryTimeNs : 0;
		row.linkId = *linkId;
		row.switchId = runtime.config.nodeId;
		row.egressPort = runtime.config.ifIndex;
		row.pendingCount = count;
		row.admissionCapacityBps = capacity;
		row.independentAggregateBps = aggregate;
		row.oversubscriptionBps = aggregate > capacity ?
			aggregate - capacity : 0;
		row.oversubscriptionRatio = ratio;
		row.enabledOnLink = linkEnabled;
		row.preReleaseCausal = !runtime.initialized ||
			(runtime.latest.sampleTimeNs <= group.applicationReadyNs &&
			 runtime.latest.deliveryTimeNs <= group.applicationReadyNs);
		NS_ASSERT_MSG(row.preReleaseCausal,
			"scope decision attempted to use post-ready telemetry");
		s_cbapScopeLinkRecords.push_back(row);
	}

	CbapScopeBatchRecord batch = {};
	batch.batchId = groupId;
	batch.applicationReadyNs = group.applicationReadyNs;
	batch.decisionCompleteNs = group.commonReleaseNs;
	batch.decisionDelayNs = group.commonReleaseNs -
		group.applicationReadyNs;
	batch.flowCount = pending.size();
	batch.usedLinkCount = usedLinks.size();
	batch.enabled = enabled;
	batch.reason = enabled ?
		CBAP_SCOPE_REASON_SHARED_BATCH_OVERSUBSCRIBED :
		(maximumPending < 2 ? CBAP_SCOPE_REASON_NO_SHARED_LINK :
		 CBAP_SCOPE_REASON_WITHIN_ADMISSION_CAPACITY);
	batch.triggeringLinkCount = triggerCount;
	batch.maximumPendingCount = maximumPending;
	batch.maximumOversubscriptionRatio = maximumRatio;
	NS_ASSERT_MSG(batch.decisionDelayNs == UINT64_C(5000),
		"v1.2 scope decision delay must be exactly 5 us");
	s_cbapScopeBatchRecords.push_back(batch);

	if (enabled){
		PlanCbapBatch(groupId);
	}else{
		for (uint32_t i = 0; i < pending.size(); ++i){
			CbapScopeBaseFlowRuntime base;
			base.qp = pendingQp[pending[i]];
			base.flowId = pending[i];
			s_cbapScopeBaseFlows[pending[i]] = base;
		}
		Simulator::Schedule(NanoSeconds(group.earliestReleaseNs -
			Simulator::Now().GetTimeStep()),
			&RdmaHw::PlanRoundGroup, groupId);
	}
}

/*
 * CBAP-v2.0 is intentionally separate from the frozen v1.x planner.  It
 * performs one causal, group-wide startup decision and never enters the
 * legacy TRACKING/RECOVERY controller.
 */
void RdmaHw::PlanCbapV20Batch(uint32_t groupId)
{
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.planScheduled && !group.planned,
		"CBAP-v2.0 batch plan callback executed out of order");
	NS_ASSERT_MSG(Simulator::Now().GetTimeStep() == group.applicationReadyNs,
		"CBAP-v2.0 classification did not run at application_ready");
	NS_ASSERT_MSG(!group.members.empty() &&
		IsCbapV20Mode(group.members.front().hw->m_cc_mode),
		"CBAP-v2.0 planner received a non-v2.0 group");

	std::vector<uint32_t> pending;
	std::map<uint32_t, Ptr<RdmaQueuePair> > qps;
	std::map<uint32_t, uint32_t> linkFlowCount;
	for (uint32_t i = 0; i < group.members.size(); ++i){
		RoundGroupMember &member = group.members[i];
		NS_ASSERT_MSG(member.hw->m_cc_mode ==
			group.members.front().hw->m_cc_mode,
			"mixed base CC in a CBAP-v2.0 batch");
		uint32_t flowId = member.qp->crfm.flowId;
		NS_ASSERT_MSG(s_cbapFlowPaths.count(flowId) &&
			!s_cbapFlowPaths[flowId].empty(),
			"CBAP-v2.0 requires an explicit non-empty fixed path");
		CbapFlowRuntime &flow = s_cbapFlows[flowId];
		NS_ASSERT_MSG(!flow.planned, "CBAP-v2.0 flow planned twice");
		flow.hw = member.hw;
		flow.qp = member.qp;
		flow.flowId = flowId;
		flow.batchId = groupId;
		flow.roundIndex = member.roundIndex;
		flow.planned = true;
		pending.push_back(flowId);
		qps[flowId] = member.qp;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[flowId];
		for (uint32_t hop = 0; hop < path.size(); ++hop)
			linkFlowCount[path[hop]]++;
	}

	std::map<uint32_t, uint64_t> effective, queue0, target, margin;
	std::map<uint32_t, uint64_t> blind, work, service, excess, startup;
	uint32_t riskyLinks = 0;
	bool hasSharedLink = false;
	bool sharedSummaryUnavailable = false;
	uint64_t maximumBlind = 1;
	for (std::map<uint32_t, uint32_t>::const_iterator used =
			linkFlowCount.begin(); used != linkFlowCount.end(); ++used){
		uint32_t linkId = used->first;
		CbapLinkRuntime &link = s_cbapLinks[linkId];
		if (link.initialized){
			NS_ASSERT_MSG(link.latest.sampleTimeNs <= group.applicationReadyNs &&
				link.latest.deliveryTimeNs <= group.applicationReadyNs,
				"CBAP-v2.0 attempted to read future link telemetry");
			queue0[linkId] = link.latest.queueBytes;
			effective[linkId] = link.latest.effectiveCapacityBps;
		}else{
			queue0[linkId] = 0;
			effective[linkId] = link.previousEffectiveCapacityBps;
		}
		target[linkId] = (uint64_t)std::floor(
			s_cbapConfig.queueTargetFraction *
			link.config.ecnThresholdBytes);
		margin[linkId] = (uint64_t)used->second *
			s_cbapConfig.maxWirePacketBytes;
		uint64_t horizon = 1;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), linkId) != path.end())
				horizon = std::max(horizon, qps[pending[i]]->m_baseRtt);
		}
		uint64_t pipeline = link.initialized &&
			link.latest.deliveryTimeNs >= link.latest.sampleTimeNs ?
			link.latest.deliveryTimeNs - link.latest.sampleTimeNs :
			std::max(s_cbapConfig.controlEpochNs,
				s_cbapConfig.controlDelayNs);
		blind[linkId] = std::max(horizon, std::max((uint64_t)1, pipeline));
		maximumBlind = std::max(maximumBlind, blind[linkId]);
		if (used->second >= 2){
			hasSharedLink = true;
			uint64_t staleLimit = std::max(
				(uint64_t)2 * s_cbapConfig.controlEpochNs,
				blind[linkId]);
			sharedSummaryUnavailable = sharedSummaryUnavailable ||
				!link.initialized ||
				(group.applicationReadyNs > link.latest.deliveryTimeNs &&
				 group.applicationReadyNs - link.latest.deliveryTimeNs >
					staleLimit);
		}

		long double linkWork = 0;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), linkId) == path.end())
				continue;
			uint64_t singleMargin = s_cbapConfig.maxWirePacketBytes;
			uint64_t singleRoom = target[linkId] > queue0[linkId] &&
				target[linkId] - queue0[linkId] > singleMargin ?
				target[linkId] - queue0[linkId] - singleMargin : 0;
			long double extra = (long double)8 * singleRoom * 1e9L /
				blind[linkId];
			long double independent = std::min((long double)
				qps[pending[i]]->m_max_rate.GetBitRate(),
				(long double)effective[linkId] + extra);
			RdmaQueuePair::CrfmRoundState &round =
				qps[pending[i]]->crfm.rounds[
					s_cbapFlows[pending[i]].roundIndex];
			linkWork += std::min((long double)round.roundBytes,
				independent * blind[linkId] / 8.0e9L);
		}
		work[linkId] = linkWork >= std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(linkWork);
		uint64_t room = target[linkId] > queue0[linkId] &&
			target[linkId] - queue0[linkId] > margin[linkId] ?
			target[linkId] - queue0[linkId] - margin[linkId] : 0;
		long double serviceBytes = (long double)effective[linkId] *
			blind[linkId] / 8.0e9L + room;
		service[linkId] = serviceBytes >=
			std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(serviceBytes);
		excess[linkId] = work[linkId] > service[linkId] ?
			work[linkId] - service[linkId] : 0;
		if (used->second >= 2 && excess[linkId] > margin[linkId])
			riskyLinks++;

		long double signedRoom = (long double)target[linkId] -
			queue0[linkId] - margin[linkId];
		long double candidate = (long double)effective[linkId] +
			8.0e9L * signedRoom / blind[linkId];
		candidate = std::max((long double)0, candidate);
		startup[linkId] = candidate >=
			std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(candidate);
	}

	CbapV20BatchRuntime &runtime = s_cbapV20Batches[groupId];
	runtime.riskyLinkCount = riskyLinks;
	runtime.releaseNs = group.commonReleaseNs;
	runtime.blindWindowNs = maximumBlind;
	runtime.leaseExpiryNs = group.commonReleaseNs + 2 * maximumBlind;
	runtime.classification = !hasSharedLink ? CBAP_V20_C0_NO_RISK :
		(sharedSummaryUnavailable ? CBAP_V20_C2_COMPLEX :
		 (riskyLinks == 0 ? CBAP_V20_C0_NO_RISK :
		  (riskyLinks == 1 ? CBAP_V20_C1_SINGLE_HOTSPOT :
		   CBAP_V20_C2_COMPLEX)));
	runtime.bypass = runtime.classification == CBAP_V20_C0_NO_RISK;
	runtime.handoffReason = runtime.bypass ? "c0_bypass" :
		"awaiting_fresh_feedback";
	std::string classificationReason = !hasSharedLink ?
		"no_shared_pending_link" :
		(sharedSummaryUnavailable ? "shared_path_summary_missing_or_stale" :
		(runtime.bypass ? "blind_window_excess_within_packet_margin" :
		(runtime.classification == CBAP_V20_C1_SINGLE_HOTSPOT ?
		 "one_risky_shared_link" : "multiple_risky_links_path_min")));

	std::map<uint32_t, uint64_t> emptyInitial;
	std::map<uint32_t, uint64_t> grants;
	if (!runtime.bypass)
		grants = ComputeCbapProgressiveFill(pending, startup, emptyInitial);
	else
		for (uint32_t i = 0; i < pending.size(); ++i)
			grants[pending[i]] = qps[pending[i]]->m_max_rate.GetBitRate();

	for (uint32_t i = 0; i < pending.size(); ++i){
		uint32_t flowId = pending[i];
		CbapFlowRuntime &flow = s_cbapFlows[flowId];
		Ptr<RdmaQueuePair> qp = flow.qp;
		qp->cbap.enabled = true;
		qp->cbap.v20Enabled = true;
		qp->cbap.v20Classification = runtime.classification;
		qp->cbap.v20BaseCc = flow.hw->m_cc_mode ==
			CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ? 1 : 3;
		qp->cbap.v20BlindWindowNs = maximumBlind;
		qp->cbap.v20LeaseExpiryNs = runtime.leaseExpiryNs;
		qp->cbap.batchId = groupId;
		qp->cbap.phase = RdmaQueuePair::CBAP_PREPARE;
		qp->cbap.applicationReadyNs = group.applicationReadyNs;
		qp->cbap.networkReleaseNs = group.commonReleaseNs;
		qp->cbap.baseRateBps = grants[flowId];
		qp->cbap.admitRateBps = grants[flowId];
		qp->cbap.targetRateBps = grants[flowId];
		qp->cbap.initialAdmitRateBps = grants[flowId];
		qp->cbap.fullCredit = false;
		qp->cbap.creditGateActive = false;
		qp->cbap.handedOff = runtime.bypass;
		if (!runtime.bypass)
			SetCbapRate(flow, grants[flowId], 8, 0, false);

		CbapV20FlowRecord row;
		row.batchId = groupId;
		row.flowId = flowId;
		row.classification = runtime.classification;
		row.startupGrantBps = grants[flowId];
		row.pathMinGrantBps = grants[flowId];
		row.appliedRateBps = qp->m_rate.GetBitRate();
		row.packetGapNs = CbapPacketGapNs(
			s_cbapConfig.maxWirePacketBytes,
			std::max((uint64_t)1, row.appliedRateBps));
		row.postHandoffOwner = runtime.bypass ?
			(qp->cbap.v20BaseCc == 1 ? "DCQCN" : "HPCC_INT") : "CBAP";
		s_cbapV20FlowRecords.push_back(row);
		s_cbapGrantMessages += runtime.bypass ? 0 : 1;
		if (!runtime.bypass)
			s_cbapBatchGrantMessages[groupId]++;
	}

	for (std::map<uint32_t, uint32_t>::const_iterator used =
			linkFlowCount.begin(); used != linkFlowCount.end(); ++used){
		uint64_t aggregate = 0;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), used->first) != path.end())
				aggregate += grants[pending[i]];
		}
		CbapV20BatchRecord row;
		row.batchId = groupId;
		row.linkId = used->first;
		row.classification = runtime.classification;
		row.classificationReason = classificationReason;
		row.riskyLinkCount = riskyLinks;
		row.blindWindowNs = blind[used->first];
		row.queue0Bytes = queue0[used->first];
		row.queueTargetBytes = target[used->first];
		row.effectiveCapacityBps = effective[used->first];
		row.blindWorkBytes = work[used->first];
		row.serviceAndBufferBytes = service[used->first];
		row.excessBytes = excess[used->first];
		row.startupBudgetBps = startup[used->first];
		row.admissionAggregateBps = aggregate;
		row.actualAppliedAggregateBps = aggregate;
		row.leaseExpiryNs = runtime.leaseExpiryNs;
		row.handoffReason = runtime.handoffReason;
		row.baseCc = group.members.front().hw->m_cc_mode ==
			CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ? "DCQCN" : "HPCC_INT";
		row.preReleaseCausal = !s_cbapLinks[used->first].initialized ||
			(s_cbapLinks[used->first].latest.sampleTimeNs <=
			 group.applicationReadyNs &&
			 s_cbapLinks[used->first].latest.deliveryTimeNs <=
			 group.applicationReadyNs);
		long double predictedQueue = (long double)queue0[used->first] +
			((long double)aggregate - effective[used->first]) *
			blind[used->first] / 8.0e9L;
		predictedQueue = std::max((long double)0, predictedQueue);
		row.capacityViolation = !runtime.bypass && predictedQueue >
			(long double)target[used->first] + margin[used->first] + 1;
		s_cbapV20BatchRecords.push_back(row);
	}

	if (!runtime.bypass){
		uint64_t now = Simulator::Now().GetTimeStep();
		NS_ASSERT_MSG(runtime.leaseExpiryNs >= now,
			"CBAP-v2.0 lease expires before classification");
		Simulator::Schedule(NanoSeconds(runtime.leaseExpiryNs - now),
			&RdmaHw::EvaluateCbapV20Lease, groupId);
	}
	Simulator::Schedule(NanoSeconds(group.earliestReleaseNs -
		Simulator::Now().GetTimeStep()), &RdmaHw::PlanRoundGroup, groupId);
}

std::map<uint32_t, uint64_t> RdmaHw::GetCbapSbaAvailableCapacity()
{
	std::map<uint32_t, uint64_t> available;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link) {
		if (link->second.initialized)
			available[link->first] =
				link->second.latest.effectiveCapacityBps;
		else
			available[link->first] =
				link->second.config.capacityBps >
					link->second.config.backgroundBps ?
				link->second.config.capacityBps -
					link->second.config.backgroundBps : 0;
	}
	return available;
}

void RdmaHw::PlanCbapSbaBatch(uint32_t groupId)
{
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.planScheduled && !group.planned &&
			!group.members.empty(),
		"CBAP-SBA batch plan callback executed out of order");
	NS_ASSERT_MSG(Simulator::Now().GetTimeStep() == group.applicationReadyNs,
		"CBAP-SBA plan did not run at collective application release");

	std::vector<CbapSbaController::FlowInput> inputs;
	std::map<uint32_t, Ptr<RdmaQueuePair> > qps;
	for (uint32_t i = 0; i < group.members.size(); ++i) {
		RoundGroupMember &member = group.members[i];
		NS_ASSERT_MSG(IsCbapSbaMode(member.hw->m_cc_mode),
			"mixed controller ownership in CBAP-SBA batch");
		uint32_t flowId = member.qp->crfm.flowId;
		NS_ASSERT_MSG(s_cbapFlowPaths.count(flowId) &&
				!s_cbapFlowPaths[flowId].empty(),
			"CBAP-SBA requires an explicit non-empty path");
		CbapFlowRuntime &runtime = s_cbapFlows[flowId];
		NS_ASSERT_MSG(!runtime.planned, "CBAP-SBA flow planned twice");
		runtime.hw = member.hw;
		runtime.qp = member.qp;
		runtime.flowId = flowId;
		runtime.batchId = groupId;
		runtime.roundIndex = member.roundIndex;
		runtime.planned = true;
		CbapSbaController::FlowInput input;
		input.flowId = flowId;
		input.path = s_cbapFlowPaths[flowId];
		input.maximumRateBps = member.qp->m_max_rate.GetBitRate();
		inputs.push_back(input);
		qps[flowId] = member.qp;
	}

	const std::map<uint32_t, uint64_t> available =
		GetCbapSbaAvailableCapacity();
	std::map<uint32_t, uint64_t> grants = s_cbapSbaController.AdmitBatch(
		groupId, group.commonReleaseNs, inputs, available,
		s_cbapConfig.oldBatchWeight, s_cbapConfig.newBatchWeight);
	NS_ASSERT_MSG(s_cbapSbaController.CheckConservation(groupId, available),
		"CBAP-SBA batch admission violates link conservation");

	for (uint32_t i = 0; i < inputs.size(); ++i) {
		const uint32_t flowId = inputs[i].flowId;
		const uint64_t grant = grants[flowId];
		CbapFlowRuntime &runtime = s_cbapFlows[flowId];
		Ptr<RdmaQueuePair> qp = qps[flowId];
		qp->cbap.enabled = true;
		qp->cbap.sbaEnabled = true;
		qp->cbap.fullCredit = false;
		qp->cbap.initOnly = false;
		qp->cbap.handoffEnabled = false;
		qp->cbap.delegationEnabled = false;
		qp->cbap.v20Enabled = false;
		qp->cbap.handedOff = false;
		qp->cbap.batchId = groupId;
		qp->cbap.phase = RdmaQueuePair::CBAP_PREPARE;
		qp->cbap.applicationReadyNs = group.applicationReadyNs;
		qp->cbap.networkReleaseNs = group.commonReleaseNs;
		qp->cbap.baseRateBps = grant;
		qp->cbap.admitRateBps = grant;
		qp->cbap.targetRateBps = grant;
		qp->cbap.requestedRateBps = grant;
		qp->cbap.currentRateBps = grant;
		qp->cbap.initialAdmitRateBps = grant;
		qp->cbap.exactGrantPacing = true;
		qp->cbap.sbaLastAppliedRateBps = grant;
		qp->cbap.sbaFirstFeedbackNs = 0;
		qp->cbap.sbaHandoffCount = 0;

		if (grant == 0) {
			// HOLD is a scheduler gate, not a synthetic 0/1-bps transport
			// rate.  Preserve the dormant QP's legal rate object.
			qp->cbap.zeroGrantPaused = true;
			qp->cbap.zeroGrantPauseCount++;
			qp->cbap.zeroGrantPauseStartNs = group.commonReleaseNs;
			qp->m_nextAvail = Simulator::GetMaximumSimulationTime();
		} else {
			qp->cbap.zeroGrantPaused = false;
			qp->cbap.sbaLeaseExpiryNs =
				group.commonReleaseNs + s_cbapConfig.sbaLeaseNs;
			runtime.hw->ChangeRate(qp, DataRate(grant));
		}
		uint32_t nic = runtime.hw->GetNicIdxOfQp(qp);
		runtime.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();

		CbapAdmissionRecord record = {};
		record.planStartNs = group.applicationReadyNs;
		record.planCompleteNs = group.commonReleaseNs;
		record.applicationReadyNs = group.applicationReadyNs;
		record.networkReleaseNs = group.commonReleaseNs;
		record.batchId = groupId;
		record.flowId = flowId;
		record.baseRateBps = grant;
		record.admitRateBps = grant;
		record.initialRateBps = grant;
		record.creditBytes = 0;
		record.effectiveCapacityBps =
			std::numeric_limits<uint64_t>::max();
		for (uint32_t hop = 0; hop < inputs[i].path.size(); ++hop)
			record.effectiveCapacityBps = std::min(
				record.effectiveCapacityBps,
				available.find(inputs[i].path[hop])->second);
		record.capacityValid = true;
		s_cbapAdmissionRecords.push_back(record);
		s_cbapGrantMessages++;
		s_cbapBatchGrantMessages[groupId]++;
	}

	Simulator::Schedule(NanoSeconds(group.earliestReleaseNs -
		Simulator::Now().GetTimeStep()), &RdmaHw::PlanRoundGroup, groupId);
}

void RdmaHw::EvaluateCbapSbaReadmission(uint64_t nowNs,
		const std::string &reason)
{
	std::set<uint32_t> batches;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (flow->second.active && !flow->second.finished &&
				flow->second.qp && flow->second.qp->cbap.sbaEnabled) {
			batches.insert(flow->second.batchId);
			if (flow->second.qp->cbap.handedOff)
				s_cbapSbaController.ObserveDcqcnAppliedRate(
					flow->first,
					flow->second.qp->m_rate.GetBitRate());
		}
	}
	const std::map<uint32_t, uint64_t> available =
		GetCbapSbaAvailableCapacity();
	for (std::set<uint32_t>::const_iterator batch = batches.begin();
			batch != batches.end(); ++batch) {
		std::vector<uint32_t> admitted = s_cbapSbaController.ReadmitHeld(
			*batch, nowNs, available, reason);
		for (uint32_t i = 0; i < admitted.size(); ++i) {
			CbapFlowRuntime &runtime = s_cbapFlows[admitted[i]];
			Ptr<RdmaQueuePair> qp = runtime.qp;
			const CbapSbaController::FlowState *state =
				s_cbapSbaController.GetFlow(admitted[i]);
			NS_ASSERT_MSG(qp && state && state->appliedRateBps > 0 &&
					!qp->cbap.handedOff,
				"CBAP-SBA readmission produced invalid state");
			qp->cbap.admitRateBps = state->grantRateBps;
			qp->cbap.targetRateBps = state->grantRateBps;
			qp->cbap.requestedRateBps = state->grantRateBps;
			qp->cbap.currentRateBps = state->appliedRateBps;
			qp->cbap.sbaLastAppliedRateBps = state->appliedRateBps;
			qp->cbap.zeroGrantPaused = false;
			qp->cbap.zeroGrantResumeCount++;
			if (nowNs >= qp->cbap.zeroGrantPauseStartNs)
				qp->cbap.zeroGrantPausedNs +=
					nowNs - qp->cbap.zeroGrantPauseStartNs;
			qp->cbap.zeroGrantPauseStartNs = 0;
			qp->cbap.phase = RdmaQueuePair::CBAP_STARTUP_ADMISSION;
			qp->cbap.sbaLeaseExpiryNs = nowNs + s_cbapConfig.sbaLeaseNs;
			runtime.hw->ChangeRate(qp, DataRate(state->appliedRateBps));
			uint32_t nic = runtime.hw->GetNicIdxOfQp(qp);
			runtime.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();
		}
	}
}

void RdmaHw::EvaluateCbapSbaLease(uint64_t nowNs)
{
	// UNCALIBRATED backstop (doc section 3.3): if a flow's first-batch
	// packets never trip ECN, no CNP ever arrives and OnActionableFeedback
	// is never called from the RX path.  Without this, such a flow would
	// stay in CBAP_STARTUP_ADMISSION forever.  s_cbapConfig.sbaLeaseNs is a
	// fixed conservative placeholder, not a value derived from a measured
	// blind-window distribution; it must be recalibrated once S1-S6
	// first-feedback timestamps exist.
	for (std::map<uint32_t, CbapFlowRuntime>::iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (!flow->second.active || flow->second.finished ||
				!flow->second.qp || !flow->second.qp->cbap.sbaEnabled ||
				flow->second.qp->cbap.handedOff)
			continue;
		Ptr<RdmaQueuePair> qp = flow->second.qp;
		if (qp->cbap.phase != RdmaQueuePair::CBAP_STARTUP_ADMISSION ||
				nowNs < qp->cbap.sbaLeaseExpiryNs)
			continue;
		qp->cbap.sbaLeaseExpiryCount++;
		flow->second.hw->HandoffCbapSbaFlow(qp, nowNs);
	}
}

// Capacity migration, per control epoch: advance each migrating flow's
// envelope toward its target with a queue-pressure-dependent step, then
// clamp the live rate.  Coefficients follow design doc section 4:
// f_inc > f_dec when the queue is idle (close the gap fast), equal
// mid-band, f_inc < f_dec at/above Qmax (net drain).

// Recompute migration targets from the CURRENT active set.  Called from
// the epoch tick whenever that set changes (new batch, a migrating flow
// finishing, any churn) or a deadline lapses, so capacity freed by a
// completed flow is redistributed instead of being left stranded.
//
// The newest batch present is treated as the 'new' side and everything
// else as the 'old' side, giving R_old* = (1-eta)*R_old and
// R_new* = C - R_old*.  When only one batch remains there is nothing to
// hand over, so every survivor's target rises back to its own feasible
// ceiling -- min(app cap, NIC max, per-flow link share).
void RdmaHw::ReplanCbapSbaMigrationTargets(uint64_t nowNs,
		const char *reason)
{
	if (!s_cbapConfig.migrationEnabled)
		return;
	const std::map<uint32_t, uint64_t> available =
		GetCbapSbaAvailableCapacity();
	// Single scan: bucket live flows per link and find the newest batch.
	uint32_t newestBatch = 0;
	bool haveAny = false;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (!flow->second.active || flow->second.finished ||
				!flow->second.qp || !flow->second.qp->cbap.sbaEnabled)
			continue;
		if (!haveAny || flow->second.batchId > newestBatch)
			newestBatch = flow->second.batchId;
		haveAny = true;
	}
	if (!haveAny)
		return;
	std::map<uint32_t, uint64_t> oldAggregateBps;
	std::map<uint32_t, std::vector<uint32_t> > oldFlowsByLink;
	std::map<uint32_t, std::vector<uint32_t> > newFlowsByLink;
	std::set<uint32_t> liveFlows;
	bool haveOldSide = false;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (!flow->second.active || flow->second.finished ||
				!flow->second.qp || !flow->second.qp->cbap.sbaEnabled)
			continue;
		liveFlows.insert(flow->first);
		const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
		bool isNew = flow->second.batchId == newestBatch;
		uint64_t rate = flow->second.qp->m_rate.GetBitRate();
		for (uint32_t hop = 0; hop < path.size(); ++hop) {
			if (isNew) {
				newFlowsByLink[path[hop]].push_back(flow->first);
			} else {
				oldFlowsByLink[path[hop]].push_back(flow->first);
				oldAggregateBps[path[hop]] += rate;
				haveOldSide = true;
			}
		}
	}
	// Per-link shares.  With no old side left this degenerates to 'every
	// survivor gets an equal slice of the whole link', which is exactly
	// the recovery case.
	std::map<uint32_t, uint64_t> perFlowTarget;
	for (std::map<uint32_t, uint64_t>::const_iterator link =
			available.begin(); link != available.end(); ++link) {
		const std::vector<uint32_t> &olds = oldFlowsByLink.count(link->first)
			? oldFlowsByLink[link->first] : std::vector<uint32_t>();
		const std::vector<uint32_t> &news = newFlowsByLink.count(link->first)
			? newFlowsByLink[link->first] : std::vector<uint32_t>();
		if (olds.empty() && news.empty())
			continue;
		uint64_t oldShare;
		uint64_t newShare;
		if (!olds.empty() && !news.empty()) {
			// Handover in progress: old side releases eta of what it holds.
			uint64_t oldAggregate = oldAggregateBps.count(link->first) ?
				oldAggregateBps[link->first] : 0;
			oldShare = (uint64_t)std::floor(
				(1.0L - s_cbapConfig.migrationReleaseRatio) *
				(long double)oldAggregate);
			newShare = link->second > oldShare ?
				link->second - oldShare : 0;
		} else if (news.empty()) {
			// Recovery: the new batch is gone, the old side takes it all.
			oldShare = link->second;
			newShare = 0;
		} else {
			// Only the new batch is on this link.
			oldShare = 0;
			newShare = link->second;
		}
		if (!olds.empty()) {
			uint64_t per = oldShare / olds.size();
			for (uint32_t i = 0; i < olds.size(); ++i)
				if (!perFlowTarget.count(olds[i]) ||
						perFlowTarget[olds[i]] > per)
					perFlowTarget[olds[i]] = per;
		}
		if (!news.empty()) {
			uint64_t per = newShare / news.size();
			for (uint32_t i = 0; i < news.size(); ++i)
				if (!perFlowTarget.count(news[i]) ||
						perFlowTarget[news[i]] > per)
					perFlowTarget[news[i]] = per;
		}
	}
	// Arm every survivor.  Direction is NOT fixed by old/new role -- the
	// executor picks f_inc or f_dec each epoch from the sign of
	// (target - current), so the same code path handles release,
	// take-up and recovery.
	for (std::map<uint32_t, uint64_t>::const_iterator it =
			perFlowTarget.begin(); it != perFlowTarget.end(); ++it) {
		Ptr<RdmaQueuePair> qp = s_cbapFlows[it->first].qp;
		RdmaHw *hw = s_cbapFlows[it->first].hw;
		if (!qp || !hw)
			continue;
		// Never target above what this flow is actually allowed to send:
		// the application cap comes first, then the NIC line rate.
		uint64_t ceiling = qp->m_max_rate.GetBitRate();
		if (qp->m_appRateCapBps > 0 && qp->m_appRateCapBps < ceiling)
			ceiling = qp->m_appRateCapBps;
		uint64_t target = std::min(it->second, ceiling);
		target = std::max(target, (uint64_t)hw->m_minRate.GetBitRate());
		if (qp->cbap.migrationActive &&
				qp->cbap.migrationTargetBps == target)
			continue;
		qp->cbap.migrationActive = true;
		// Retained only for logging; the executor no longer reads it to
		// decide direction.
		qp->cbap.migrationIsOldFlow =
			s_cbapFlows[it->first].batchId != newestBatch;
		qp->cbap.migrationTargetBps = target;
		// Continuity: the trajectory always resumes from the real current
		// rate, never from a stale envelope or the admission grant.
		qp->cbap.migrationEnvelopeBps = qp->m_rate.GetBitRate();
		qp->cbap.migrationStartNs = nowNs;
		if (s_cbapConfig.migrationTrace)
			std::cout << "CBAP_MIG_REPLAN t=" << nowNs
				<< " reason=" << reason
				<< " flow=" << it->first
				<< " batch=" << s_cbapFlows[it->first].batchId
				<< " newest_batch=" << newestBatch
				<< " cur=" << qp->m_rate.GetBitRate()
				<< " target=" << target
				<< " ceiling=" << ceiling
				<< " old_side_present=" << (haveOldSide ? 1 : 0)
				<< std::endl;
	}
	// Drop migration state for flows that are gone, so a finished flow
	// never keeps an envelope or a reservation alive.
	for (std::map<uint32_t, CbapFlowRuntime>::iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (!flow->second.qp)
			continue;
		if (!liveFlows.count(flow->first) &&
				flow->second.qp->cbap.migrationActive) {
			flow->second.qp->cbap.migrationActive = false;
			flow->second.qp->cbap.migrationTargetBps = 0;
			flow->second.qp->cbap.migrationEnvelopeBps = 0;
		}
	}
	s_cbapSbaMigrationActiveSet = liveFlows;
}

void RdmaHw::EvaluateCbapSbaMigration(uint64_t nowNs)
{
	if (!s_cbapConfig.migrationEnabled)
		return;
	for (std::map<uint32_t, CbapFlowRuntime>::iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow) {
		if (!flow->second.active || flow->second.finished ||
				!flow->second.qp || !flow->second.hw ||
				!flow->second.qp->cbap.migrationActive)
			continue;
		Ptr<RdmaQueuePair> qp = flow->second.qp;
		// Queue pressure u over this flow's tightest link: 0 = idle,
		// 1 = at/above Qmax.
		long double pressure = 0.0L;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[flow->first];
		for (uint32_t hop = 0; hop < path.size(); ++hop) {
			std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
				s_cbapLinks.find(path[hop]);
			if (link == s_cbapLinks.end() || !link->second.initialized)
				continue;
			uint64_t qEcn = link->second.config.ecnThresholdBytes;
			long double qMin = s_cbapConfig.budgetQLowFraction * qEcn;
			long double qMax = s_cbapConfig.budgetQHighFraction * qEcn;
			long double q = (long double)link->second.latest.queueBytes;
			long double u = qMax > qMin ? (q - qMin) / (qMax - qMin) : 1.0L;
			u = std::max(0.0L, std::min(1.0L, u));
			pressure = std::max(pressure, u);
		}
		uint64_t minRate = flow->second.hw->m_minRate.GetBitRate();
		uint64_t currentRate = qp->m_rate.GetBitRate();
		uint64_t targetRate = qp->cbap.migrationTargetBps;
		// Direction comes from the sign of (target - current), NOT from the
		// old/new role: a flow that released capacity earlier must be able
		// to climb back up through the same code path once the new batch
		// finishes.  f_dec is constant; f_inc carries the queue-pressure
		// skew so extra oversubscription is only borrowed when the queue
		// has room for it.
		long double step;
		if (targetRate >= currentRate)
			step = s_cbapConfig.migrationRiseBase *
				(1.0L + s_cbapConfig.migrationRiseSkew *
				(1.0L - 2.0L * pressure));
		else
			step = s_cbapConfig.migrationDecayBase;
		step = std::max(0.0L, std::min(1.0L, step));
		// Nonlinear error convergence, anchored on the flow's REAL current
		// rate rather than the envelope's own history, so a DCQCN
		// congestion response is absorbed instead of being ignored.
		long double nextRate = (long double)currentRate +
			step * ((long double)targetRate - (long double)currentRate);
		// Never overshoot: clamp into [current, target] (either order).
		if (targetRate >= currentRate)
			nextRate = std::min((long double)targetRate,
				std::max((long double)currentRate, nextRate));
		else
			nextRate = std::max((long double)targetRate,
				std::min((long double)currentRate, nextRate));
		// A zero pacing rate would trip the assertion in UpdateNextAvail;
		// HOLD is expressed via zeroGrantPaused, never via rate 0.
		uint64_t appliedRate = std::max(minRate,
			(uint64_t)std::floor(nextRate));
		if (qp->m_max_rate.GetBitRate() > 0)
			appliedRate = std::min(appliedRate,
				(uint64_t)qp->m_max_rate.GetBitRate());
		// Record how far DCQCN had drifted above the previous envelope
		// between epochs (bounded error, design doc section 9).
		if (qp->cbap.migrationEnvelopeBps > 0 &&
				currentRate > qp->cbap.migrationEnvelopeBps) {
			uint64_t breach = currentRate - qp->cbap.migrationEnvelopeBps;
			qp->cbap.migrationBreachCount++;
			if (breach > qp->cbap.migrationMaxBreachBps)
				qp->cbap.migrationMaxBreachBps = breach;
			qp->cbap.migrationBreachBytes += (uint64_t)(
				(long double)breach * s_cbapConfig.controlEpochNs /
				(8.0L * 1e9L));
		}
		qp->cbap.migrationEnvelopeBps = appliedRate;
		// Stop DCQCN's self-scheduled timers from walking the rate back
		// up between our epochs.  m_rpTimer keeps pushing m_rate toward
		// (m_rate+m_targetRate)/2 even with no congestion feedback at all,
		// which would fight the migration trajectory.  CNP arrival still
		// reaches cnp_received_mlx and keeps its veto.  Same cancel-then-
		// restore pattern already used by HandoffCbapSbaFlow.
		if (IsDcqcnMode(flow->second.hw->m_cc_mode)) {
			Simulator::Cancel(qp->mlx.m_rpTimer);
			Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
			qp->mlx.m_targetRate = DataRate(appliedRate);
		} else if (UsesHpccTelemetryMode(flow->second.hw->m_cc_mode)) {
			// HPCC has no self-scheduled timer to cancel -- it acts only on
			// ACK arrival -- but it computes the next rate from hp.m_curRate.
			// Leaving that stale would make the next feedback undo this
			// epoch's migration step, so keep it aligned with what we applied.
			qp->hp.m_curRate = DataRate(appliedRate);
			if (flow->second.hw->m_multipleRate) {
				for (uint32_t i = 0; i < IntHeader::maxHop; i++)
					qp->hp.hopState[i].Rc = DataRate(appliedRate);
			}
		}
		// Write the rate through the one entry point that also recomputes
		// m_nextAvail -- the send gate in GetNextQindex only ever reads
		// m_nextAvail, never m_rate.
		if (currentRate != appliedRate)
			flow->second.hw->ChangeRate(qp, DataRate(appliedRate));
		// ChangeRate's incremental branch can land in the past, and a QP
		// parked in HOLD carries m_nextAvail = max-time; pull it back and
		// force a rescan, exactly as PlanCbapSbaBatch does.  Without the
		// rescan dev->UpdateNextAvail is a no-op once m_nextSend expired.
		if (qp->m_nextAvail < Simulator::Now())
			qp->m_nextAvail = Simulator::Now();
		uint32_t nic = flow->second.hw->GetNicIdxOfQp(qp);
		flow->second.hw->m_nic[nic].dev->UpdateNextAvail(qp->m_nextAvail);
		flow->second.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();
		// Convergence / deadline.  On timeout the cap is never simply
		// dropped: that would let the old flow snap back and recreate the
		// stranded capacity.  Realign to the queue state instead.
		uint64_t gap = appliedRate > targetRate ?
			appliedRate - targetRate : targetRate - appliedRate;
		bool converged = targetRate == 0 ? true :
			gap * 100 < targetRate;
		uint64_t rttNs = std::max(qp->m_baseRtt,
			s_cbapConfig.controlEpochNs);
		uint64_t deadline = qp->cbap.migrationStartNs +
			(uint64_t)s_cbapConfig.migrationMaxRtt * rttNs;
		const char *endReason = "";
		if (converged) {
			// Hand the converged rate to DCQCN as its starting point so
			// AI/HAI resumes from here with no step change, then let its
			// timers run again.
			if (IsDcqcnMode(flow->second.hw->m_cc_mode)) {
				qp->mlx.m_targetRate = DataRate(appliedRate);
				qp->mlx.m_rpTimeStage = 0;
				flow->second.hw->ScheduleUpdateAlphaMlx(qp);
			} else if (UsesHpccTelemetryMode(
					flow->second.hw->m_cc_mode)) {
				// Resume HPCC from the converged rate with a fresh window, so
				// its first post-migration update measures only new traffic.
				qp->hp.m_curRate = DataRate(appliedRate);
				if (flow->second.hw->m_multipleRate) {
					for (uint32_t i = 0; i < IntHeader::maxHop; i++)
						qp->hp.hopState[i].Rc = DataRate(appliedRate);
				}
				qp->hp.m_lastUpdateSeq = 0;
				qp->hp.m_incStage = 0;
			}
			qp->cbap.migrationActive = false;
			endReason = "converged";
		} else if (nowNs >= deadline) {
			// Not converged in time.  If the queue is already at or above
			// Qmax the target itself is unreachable, so align the target to
			// what the link actually sustains; otherwise keep the same
			// target and give it another window.
			if (pressure >= 1.0L) {
				qp->cbap.migrationTargetBps = appliedRate;
				endReason = "deadline_target_aligned";
			} else {
				endReason = "deadline_retargeted";
			}
			qp->cbap.migrationRetargetCount++;
			qp->cbap.migrationStartNs = nowNs;
			// Ask for a full replan next epoch: the target may be
			// unreachable because the link state moved under us.
			s_cbapSbaMigrationReplanPending = true;
		}
		if (s_cbapConfig.migrationTrace)
			std::cout << "CBAP_MIG t=" << nowNs
				<< " epoch=" << s_cbapEpoch
				<< " flow=" << flow->first
				<< (qp->cbap.migrationIsOldFlow ? " side=old" : " side=new")
				<< " cur=" << currentRate
				<< " next=" << appliedRate
				<< " tgt=" << qp->cbap.migrationTargetBps
				<< " f=" << (double)step
				<< " u=" << (double)pressure
				<< " breach=" << qp->cbap.migrationBreachCount
				<< " end=" << endReason
				<< std::endl;
	}
}



void RdmaHw::PlanCbapBatch(uint32_t groupId)
{
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.planScheduled && !group.planned,
		"CBAP batch plan callback executed out of order");
	NS_ASSERT_MSG(Simulator::Now().GetTimeStep() ==
		group.applicationReadyNs, "CBAP plan did not start at app ready");
	std::vector<uint32_t> pending;
	for (uint32_t i = 0; i < group.members.size(); ++i){
		RoundGroupMember &member = group.members[i];
		NS_ASSERT_MSG(IsCbapMode(member.hw->m_cc_mode),
			"mixed non-CBAP member in CBAP batch");
		uint32_t flowId = member.qp->crfm.flowId;
		NS_ASSERT_MSG(s_cbapFlowPaths.count(flowId),
			"CBAP group member lacks an explicit path");
		CbapFlowRuntime &flow = s_cbapFlows[flowId];
		NS_ASSERT_MSG(!flow.planned, "CBAP flow planned twice");
		flow.hw = member.hw;
		flow.qp = member.qp;
		flow.flowId = flowId;
		flow.batchId = groupId;
		flow.roundIndex = member.roundIndex;
		flow.planned = true;
		pending.push_back(flowId);
	}
	uint32_t groupMode = group.members.front().hw->m_cc_mode;
	if (groupMode == CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
			groupMode == CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
			groupMode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION){
		CbapHandoffBatchRecord &handoff = s_cbapHandoffBatches[groupId];
		handoff.batchId = groupId;
		handoff.applicationReadyNs = group.applicationReadyNs;
		handoff.networkReleaseNs = group.commonReleaseNs;
		handoff.activeFlowCount = pending.size();
		handoff.noHandoffReason = groupMode ==
			CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ? "v13_shadow_only" :
			"awaiting_tracking";
	}
	std::vector<uint32_t> incumbents;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
		if (flow->second.active && !flow->second.finished)
			incumbents.push_back(flow->first);
	std::vector<uint32_t> scopedBaseIncumbents;
	if (group.members.front().hw->m_cc_mode ==
			CC_MODE_CBAP_FULL_SCOPED ||
			group.members.front().hw->m_cc_mode ==
				CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
			group.members.front().hw->m_cc_mode ==
				CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
		group.members.front().hw->m_cc_mode ==
				CC_MODE_CBAP_FULL_GUARDED_DELEGATION)
		for (std::map<uint32_t, CbapScopeBaseFlowRuntime>::const_iterator
				flow = s_cbapScopeBaseFlows.begin();
				flow != s_cbapScopeBaseFlows.end(); ++flow)
			if (flow->second.qp &&
					flow->second.qp->crfm.currentRoundIndex >= 0 &&
					flow->second.qp->snd_una <
						flow->second.qp->crfm.releasedBytes)
				scopedBaseIncumbents.push_back(flow->first);
	std::map<uint32_t, uint64_t> effective;
	std::map<uint32_t, uint64_t> queue;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		effective[link->first] = link->second.initialized ?
			link->second.latest.effectiveCapacityBps :
			link->second.previousEffectiveCapacityBps;
		queue[link->first] = link->second.initialized ?
			link->second.latest.queueBytes : 0;
	}
	std::map<uint32_t, uint64_t> candidateFloor;
	for (uint32_t i = 0; i < incumbents.size(); ++i){
		Ptr<RdmaQueuePair> qp = s_cbapFlows[incumbents[i]].qp;
		uint64_t measured =
			(qp->cbap.recentActualRateBps[0] +
			 qp->cbap.recentActualRateBps[1]) / 2;
		if (measured == 0)
			measured = qp->m_rate.GetBitRate();
		candidateFloor[incumbents[i]] =
			(uint64_t)std::floor(0.90L * measured);
	}
	for (uint32_t i = 0; i < scopedBaseIncumbents.size(); ++i)
		candidateFloor[scopedBaseIncumbents[i]] =
			(uint64_t)std::floor(0.90L *
			s_cbapScopeBaseFlows[scopedBaseIncumbents[i]].qp->
			m_rate.GetBitRate());
	std::map<uint32_t, double> linkScale;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link){
		long double sum = 0;
		for (uint32_t i = 0; i < incumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[incumbents[i]];
			if (std::find(path.begin(), path.end(), link->first) !=
					path.end())
				sum += candidateFloor[incumbents[i]];
		}
		for (uint32_t i = 0; i < scopedBaseIncumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[scopedBaseIncumbents[i]];
			if (std::find(path.begin(), path.end(), link->first) !=
					path.end())
				sum += candidateFloor[scopedBaseIncumbents[i]];
		}
		linkScale[link->first] = sum > effective[link->first] && sum > 0 ?
			(double)((long double)effective[link->first] / sum) : 1.0;
	}
	std::map<uint32_t, uint64_t> floor;
	for (uint32_t i = 0; i < incumbents.size(); ++i){
		double scale = 1.0;
		const std::vector<uint32_t> &path =
			s_cbapFlowPaths[incumbents[i]];
		for (uint32_t hop = 0; hop < path.size(); ++hop)
			scale = std::min(scale, linkScale[path[hop]]);
		floor[incumbents[i]] = (uint64_t)std::floor(
			candidateFloor[incumbents[i]] * scale);
		Ptr<RdmaQueuePair> incumbent = s_cbapFlows[incumbents[i]].qp;
		incumbent->cbap.protectionFloorBps = floor[incumbents[i]];
	}
	for (uint32_t i = 0; i < scopedBaseIncumbents.size(); ++i){
		double scale = 1.0;
		const std::vector<uint32_t> &path =
			s_cbapFlowPaths[scopedBaseIncumbents[i]];
		for (uint32_t hop = 0; hop < path.size(); ++hop)
			scale = std::min(scale, linkScale[path[hop]]);
		floor[scopedBaseIncumbents[i]] = (uint64_t)std::floor(
			candidateFloor[scopedBaseIncumbents[i]] * scale);
		if (groupMode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION)
			s_cbapScopeBaseFlows[scopedBaseIncumbents[i]].
				protectionFloorBps = floor[scopedBaseIncumbents[i]];
	}
	std::map<uint32_t, uint64_t> baseCapacity = effective;
	for (std::map<uint32_t, uint64_t>::iterator capacity =
			baseCapacity.begin(); capacity != baseCapacity.end();
			++capacity){
		uint64_t used = 0;
		for (uint32_t i = 0; i < incumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[incumbents[i]];
			if (std::find(path.begin(), path.end(), capacity->first) !=
					path.end())
				used += floor[incumbents[i]];
		}
		for (uint32_t i = 0; i < scopedBaseIncumbents.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[scopedBaseIncumbents[i]];
			if (std::find(path.begin(), path.end(), capacity->first) !=
					path.end())
				used += floor[scopedBaseIncumbents[i]];
		}
		capacity->second = used < capacity->second ?
			capacity->second - used : 0;
	}
	std::map<uint32_t, uint64_t> emptyInitial;
	std::map<uint32_t, uint64_t> baseRates =
		ComputeCbapProgressiveFill(pending, baseCapacity, emptyInitial);
	std::map<uint32_t, uint64_t> admitCapacity = baseCapacity;
	std::map<uint32_t, uint64_t> packetMargin;
	std::map<uint32_t, uint64_t> feedbackHorizon;
	std::map<uint32_t, uint64_t> queueRoom;
	for (std::map<uint32_t, uint64_t>::iterator capacity =
			admitCapacity.begin(); capacity != admitCapacity.end();
			++capacity){
		uint32_t count = 0;
		uint64_t horizon = 0;
		for (uint32_t i = 0; i < pending.size(); ++i){
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[pending[i]];
			if (std::find(path.begin(), path.end(), capacity->first) ==
					path.end())
				continue;
			count++;
			Ptr<RdmaQueuePair> qp = s_cbapFlows[pending[i]].qp;
			horizon = std::max(horizon, qp->m_baseRtt +
				s_cbapConfig.controlDelayNs);
		}
		packetMargin[capacity->first] =
			(uint64_t)count * s_cbapConfig.maxWirePacketBytes;
		uint64_t target = (uint64_t)std::floor(0.50 *
			s_cbapLinks[capacity->first].config.ecnThresholdBytes);
		queueRoom[capacity->first] =
			queue[capacity->first] < target &&
			packetMargin[capacity->first] <
				target - queue[capacity->first] ?
			target - queue[capacity->first] -
				packetMargin[capacity->first] : 0;
		feedbackHorizon[capacity->first] =
			std::max((uint64_t)1, horizon);
		long double temporary = (long double)8 *
			queueRoom[capacity->first] * 1e9L /
			feedbackHorizon[capacity->first];
		uint64_t queueRate = temporary >
			std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(temporary);
		capacity->second = capacity->second <=
			std::numeric_limits<uint64_t>::max() - queueRate ?
			capacity->second + queueRate :
			std::numeric_limits<uint64_t>::max();
	}
	for (std::map<uint32_t, uint64_t>::const_iterator capacity =
			admitCapacity.begin(); capacity != admitCapacity.end(); ++capacity)
		s_cbapLinks[capacity->first].plannerCapacityBps = capacity->second;
	std::map<uint32_t, uint64_t> admitRates;
	bool independent = group.members.front().hw->m_cc_mode ==
		CC_MODE_CBAP_INDEPENDENT;
	if (!independent){
		admitRates = ComputeCbapProgressiveFill(
			pending, admitCapacity, emptyInitial);
	}else{
		for (uint32_t i = 0; i < pending.size(); ++i){
			uint64_t rate =
				s_cbapFlows[pending[i]].qp->m_max_rate.GetBitRate();
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[pending[i]];
			for (uint32_t hop = 0; hop < path.size(); ++hop)
				rate = std::min(rate, admitCapacity[path[hop]]);
			admitRates[pending[i]] = std::max((uint64_t)1, rate);
		}
	}
	for (uint32_t i = 0; i < incumbents.size(); ++i){
		Ptr<RdmaQueuePair> qp = s_cbapFlows[incumbents[i]].qp;
		uint64_t rebalance = std::max((uint64_t)2 * qp->m_baseRtt,
			(uint64_t)4 * s_cbapConfig.controlEpochNs);
		qp->cbap.rebalanceStartNs = group.commonReleaseNs +
			qp->m_baseRtt + s_cbapConfig.controlDelayNs;
		qp->cbap.rebalanceEndNs =
			qp->cbap.rebalanceStartNs + rebalance;
	}
	if (groupMode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION){
		for (uint32_t i = 0; i < scopedBaseIncumbents.size(); ++i){
			CbapScopeBaseFlowRuntime &base =
				s_cbapScopeBaseFlows[scopedBaseIncumbents[i]];
			uint64_t rebalance = std::max(
				(uint64_t)2 * base.qp->m_baseRtt,
				(uint64_t)4 * s_cbapConfig.controlEpochNs);
			base.rebalanceStartNs = group.commonReleaseNs +
				base.qp->m_baseRtt + s_cbapConfig.controlDelayNs;
			base.rebalanceEndNs = base.rebalanceStartNs + rebalance;
		}
	}
	for (uint32_t i = 0; i < pending.size(); ++i){
		CbapFlowRuntime &flow = s_cbapFlows[pending[i]];
		Ptr<RdmaQueuePair> qp = flow.qp;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[pending[i]];
		uint64_t horizon = 0;
		uint64_t credit = std::numeric_limits<uint64_t>::max();
		uint64_t observedQueue = 0;
		uint64_t margin = 0;
		uint64_t minimumEffective =
			std::numeric_limits<uint64_t>::max();
		double minimumScale = 1.0;
		for (uint32_t hop = 0; hop < path.size(); ++hop){
			uint32_t linkId = path[hop];
			uint32_t count = 0;
			for (uint32_t j = 0; j < pending.size(); ++j){
				const std::vector<uint32_t> &peerPath =
					s_cbapFlowPaths[pending[j]];
				if (std::find(peerPath.begin(), peerPath.end(), linkId) !=
						peerPath.end())
					count++;
			}
			credit = std::min(credit, count ?
				queueRoom[linkId] / count : 0);
			horizon = std::max(horizon, feedbackHorizon[linkId]);
			observedQueue = std::max(observedQueue, queue[linkId]);
			margin = std::max(margin, packetMargin[linkId]);
			minimumEffective = std::min(minimumEffective,
				effective[linkId]);
			minimumScale = std::min(minimumScale,
				linkScale[linkId]);
		}
		if (credit == std::numeric_limits<uint64_t>::max())
			credit = 0;
		bool full = flow.hw->m_cc_mode == CC_MODE_CBAP_FULL ||
			flow.hw->m_cc_mode == CC_MODE_CBAP_FULL_SCOPED ||
			flow.hw->m_cc_mode ==
				CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
			flow.hw->m_cc_mode == CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
			flow.hw->m_cc_mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION;
		qp->cbap.enabled = true;
		qp->cbap.fullCredit = full;
		qp->cbap.initOnly =
			flow.hw->m_cc_mode == CC_MODE_CBAP_INIT_ONLY;
		qp->cbap.independentDiagnostic = independent;
		qp->cbap.handoffEnabled = flow.hw->m_cc_mode ==
			CC_MODE_CBAP_FULL_STABLE_HANDOFF;
		qp->cbap.delegationEnabled = flow.hw->m_cc_mode ==
			CC_MODE_CBAP_FULL_GUARDED_DELEGATION;
		qp->cbap.delegatedEnvelope = false;
		qp->cbap.handedOff = false;
		qp->cbap.cbapCnpObserved = false;
		qp->cbap.lastCbapCnpNs = 0;
		qp->cbap.batchId = groupId;
		qp->cbap.phase = RdmaQueuePair::CBAP_PREPARE;
		qp->cbap.applicationReadyNs = group.applicationReadyNs;
		qp->cbap.networkReleaseNs = group.commonReleaseNs;
		qp->cbap.baseRateBps = baseRates[pending[i]];
		qp->cbap.admitRateBps = admitRates[pending[i]];
		qp->cbap.targetRateBps = admitRates[pending[i]];
		qp->cbap.creditInitialBytes = full ? credit : 0;
		qp->cbap.creditRemainingBytes = full ? credit : 0;
		qp->cbap.creditGateActive = false;
		qp->cbap.initialAdmitRateBps = admitRates[pending[i]];
		qp->cbap.estimatedFirstFeedbackNs =
			group.commonReleaseNs + horizon;
		qp->cbap.baseEligibleBytes = 0;
		qp->cbap.baseEligibilityLastNs = group.commonReleaseNs;
		SetCbapRate(flow, admitRates[pending[i]], 1, 0, false);
		if (qp->cbap.initOnly)
			qp->mlx.m_targetRate = DataRate(qp->m_rate.GetBitRate());
		CbapAdmissionRecord record = {};
		record.planStartNs = group.applicationReadyNs;
		record.planCompleteNs = group.commonReleaseNs;
		record.applicationReadyNs = group.applicationReadyNs;
		record.networkReleaseNs = group.commonReleaseNs;
		record.batchId = groupId;
		record.flowId = pending[i];
		record.baseRateBps = qp->cbap.baseRateBps;
		record.admitRateBps = qp->cbap.admitRateBps;
		record.initialRateBps = qp->m_rate.GetBitRate();
		record.creditBytes = qp->cbap.creditInitialBytes;
		record.feedbackHorizonNs = horizon;
		record.observedQueueBytes = observedQueue;
		record.packetMarginBytes = margin;
		record.effectiveCapacityBps = minimumEffective;
		record.floorScale = minimumScale;
		record.independentDiagnostic = independent;
		record.capacityValid = true;
		s_cbapAdmissionRecords.push_back(record);
		s_cbapGrantMessages++;
		s_cbapBatchGrantMessages[groupId]++;
	}
	Simulator::Schedule(NanoSeconds(group.earliestReleaseNs -
		Simulator::Now().GetTimeStep()), &RdmaHw::PlanRoundGroup, groupId);
}

void RdmaHw::SetCbapRate(CbapFlowRuntime &flow, uint64_t newRate,
		uint32_t reason, uint32_t rootId, bool stale)
{
	Ptr<RdmaQueuePair> qp = flow.qp;
	if (!qp || flow.finished)
		return;
	NS_ASSERT_MSG(!qp->cbap.handedOff &&
			qp->cbap.phase != RdmaQueuePair::CBAP_BASE_CC,
		"CBAP attempted to update a DCQCN-owned handoff flow");
	uint64_t oldRate = qp->m_rate.GetBitRate();
	bool wasPaused = qp->cbap.zeroGrantPaused;
	uint64_t minimum = (uint64_t)std::ceil(
		(long double)8 * s_cbapConfig.maxWirePacketBytes * 1e9L /
		s_cbapConfig.controlEpochNs);
	uint64_t requestedRate = std::min(newRate,
		qp->m_max_rate.GetBitRate());
	if (qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD)
		requestedRate = std::min(requestedRate, qp->cbap.admitRateBps);
	bool exact = s_cbapConfig.rateFloorPolicy ==
		CBAP_RATE_FLOOR_EXACT_GRANT_PACING;
	qp->cbap.exactGrantPacing = exact;
	qp->cbap.requestedRateBps = requestedRate;
	if (exact)
		newRate = requestedRate;
	else{
		// Frozen v1.2 semantics: retain the one-packet-per-control-epoch
		// clamp exactly, including the later Admission-Hold ceiling.
		newRate = std::max(minimum,
			std::min(newRate, qp->m_max_rate.GetBitRate()));
		if (qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD)
			newRate = std::min(newRate, qp->cbap.admitRateBps);
	}
	bool pause = exact && newRate == 0;
	CbapRateRecord record = {};
	record.timeNs = Simulator::Now().GetTimeStep();
	record.epoch = s_cbapEpoch;
	record.batchId = qp->cbap.batchId;
	record.flowId = flow.flowId;
	record.phaseBefore = qp->cbap.phase;
	record.oldRateBps = oldRate;
	record.targetRateBps = qp->cbap.targetRateBps;
	record.newRateBps = newRate;
	record.reason = reason;
	record.rootId = rootId;
	record.feedbackAgeNs = qp->cbap.lastFreshFeedbackNs > 0 &&
		record.timeNs >= qp->cbap.lastFreshFeedbackNs ?
		record.timeNs - qp->cbap.lastFreshFeedbackNs : 0;
	record.creditRemainingBytes = qp->cbap.creditRemainingBytes;
	record.protectionFloorBps = qp->cbap.protectionFloorBps;
	record.rebalanceStartNs = qp->cbap.rebalanceStartNs;
	record.rebalanceEndNs = qp->cbap.rebalanceEndNs;
	record.staleFeedback = stale;
	record.capacityValid = true;
	if (newRate != oldRate || pause != wasPaused){
		uint64_t now = Simulator::Now().GetTimeStep();
		if (qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD){
			if (qp->cbap.firstDataTxNs == 0)
				qp->cbap.rateUpdatesBeforeFirstTx++;
			if (reason == 4)
				qp->cbap.emergencyRateUpdatesDuringAdmission++;
			else if (reason != 1)
				qp->cbap.ordinaryRateUpdatesDuringAdmission++;
		}
		if (qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING ||
				qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY)
			UpdateCbapTrackingRateIntegral(qp, now);
		uint64_t oldSchedule = qp->m_nextAvail.GetTimeStep();
		RecordCbapTxEvent(qp, CBAP_TX_CANCEL_OR_INVALIDATE,
			oldSchedule, 0, qp->cbap.lastTxTimeNs, 0, 0, reason);
		if (pause){
			qp->cbap.zeroGrantPaused = true;
			if (!wasPaused){
				qp->cbap.zeroGrantPauseCount++;
				qp->cbap.zeroGrantPauseStartNs = now;
			}
			qp->m_rate = DataRate(0);
			qp->m_nextAvail = Simulator::GetMaximumSimulationTime();
		}else{
			if (wasPaused){
				qp->cbap.zeroGrantResumeCount++;
				if (now >= qp->cbap.zeroGrantPauseStartNs)
					qp->cbap.zeroGrantPausedNs += now -
						qp->cbap.zeroGrantPauseStartNs;
				qp->cbap.zeroGrantPauseStartNs = 0;
			}
			qp->cbap.zeroGrantPaused = false;
			flow.hw->ChangeRate(qp, DataRate(newRate));
			if (qp->m_nextAvail < Simulator::Now())
				qp->m_nextAvail = Simulator::Now();
		}
		uint32_t nic = flow.hw->GetNicIdxOfQp(qp);
		flow.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();
		RecordCbapTxEvent(qp, CBAP_TX_RESCHEDULE,
			qp->m_nextAvail.GetTimeStep(), 0,
			qp->cbap.lastTxTimeNs, 0, 0, reason);
		if (!pause && newRate > oldRate)
			qp->cbap.rateIncreaseCount++;
		else
			qp->cbap.rateDecreaseCount++;
		qp->cbap.rescheduleCount++;
	}else{
		qp->cbap.rateHoldCount++;
	}
	qp->cbap.currentRateBps = newRate;
	qp->cbap.rootId = rootId;
	record.phaseAfter = qp->cbap.phase;
	s_cbapRateRecords.push_back(record);
	if (qp->cbap.handoffEnabled || qp->cbap.delegationEnabled ||
			qp->cbap.v20Enabled){
		CbapControllerOwnershipRecord owner = {};
		owner.timeNs = record.timeNs;
		owner.epoch = s_cbapEpoch;
		owner.batchId = qp->cbap.batchId;
		owner.flowId = flow.flowId;
		owner.phase = qp->cbap.phase;
		owner.owner = "CBAP";
		owner.cbapRateUpdate = true;
		owner.dcqcnRateUpdate = false;
		s_cbapControllerOwnershipRecords.push_back(owner);
	}
}

bool RdmaHw::HasCompletePostReleaseFeedback(
		const CbapFlowRuntime &flow, uint64_t &firstSampleNs,
		uint64_t &completeDeliveryNs)
{
	firstSampleNs = 0;
	completeDeliveryNs = 0;
	if (!flow.qp)
		return false;
	const uint64_t release = flow.qp->cbap.networkReleaseNs;
	const std::vector<uint32_t> &path = s_cbapFlowPaths[flow.flowId];
	for (uint32_t hop = 0; hop < path.size(); ++hop){
		const CbapLinkRuntime &link = s_cbapLinks[path[hop]];
		if (!link.initialized ||
				link.latest.sampleTimeNs <= release ||
				link.latest.deliveryTimeNs <= release)
			return false;
		if (firstSampleNs == 0 ||
				link.latest.sampleTimeNs < firstSampleNs)
			firstSampleNs = link.latest.sampleTimeNs;
		completeDeliveryNs = std::max(completeDeliveryNs,
			link.latest.deliveryTimeNs);
	}
	return !path.empty();
}

bool RdmaHw::HasPostReleaseEmergencyEvidence(
		const CbapFlowRuntime &flow, uint32_t &rootId)
{
	rootId = 0;
	if (!flow.qp)
		return false;
	const uint64_t release = flow.qp->cbap.networkReleaseNs;
	const std::vector<uint32_t> &path = s_cbapFlowPaths[flow.flowId];
	for (uint32_t hop = 0; hop < path.size(); ++hop){
		const CbapLinkRuntime &link = s_cbapLinks[path[hop]];
		if (!link.initialized ||
				link.latest.sampleTimeNs <= release ||
				link.latest.deliveryTimeNs <= release)
			continue;
		uint64_t qHigh = (uint64_t)std::floor(0.80 *
			link.config.ecnThresholdBytes);
		if (link.latest.portState == CBAP_PORT_ROOT_CONGESTED){
			rootId = link.latest.rootId;
			return true;
		}
		if (link.latest.queueBytes >= qHigh ||
				link.latest.pfcEventsDelta > 0 ||
				link.latest.localPaused){
			rootId = link.latest.rootId;
			return true;
		}
	}
	return false;
}

void RdmaHw::UpdateCbapTrackingRateIntegral(Ptr<RdmaQueuePair> qp,
		uint64_t nowNs)
{
	if (!qp || qp->cbap.trackingRateLastNs == 0 ||
			nowNs <= qp->cbap.trackingRateLastNs)
		return;
	qp->cbap.trackingRateIntegral +=
		(long double)qp->cbap.currentRateBps *
		(nowNs - qp->cbap.trackingRateLastNs);
	qp->cbap.trackingRateLastNs = nowNs;
}

void RdmaHw::ExitCbapAdmission(Ptr<RdmaQueuePair> qp,
		uint64_t completeDeliveryNs)
{
	NS_ASSERT_MSG(qp &&
			qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD,
			"CBAP admission exit outside ADMISSION_HOLD");
	uint64_t now = Simulator::Now().GetTimeStep();
	NS_ASSERT_MSG(completeDeliveryNs > qp->cbap.networkReleaseNs,
			"CBAP admission exited on a pre-release sample");
	qp->cbap.firstCompleteFreshFeedbackNs = completeDeliveryNs;
	if (qp->cbap.firstFreshFeedbackNs == 0)
		qp->cbap.firstFreshFeedbackNs = completeDeliveryNs;
	qp->cbap.lastFreshFeedbackNs = completeDeliveryNs;
	qp->cbap.admissionExitNs = now;
	qp->cbap.bytesSentBeforeFreshFeedback =
		qp->snd_nxt >= qp->cbap.bytesSentAtRelease ?
		qp->snd_nxt - qp->cbap.bytesSentAtRelease : 0;
	qp->cbap.creditRemainingAtAdmissionExit =
		qp->cbap.creditRemainingBytes;
	qp->cbap.creditGateActive = false;
	if (qp->cbap.creditGateEnterNs > 0)
		qp->cbap.creditGateExitNs = now;
	qp->cbap.phase = RdmaQueuePair::CBAP_TRACKING;
	qp->cbap.trackingStartNs = now;
	qp->cbap.trackingRateLastNs = now;
	qp->cbap.trackingRateIntegral = 0;
	if (qp->cbap.handoffEnabled &&
			s_cbapConfig.handoffDiagnosticRecoveryUntilEpoch > 0)
		qp->cbap.phase = RdmaQueuePair::CBAP_RECOVERY;
}

void RdmaHw::RecordCbapTxEvent(Ptr<RdmaQueuePair> qp,
		uint32_t eventType, uint64_t scheduledTimeNs,
		uint64_t actualSendTimeNs, uint64_t previousTxTimeNs,
		uint64_t expectedGapNs, uint64_t actualGapNs,
		uint32_t reason)
{
	if (!qp || !qp->cbap.enabled)
		return;
	// CBAP-v2.0 relinquishes the data path after its one-shot handoff.
	// Keeping the legacy per-packet audit active here would turn a bounded
	// startup diagnostic into an unbounded base-CC trace.
	if (qp->cbap.v20Enabled && qp->cbap.handedOff)
		return;
	bool trackingPacket = qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING ||
		qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY ||
		qp->cbap.phase == RdmaQueuePair::CBAP_STARTUP_ADMISSION;
	if (trackingPacket &&
			(eventType == CBAP_TX_SEND || eventType == CBAP_TX_SCHEDULE) &&
			qp->cbap.txTraceTrackingPackets >=
				s_cbapConfig.txTraceTrackingPackets)
		return;
	CbapTxRecord record = {};
	record.timeNs = Simulator::Now().GetTimeStep();
	record.eventType = eventType;
	record.flowId = qp->crfm.flowId;
	record.batchId = qp->cbap.batchId;
	record.packetSeq = qp->cbap.lastPacketSeq;
	record.wireBytes = qp->cbap.lastPacketWireBytes;
	record.phase = qp->cbap.phase;
	record.currentRateBps = qp->m_rate.GetBitRate();
	record.targetRateBps = qp->cbap.targetRateBps;
	record.admitRateBps = qp->cbap.admitRateBps;
	record.baseRateBps = qp->cbap.baseRateBps;
	record.creditGateActive = qp->cbap.creditGateActive;
	record.creditRemainingBytes = qp->cbap.creditRemainingBytes;
	record.scheduledTimeNs = scheduledTimeNs;
	record.actualSendTimeNs = actualSendTimeNs;
	record.previousTxTimeNs = previousTxTimeNs;
	record.expectedGapNs = expectedGapNs;
	record.actualGapNs = actualGapNs;
	record.rescheduleReason = reason;
	s_cbapTxRecords.push_back(record);
}

void RdmaHw::ExecuteCbapBatchHandoff(uint32_t batchId, uint64_t now)
{
	CbapHandoffBatchRecord &batch = s_cbapHandoffBatches[batchId];
	NS_ASSERT_MSG(!batch.handoffOccurred,
		"CBAP stable handoff executed more than once for a batch");
	batch.handoffCandidateNs = now;
	batch.handoffExecuteNs = now;
	batch.handoffOccurred = true;
	batch.noHandoffReason = "none";
	batch.grantsBeforeHandoff = s_cbapBatchGrantMessages[batchId];
	batch.controlBytesBeforeHandoff =
		s_cbapBatchActiveSummaries[batchId] * s_cbapConfig.summaryBytes +
		batch.grantsBeforeHandoff * s_cbapConfig.grantBytes;

	for (std::map<uint32_t, CbapFlowRuntime>::iterator it =
			s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it){
		CbapFlowRuntime &flow = it->second;
		if (flow.batchId != batchId || !flow.active || flow.finished ||
				!flow.qp || flow.qp->cbap.handedOff)
			continue;
		Ptr<RdmaQueuePair> qp = flow.qp;
		NS_ASSERT_MSG(qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING,
			"handoff may only begin from TRACKING");
		CbapHandoffFlowRecord row;
		row.flowId = flow.flowId;
		row.batchId = batchId;
		row.phaseBefore = qp->cbap.phase;
		uint64_t roundEnd = qp->m_size;
		if (flow.roundIndex < qp->crfm.rounds.size())
			roundEnd = qp->crfm.rounds[flow.roundIndex].endSeq;
		row.remainingBytes = roundEnd > qp->snd_una ?
			roundEnd - qp->snd_una : 0;
		row.cbapAppliedRateBefore = qp->m_rate.GetBitRate();
		row.nextTxBeforeNs = qp->m_nextAvail.GetTimeStep();
		qp->cbap.phase = RdmaQueuePair::CBAP_HANDOFF_PENDING;
		qp->cbap.creditGateActive = false;
		qp->cbap.creditRemainingBytes = 0;
		qp->cbap.zeroGrantPaused = false;
		qp->cbap.handoffExecuteNs = now;
		qp->cbap.handoffRateBps = row.cbapAppliedRateBefore;
		qp->cbap.handoffNextTxBeforeNs = row.nextTxBeforeNs;
		NS_ASSERT_MSG(row.cbapAppliedRateBefore > 0,
			"stable handoff cannot initialize DCQCN with zero rate");

		// CBAP deliberately does not maintain a second DCQCN controller.
		// Stable eligibility excludes fresh CNP evidence, so initialize the
		// original Mellanox state as uncongested at the frozen applied rate.
		Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
		Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
		Simulator::Cancel(qp->mlx.m_rpTimer);
		qp->mlx.m_targetRate = DataRate(row.cbapAppliedRateBefore);
		qp->m_rate = DataRate(row.cbapAppliedRateBefore);
		qp->mlx.m_alpha = 0.0;
		qp->mlx.m_alpha_cnp_arrived = false;
		qp->mlx.m_decrease_cnp_arrived = false;
		qp->mlx.m_first_cnp = true;
		qp->mlx.m_rpTimeStage = 0;
		// The inherited rate may be below line rate even when no CNP is
		// fresh. Start the original DCQCN recovery timer, but do not perform
		// an AI step in the handoff event itself.
		qp->mlx.m_rpTimer = Simulator::Schedule(
			MicroSeconds(flow.hw->m_rpgTimeReset),
			&RdmaHw::RateIncEventTimerMlx, flow.hw, qp);

		uint64_t packetBytes = qp->cbap.lastPacketWireBytes > 0 ?
			qp->cbap.lastPacketWireBytes : s_cbapConfig.maxWirePacketBytes;
		uint64_t requiredGap = CbapPacketGapNs(packetBytes,
			row.cbapAppliedRateBefore);
		uint64_t safeNext = qp->cbap.lastTxTimeNs > 0 &&
			qp->cbap.lastTxTimeNs <=
				std::numeric_limits<uint64_t>::max() - requiredGap ?
			qp->cbap.lastTxTimeNs + requiredGap : now;
		uint64_t next = std::max(now, safeNext);
		if (row.nextTxBeforeNs > next)
			next = row.nextTxBeforeNs;
		qp->m_nextAvail = NanoSeconds(next);
		qp->cbap.handoffNextTxAfterNs = next;
		qp->cbap.exactGrantPacing = false;
		qp->cbap.handedOff = true;
		qp->cbap.phase = RdmaQueuePair::CBAP_BASE_CC;
		uint32_t nic = flow.hw->GetNicIdxOfQp(qp);
		flow.hw->m_nic[nic].dev->UpdateNextAvail(qp->m_nextAvail);
		flow.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();

		row.phaseAfter = qp->cbap.phase;
		row.dcqcnCurrentRateAfter = qp->m_rate.GetBitRate();
		row.dcqcnTargetRateAfter = qp->mlx.m_targetRate.GetBitRate();
		row.alphaAfter = qp->mlx.m_alpha;
		row.nextTxAfterNs = next;
		row.packetGapRequiredNs = requiredGap;
		qp->cbap.handoffFlowRecordIndex = s_cbapHandoffFlowRecords.size();
		s_cbapHandoffFlowRecords.push_back(row);
		batch.dcqcnRateSumAfterInit += row.dcqcnCurrentRateAfter;
		uint64_t jump = row.dcqcnCurrentRateAfter >
			row.cbapAppliedRateBefore ? row.dcqcnCurrentRateAfter -
			row.cbapAppliedRateBefore : row.cbapAppliedRateBefore -
			row.dcqcnCurrentRateAfter;
		batch.maxPerFlowRateJumpBps = std::max(
			batch.maxPerFlowRateJumpBps, jump);
		CbapControllerOwnershipRecord owner = {};
		owner.timeNs = now;
		owner.epoch = s_cbapEpoch;
		owner.batchId = batchId;
		owner.flowId = flow.flowId;
		owner.phase = qp->cbap.phase;
		owner.owner = "DCQCN";
		owner.cbapRateUpdate = false;
		owner.dcqcnRateUpdate = false;
		s_cbapControllerOwnershipRecords.push_back(owner);
	}
}

void RdmaHw::ExecuteCbapV20Handoff(uint32_t batchId, uint64_t now,
		const std::string &reason)
{
	CbapV20BatchRuntime &batch = s_cbapV20Batches[batchId];
	if (batch.handedOff || batch.bypass)
		return;
	batch.handedOff = true;
	batch.handoffNs = now;
	batch.handoffReason = reason;
	for (std::map<uint32_t, CbapFlowRuntime>::iterator it =
			s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it){
		CbapFlowRuntime &flow = it->second;
		if (flow.batchId != batchId || !flow.active || flow.finished ||
				!flow.qp || !flow.qp->cbap.v20Enabled ||
				flow.qp->cbap.handedOff)
			continue;
		Ptr<RdmaQueuePair> qp = flow.qp;
		NS_ASSERT_MSG(qp->cbap.phase ==
			RdmaQueuePair::CBAP_STARTUP_ADMISSION,
			"CBAP-v2.0 handoff outside STARTUP_ADMISSION");
		uint64_t inherited = qp->m_rate.GetBitRate();
		NS_ASSERT_MSG(inherited > 0,
			"CBAP-v2.0 cannot hand off a zero live rate");
		qp->cbap.phase = RdmaQueuePair::CBAP_SMOOTH_HANDOFF;
		qp->cbap.creditGateActive = false;
		qp->cbap.creditRemainingBytes = 0;
		qp->cbap.zeroGrantPaused = false;
		qp->cbap.v20HandoffInitialRateBps = inherited;
		qp->cbap.exactGrantPacing = false;
		uint64_t packetBytes = qp->cbap.lastPacketWireBytes > 0 ?
			qp->cbap.lastPacketWireBytes : s_cbapConfig.maxWirePacketBytes;
		uint64_t requiredGap = CbapPacketGapNs(packetBytes, inherited);
		uint64_t safeNext = qp->cbap.lastTxTimeNs > 0 &&
			qp->cbap.lastTxTimeNs <=
				std::numeric_limits<uint64_t>::max() - requiredGap ?
			qp->cbap.lastTxTimeNs + requiredGap : now;
		uint64_t next = std::max(now, safeNext);
		if (qp->m_nextAvail.GetTimeStep() > next)
			next = qp->m_nextAvail.GetTimeStep();
		qp->m_nextAvail = NanoSeconds(next);
		qp->cbap.v20CatchUpBurst = next < safeNext;
		NS_ASSERT_MSG(!qp->cbap.v20CatchUpBurst,
			"CBAP-v2.0 handoff created a catch-up burst");

		if (flow.hw->m_cc_mode ==
				CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN){
			Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
			Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
			Simulator::Cancel(qp->mlx.m_rpTimer);
			qp->mlx.m_targetRate = DataRate(inherited);
			qp->m_rate = DataRate(inherited);
			qp->mlx.m_alpha = 0.0;
			qp->mlx.m_alpha_cnp_arrived = false;
			qp->mlx.m_decrease_cnp_arrived = false;
			qp->mlx.m_first_cnp = true;
			qp->mlx.m_rpTimeStage = 0;
			qp->mlx.m_rpTimer = Simulator::Schedule(
				MicroSeconds(flow.hw->m_rpgTimeReset),
				&RdmaHw::RateIncEventTimerMlx, flow.hw, qp);
		}else{
			qp->hp.m_curRate = DataRate(inherited);
			for (uint32_t hop = 0; hop < IntHeader::maxHop; ++hop)
				qp->hp.hopState[hop].Rc = DataRate(inherited);
		}
		qp->cbap.handedOff = true;
		qp->cbap.phase = RdmaQueuePair::CBAP_BASE_CC_ONLY;
		uint32_t nic = flow.hw->GetNicIdxOfQp(qp);
		flow.hw->m_nic[nic].dev->UpdateNextAvail(qp->m_nextAvail);
		flow.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();

		for (uint32_t i = 0; i < s_cbapV20FlowRecords.size(); ++i){
			CbapV20FlowRecord &row = s_cbapV20FlowRecords[i];
			if (row.batchId != batchId || row.flowId != flow.flowId)
				continue;
			row.firstFreshFeedbackNs =
				qp->cbap.v20FirstFreshFeedbackNs;
			row.handoffInitialRateBps = inherited;
			row.postHandoffOwner = flow.hw->m_cc_mode ==
				CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ?
				"DCQCN" : "HPCC_INT";
			row.postHandoffCbapWriteCount =
				qp->cbap.v20PostHandoffCbapWriteCount;
			row.catchUpBurst = qp->cbap.v20CatchUpBurst;
		}
		CbapControllerOwnershipRecord owner = {};
		owner.timeNs = now;
		owner.epoch = s_cbapEpoch;
		owner.batchId = batchId;
		owner.flowId = flow.flowId;
		owner.phase = qp->cbap.phase;
		owner.owner = flow.hw->m_cc_mode ==
			CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN ?
			"DCQCN" : "HPCC_INT";
		owner.cbapRateUpdate = false;
		owner.dcqcnRateUpdate = false;
		s_cbapControllerOwnershipRecords.push_back(owner);
	}
	for (uint32_t i = 0; i < s_cbapV20BatchRecords.size(); ++i){
		CbapV20BatchRecord &row = s_cbapV20BatchRecords[i];
		if (row.batchId != batchId)
			continue;
		uint64_t aggregate = 0;
		bool pacingViolation = false;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flowIt =
				s_cbapFlows.begin(); flowIt != s_cbapFlows.end(); ++flowIt){
			if (flowIt->second.batchId != batchId || !flowIt->second.qp)
				continue;
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[flowIt->first];
			if (std::find(path.begin(), path.end(), row.linkId) != path.end())
				aggregate += flowIt->second.qp->
					cbap.v20HandoffInitialRateBps;
			pacingViolation = pacingViolation ||
				flowIt->second.qp->cbap.pacingViolationCount > 0;
		}
		row.actualAppliedAggregateBps = aggregate;
		row.firstFreshFeedbackNs = batch.firstFreshFeedbackNs;
		row.handoffNs = now;
		row.handoffReason = reason;
		row.postHandoffCbapWriteCount = 0;
		row.catchUpBurst = false;
		row.pacingViolation = pacingViolation;
	}
}

bool RdmaHw::HandoffCbapSbaFlow(Ptr<RdmaQueuePair> qp,
		uint64_t feedbackTimeNs)
{
	if (!qp || !qp->cbap.sbaEnabled || qp->cbap.handedOff ||
			qp->cbap.phase != RdmaQueuePair::CBAP_STARTUP_ADMISSION)
		return false;
	const uint32_t flowId = qp->crfm.flowId;
	const uint64_t actualApplied = qp->m_rate.GetBitRate();
	if (actualApplied == 0) {
		// A non-positive live rate is a state-machine fault, not a legal
		// DCQCN initial value.  Return to scheduler HOLD without installing
		// either a zero-rate controller or a fake 1-bps rate.
		s_cbapSbaController.HoldForInvalidAppliedRate(flowId);
		qp->cbap.phase = RdmaQueuePair::CBAP_ADMISSION_HOLD;
		qp->cbap.zeroGrantPaused = true;
		qp->cbap.sbaLastAppliedRateBps = 0;
		qp->m_nextAvail = Simulator::GetMaximumSimulationTime();
		uint32_t nic = GetNicIdxOfQp(qp);
		m_nic[nic].dev->InvalidateAndRescheduleRdma();
		return false;
	}
	NS_ASSERT_MSG(s_cbapSbaController.TrySetStartupAppliedRate(
		flowId, actualApplied),
		"CBAP-SBA lost startup ownership before feedback");
	uint64_t handoffRate = 0;
	if (!s_cbapSbaController.OnActionableFeedback(flowId,
			feedbackTimeNs, &handoffRate))
		return false;
	// The grant is already bounded by the QP's protocol maximum.  This is
	// the sole legal-range clip; no floor/base/target max chain is allowed.
	handoffRate = std::min(handoffRate, qp->m_max_rate.GetBitRate());
	if (handoffRate == 0) {
		s_cbapSbaController.HoldForInvalidAppliedRate(flowId);
		qp->cbap.phase = RdmaQueuePair::CBAP_ADMISSION_HOLD;
		qp->cbap.zeroGrantPaused = true;
		return false;
	}

	// Seed the post-handoff controller at exactly the granted rate so the
	// transition introduces no rate step.  Which controller receives the flow
	// is the only difference between the two SBA modes.
	qp->m_rate = DataRate(handoffRate);
	if (UsesHpccTelemetryMode(m_cc_mode)) {
		// HPCC drives from hp.m_curRate and, with MULTI_RATE on, from a
		// per-hop rate vector.  Both must start at the granted rate or
		// UpdateRateHp's first window would compute against a stale value.
		qp->hp.m_curRate = DataRate(handoffRate);
		if (m_multipleRate) {
			for (uint32_t i = 0; i < IntHeader::maxHop; i++)
				qp->hp.hopState[i].Rc = DataRate(handoffRate);
		}
		// m_lastUpdateSeq = 0 makes the first feedback initialise the window
		// rather than treat the admission phase as a measured interval.
		qp->hp.m_lastUpdateSeq = 0;
		qp->hp.m_incStage = 0;
	} else {
		Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
		Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
		Simulator::Cancel(qp->mlx.m_rpTimer);
		qp->mlx.m_targetRate = DataRate(handoffRate);
		qp->mlx.m_alpha = 0.0;
		qp->mlx.m_alpha_cnp_arrived = false;
		qp->mlx.m_decrease_cnp_arrived = false;
		qp->mlx.m_first_cnp = true;
		qp->mlx.m_rpTimeStage = 0;
	}
	qp->cbap.sbaFirstFeedbackNs = feedbackTimeNs;
	qp->cbap.firstFreshFeedbackNs = feedbackTimeNs;
	qp->cbap.sbaLastAppliedRateBps = handoffRate;
	qp->cbap.handoffRateBps = handoffRate;
	qp->cbap.sbaHandoffCount++;
	qp->cbap.handedOff = true;
	qp->cbap.exactGrantPacing = false;
	qp->cbap.zeroGrantPaused = false;
	qp->cbap.phase = RdmaQueuePair::CBAP_BASE_CC_ONLY;
	NS_ASSERT_MSG(qp->cbap.sbaHandoffCount == 1,
		"CBAP-SBA handed off a flow more than once");
	uint32_t nic = GetNicIdxOfQp(qp);
	m_nic[nic].dev->UpdateNextAvail(qp->m_nextAvail);
	m_nic[nic].dev->InvalidateAndRescheduleRdma();
	return true;
}

void RdmaHw::EvaluateCbapV20Batches(uint64_t now)
{
	for (std::map<uint32_t, CbapV20BatchRuntime>::iterator batchIt =
			s_cbapV20Batches.begin(); batchIt != s_cbapV20Batches.end();
			++batchIt){
		uint32_t batchId = batchIt->first;
		CbapV20BatchRuntime &batch = batchIt->second;
		if (batch.bypass || batch.handedOff || now < batch.releaseNs)
			continue;
		bool anyActive = false, allFresh = true, anyFresh = false;
		bool anyPostReleaseFeedback = false;
		bool pfc = false, queueHigh = false, pathStale = false;
		uint64_t allCompleteNs = 0, firstAnyNs = 0;
		for (std::map<uint32_t, CbapFlowRuntime>::iterator flowIt =
				s_cbapFlows.begin(); flowIt != s_cbapFlows.end(); ++flowIt){
			CbapFlowRuntime &flow = flowIt->second;
			if (flow.batchId != batchId || !flow.active || flow.finished ||
					!flow.qp || !flow.qp->cbap.v20Enabled)
				continue;
			anyActive = true;
			uint64_t firstSample = 0, completeDelivery = 0;
			bool complete = HasCompletePostReleaseFeedback(flow,
				firstSample, completeDelivery);
			allFresh = allFresh && complete;
			if (complete){
				anyFresh = true;
				allCompleteNs = std::max(allCompleteNs, completeDelivery);
				if (firstAnyNs == 0 || completeDelivery < firstAnyNs)
					firstAnyNs = completeDelivery;
				flow.qp->cbap.v20FirstFreshFeedbackNs = completeDelivery;
			}
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow.flowId];
			for (uint32_t hop = 0; hop < path.size(); ++hop){
				CbapLinkRuntime &link = s_cbapLinks[path[hop]];
				if (!link.initialized){
					pathStale = true;
					continue;
				}
				anyPostReleaseFeedback = anyPostReleaseFeedback ||
					(link.latest.sampleTimeNs > batch.releaseNs &&
					 link.latest.deliveryTimeNs > batch.releaseNs &&
					 link.latest.deliveryTimeNs <= now);
				uint64_t qHigh = (uint64_t)std::floor(0.80 *
					link.config.ecnThresholdBytes);
				pfc = pfc || link.latest.pfcEventsDelta > 0 ||
					link.latest.localPaused || link.latest.downstreamPaused;
				queueHigh = queueHigh || link.latest.queueBytes > qHigh;
				pathStale = pathStale || (link.latest.deliveryTimeNs > 0 &&
					now > link.latest.deliveryTimeNs +
					flow.qp->cbap.v20BlindWindowNs);
			}
		}
		if (!anyActive)
			continue;
		if (allFresh && allCompleteNs > 0){
			batch.firstFreshFeedbackNs = allCompleteNs;
		}else if (anyFresh && firstAnyNs > 0 &&
				batch.firstFreshFeedbackNs == 0){
			batch.firstFreshFeedbackNs = firstAnyNs;
		}
		if (pfc)
			ExecuteCbapV20Handoff(batchId, now, "pfc");
		else if (queueHigh)
			ExecuteCbapV20Handoff(batchId, now, "queue_above_q_high");
		else if (pathStale && now > batch.releaseNs)
			ExecuteCbapV20Handoff(batchId, now, "path_summary_stale");
		else if (batch.classification == CBAP_V20_C1_SINGLE_HOTSPOT &&
				allFresh)
			ExecuteCbapV20Handoff(batchId, now,
				"first_complete_fresh_feedback");
		else if (batch.classification == CBAP_V20_C2_COMPLEX &&
				anyPostReleaseFeedback)
			ExecuteCbapV20Handoff(batchId, now,
				"first_valid_post_release_feedback");
		else if (now >= batch.leaseExpiryNs)
			ExecuteCbapV20Handoff(batchId, now, "two_rtt_lease_expiry");
	}
}

void RdmaHw::EvaluateCbapV20Lease(uint32_t groupId)
{
	std::map<uint32_t, CbapV20BatchRuntime>::iterator it =
		s_cbapV20Batches.find(groupId);
	if (it == s_cbapV20Batches.end() || it->second.bypass ||
			it->second.handedOff)
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	if (now >= it->second.leaseExpiryNs)
		// Port-summary delivery may already be queued at this exact ns with a
		// later event UID. ScheduleNow keeps the 2-RTT timestamp while letting
		// all previously queued same-time fresh feedback become visible.
		Simulator::ScheduleNow(&RdmaHw::FinalizeCbapV20Lease, groupId);
}

void RdmaHw::FinalizeCbapV20Lease(uint32_t groupId)
{
	std::map<uint32_t, CbapV20BatchRuntime>::iterator it =
		s_cbapV20Batches.find(groupId);
	if (it == s_cbapV20Batches.end() || it->second.bypass ||
			it->second.handedOff)
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	EvaluateCbapV20Batches(now);
	if (!it->second.handedOff && now >= it->second.leaseExpiryNs)
		ExecuteCbapV20Handoff(groupId, now, "two_rtt_lease_expiry");
}

void RdmaHw::ExecuteCbapBatchDelegation(uint32_t batchId, uint64_t now)
{
	CbapHandoffBatchRecord &batch = s_cbapHandoffBatches[batchId];
	NS_ASSERT_MSG(!batch.handoffOccurred,
		"guarded delegation executed more than once for a batch");
	batch.handoffCandidateNs = now;
	batch.handoffExecuteNs = now;
	batch.handoffOccurred = true;
	batch.noHandoffReason = "none";
	batch.grantsBeforeHandoff = s_cbapBatchGrantMessages[batchId];
	batch.controlBytesBeforeHandoff =
		s_cbapBatchActiveSummaries[batchId] * s_cbapConfig.summaryBytes +
		batch.grantsBeforeHandoff * s_cbapConfig.grantBytes;
	for (std::map<uint32_t, CbapFlowRuntime>::iterator it =
			s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it){
		CbapFlowRuntime &flow = it->second;
		if (flow.batchId != batchId || !flow.active || flow.finished ||
				!flow.qp || flow.qp->cbap.delegatedEnvelope)
			continue;
		Ptr<RdmaQueuePair> qp = flow.qp;
		NS_ASSERT_MSG(qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING,
			"guarded delegation may only begin from TRACKING");
		uint64_t inherited = qp->m_rate.GetBitRate();
		NS_ASSERT_MSG(inherited > 0,
			"guarded delegation cannot initialize with zero rate");
		Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
		Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
		Simulator::Cancel(qp->mlx.m_rpTimer);
		qp->mlx.m_targetRate = DataRate(inherited);
		qp->mlx.m_alpha = 0.0;
		qp->mlx.m_alpha_cnp_arrived = false;
		qp->mlx.m_decrease_cnp_arrived = false;
		qp->mlx.m_first_cnp = true;
		qp->mlx.m_rpTimeStage = 0;
		qp->cbap.dcqcnDesiredRateBps = inherited;
		qp->cbap.envelopeAppliedRateBps = inherited;
		qp->cbap.envelopeScale = 1.0;
		qp->cbap.envelopeBound = false;
		qp->cbap.desiredRateLastUpdateNs = now;
		qp->cbap.appliedRateLastUpdateNs = now;
		qp->cbap.delegationExecuteNs = now;
		qp->cbap.delegationCount++;
		qp->cbap.delegatedEnvelope = true;
		qp->cbap.phase = RdmaQueuePair::CBAP_DELEGATED_ENVELOPE;
		qp->cbap.creditGateActive = false;
		qp->cbap.creditRemainingBytes = 0;
		qp->cbap.exactGrantPacing = true;
		qp->mlx.m_rpTimer = Simulator::Schedule(
			MicroSeconds(flow.hw->m_rpgTimeReset),
			&RdmaHw::RateIncEventTimerMlx, flow.hw, qp);
		CbapControllerOwnershipRecord owner = {};
		owner.timeNs = now; owner.epoch = s_cbapEpoch;
		owner.batchId = batchId; owner.flowId = flow.flowId;
		owner.phase = qp->cbap.phase;
		owner.owner = "ENVELOPE_PROJECTOR";
		owner.cbapRateUpdate = false; owner.dcqcnRateUpdate = false;
		s_cbapControllerOwnershipRecords.push_back(owner);
	}
}

void RdmaHw::SetCbapEnvelopeAppliedRate(CbapFlowRuntime &flow,
		uint64_t rateBps)
{
	Ptr<RdmaQueuePair> qp = flow.qp;
	if (!qp || flow.finished)
		return;
	NS_ASSERT_MSG(qp->cbap.delegatedEnvelope &&
		qp->cbap.phase == RdmaQueuePair::CBAP_DELEGATED_ENVELOPE,
		"envelope projector attempted to write a non-delegated flow");
	rateBps = std::min(rateBps, qp->m_max_rate.GetBitRate());
	uint64_t now = Simulator::Now().GetTimeStep();
	bool paused = rateBps == 0;
	bool changed = qp->m_rate.GetBitRate() != rateBps ||
		qp->cbap.zeroGrantPaused != paused;
	if (changed){
		uint64_t oldSchedule = qp->m_nextAvail.GetTimeStep();
		RecordCbapTxEvent(qp, CBAP_TX_CANCEL_OR_INVALIDATE,
			oldSchedule, 0, qp->cbap.lastTxTimeNs, 0, 0, 7);
		if (paused){
			if (!qp->cbap.zeroGrantPaused){
				qp->cbap.zeroGrantPauseCount++;
				qp->cbap.zeroGrantPauseStartNs = now;
			}
			qp->cbap.zeroGrantPaused = true;
			qp->m_rate = DataRate(0);
			qp->m_nextAvail = Simulator::GetMaximumSimulationTime();
		}else{
			if (qp->cbap.zeroGrantPaused){
				qp->cbap.zeroGrantResumeCount++;
				if (now >= qp->cbap.zeroGrantPauseStartNs)
					qp->cbap.zeroGrantPausedNs +=
						now - qp->cbap.zeroGrantPauseStartNs;
			}
			qp->cbap.zeroGrantPaused = false;
			flow.hw->ChangeRate(qp, DataRate(rateBps));
			if (qp->m_nextAvail < Simulator::Now())
				qp->m_nextAvail = Simulator::Now();
		}
		uint32_t nic = flow.hw->GetNicIdxOfQp(qp);
		flow.hw->m_nic[nic].dev->InvalidateAndRescheduleRdma();
		qp->cbap.simulatorInternalRateWrites++;
	}
	qp->cbap.envelopeAppliedRateBps = rateBps;
	qp->cbap.currentRateBps = rateBps;
	qp->cbap.requestedRateBps = rateBps;
	qp->cbap.appliedRateLastUpdateNs = now;
	CbapControllerOwnershipRecord owner = {};
	owner.timeNs = now; owner.epoch = s_cbapEpoch;
	owner.batchId = qp->cbap.batchId; owner.flowId = flow.flowId;
	owner.phase = qp->cbap.phase; owner.owner = "ENVELOPE_PROJECTOR";
	owner.cbapRateUpdate = false; owner.dcqcnRateUpdate = false;
	s_cbapControllerOwnershipRecords.push_back(owner);
}

void RdmaHw::ProjectCbapDelegatedEnvelope(uint64_t now)
{
	std::set<uint32_t> batches;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator it =
			s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it)
		if (it->second.active && !it->second.finished && it->second.qp &&
				it->second.qp->cbap.delegatedEnvelope)
			batches.insert(it->second.batchId);
	for (std::set<uint32_t>::const_iterator batchIt = batches.begin();
			batchIt != batches.end(); ++batchIt){
		// All currently delegated newcomer flows are projected together.
		// The first batch id is only an audit label for the shared envelope;
		// later batch iterator entries must not run a second projection.
		if (batchIt != batches.begin())
			break;
		uint32_t batchId = *batchIt;
		std::vector<uint32_t> flows;
		std::set<uint32_t> links;
		for (std::map<uint32_t, CbapFlowRuntime>::const_iterator it =
				s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it)
			if (it->second.active && !it->second.finished && it->second.qp &&
					it->second.qp->cbap.delegatedEnvelope){
				flows.push_back(it->first);
				const std::vector<uint32_t> &path = s_cbapFlowPaths[it->first];
				links.insert(path.begin(), path.end());
			}
		std::map<uint32_t, uint64_t> budgets, desiredSums, reserves;
		std::map<uint32_t, double> scales;
		std::map<uint32_t, bool> stale;
		for (std::set<uint32_t>::const_iterator linkIt = links.begin();
				linkIt != links.end(); ++linkIt){
			uint32_t linkId = *linkIt;
			CbapLinkRuntime &link = s_cbapLinks[linkId];
			uint64_t effective = link.initialized ?
				link.latest.effectiveCapacityBps :
				link.previousEffectiveCapacityBps;
			uint64_t reserve = 0;
			for (std::map<uint32_t, CbapFlowRuntime>::const_iterator inc =
					s_cbapFlows.begin(); inc != s_cbapFlows.end(); ++inc){
				if (!inc->second.active || inc->second.finished || !inc->second.qp ||
						inc->second.qp->cbap.delegatedEnvelope)
					continue;
				const std::vector<uint32_t> &path = s_cbapFlowPaths[inc->first];
				if (std::find(path.begin(), path.end(), linkId) == path.end())
					continue;
				Ptr<RdmaQueuePair> qp = inc->second.qp;
				uint64_t floor = 0;
				if (now <= qp->cbap.rebalanceStartNs)
					floor = qp->cbap.protectionFloorBps;
				else if (now < qp->cbap.rebalanceEndNs &&
						qp->cbap.rebalanceEndNs > qp->cbap.rebalanceStartNs)
					floor = (uint64_t)((long double)qp->cbap.protectionFloorBps *
						(qp->cbap.rebalanceEndNs - now) /
						(qp->cbap.rebalanceEndNs - qp->cbap.rebalanceStartNs));
				uint64_t measured = (qp->cbap.recentActualRateBps[0] +
					qp->cbap.recentActualRateBps[1]) / 2;
				if (measured == 0) measured = qp->m_rate.GetBitRate();
				uint64_t demandFloor = (uint64_t)std::floor(0.90L * measured);
				reserve += std::max(floor, demandFloor);
			}
			for (std::map<uint32_t, CbapScopeBaseFlowRuntime>::const_iterator inc =
					s_cbapScopeBaseFlows.begin(); inc != s_cbapScopeBaseFlows.end(); ++inc){
				if (!inc->second.qp || inc->second.qp->IsFinished()) continue;
				const std::vector<uint32_t> &path = s_cbapFlowPaths[inc->first];
				if (std::find(path.begin(), path.end(), linkId) == path.end()) continue;
				uint64_t floor = 0;
				if (now <= inc->second.rebalanceStartNs) floor = inc->second.protectionFloorBps;
				else if (now < inc->second.rebalanceEndNs &&
						inc->second.rebalanceEndNs > inc->second.rebalanceStartNs)
					floor = (uint64_t)((long double)inc->second.protectionFloorBps *
						(inc->second.rebalanceEndNs - now) /
						(inc->second.rebalanceEndNs - inc->second.rebalanceStartNs));
				uint64_t demandFloor = (uint64_t)std::floor(0.90L *
					inc->second.qp->m_rate.GetBitRate());
				reserve += std::max(floor, demandFloor);
			}
			uint64_t desired = 0;
			for (uint32_t i = 0; i < flows.size(); ++i){
				const std::vector<uint32_t> &path = s_cbapFlowPaths[flows[i]];
				if (std::find(path.begin(), path.end(), linkId) != path.end())
					desired += s_cbapFlows[flows[i]].qp->cbap.dcqcnDesiredRateBps;
			}
			uint64_t budget = effective > reserve ? effective - reserve : 0;
			uint64_t staleLimit = 2 * s_cbapConfig.controlEpochNs;
			for (uint32_t i = 0; i < flows.size(); ++i)
				staleLimit = std::max(staleLimit,
					s_cbapFlows[flows[i]].qp->m_baseRtt);
			bool isStale = !link.initialized || now >
				link.latest.deliveryTimeNs + staleLimit;
			for (uint32_t i = 0; i < flows.size(); ++i)
				if (s_cbapConfig.delegationDiagnosticForceStaleEpochs > 0 &&
						now < s_cbapFlows[flows[i]].qp->cbap.delegationExecuteNs +
						s_cbapConfig.delegationDiagnosticForceStaleEpochs *
							s_cbapConfig.controlEpochNs)
					isStale = true;
			uint64_t key = ((uint64_t)batchId << 32) | linkId;
			uint64_t previous = s_cbapEnvelopeLastBudget.count(key) ?
				s_cbapEnvelopeLastBudget[key] : budget;
			if (isStale && budget > previous) budget = previous;
			s_cbapEnvelopeLastBudget[key] = budget;
			budgets[linkId] = budget; desiredSums[linkId] = desired;
			reserves[linkId] = reserve; stale[linkId] = isStale;
			scales[linkId] = desired > budget && desired > 0 ?
				(double)((long double)budget / desired) : 1.0;
		}
		std::map<uint32_t, uint64_t> appliedSums;
		for (uint32_t i = 0; i < flows.size(); ++i){
			CbapFlowRuntime &flow = s_cbapFlows[flows[i]];
			Ptr<RdmaQueuePair> qp = flow.qp;
			double pathScale = 1.0;
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flows[i]];
			for (uint32_t hop = 0; hop < path.size(); ++hop)
				pathScale = std::min(pathScale, scales[path[hop]]);
			uint64_t applied = (uint64_t)std::floor(
				(long double)qp->cbap.dcqcnDesiredRateBps * pathScale);
			qp->cbap.envelopeScale = pathScale;
			qp->cbap.envelopeBound = applied < qp->cbap.dcqcnDesiredRateBps;
			SetCbapEnvelopeAppliedRate(flow, applied);
			for (uint32_t hop = 0; hop < path.size(); ++hop)
				appliedSums[path[hop]] += applied;
			CbapEnvelopeFlowRecord row = {};
			row.epochNs = now; row.epoch = s_cbapEpoch;
			row.batchId = qp->cbap.batchId; row.flowId = flows[i];
			row.desiredRateBps = qp->cbap.dcqcnDesiredRateBps;
			row.appliedRateBps = applied; row.pathScale = pathScale;
			row.envelopeBound = qp->cbap.envelopeBound;
			row.positiveAiSuppressed = qp->cbap.positiveAiSuppressed;
			row.decreaseApplied = qp->cbap.decreaseApplied;
			row.packetGapNs = applied ? CbapPacketGapNs(
				qp->cbap.lastPacketWireBytes ? qp->cbap.lastPacketWireBytes :
				s_cbapConfig.maxWirePacketBytes, applied) : 0;
			row.simulatorInternalRateWriteCount =
				qp->cbap.simulatorInternalRateWrites;
			row.postDelegationFullCbapGrantCount =
				s_cbapBatchGrantMessages[qp->cbap.batchId] -
				s_cbapHandoffBatches[qp->cbap.batchId].grantsBeforeHandoff;
			row.desiredWriter = "DCQCN";
			row.appliedWriter = "ENVELOPE_PROJECTOR";
			s_cbapEnvelopeFlowRecords.push_back(row);
		}
		for (std::set<uint32_t>::const_iterator linkIt = links.begin();
				linkIt != links.end(); ++linkIt){
			uint32_t linkId = *linkIt;
			uint64_t tolerance = std::max((uint64_t)1,
				(uint64_t)std::ceil(1e-9L * s_cbapLinks[linkId].config.capacityBps));
			CbapEnvelopeLinkRecord row = {};
			row.epochNs = now; row.epoch = s_cbapEpoch; row.batchId = batchId;
			row.linkId = linkId;
			row.effectiveCapacityBps = s_cbapLinks[linkId].initialized ?
				s_cbapLinks[linkId].latest.effectiveCapacityBps :
				s_cbapLinks[linkId].previousEffectiveCapacityBps;
			row.incumbentReserveBps = reserves[linkId];
			row.batchBudgetBps = budgets[linkId];
			row.delegatedFlowCount = 0;
			for (uint32_t i = 0; i < flows.size(); ++i){
				const std::vector<uint32_t> &path = s_cbapFlowPaths[flows[i]];
				if (std::find(path.begin(), path.end(), linkId) != path.end())
					row.delegatedFlowCount++;
			}
			row.desiredRateSumBps = desiredSums[linkId];
			row.appliedRateSumBps = appliedSums[linkId];
			row.scale = scales[linkId]; row.staleFeedback = stale[linkId];
			row.capIncreaseAllowed = !stale[linkId];
			uint64_t previousReserve = row.incumbentReserveBps;
			for (std::vector<CbapEnvelopeLinkRecord>::const_reverse_iterator prev =
					s_cbapEnvelopeLinkRecords.rbegin();
					prev != s_cbapEnvelopeLinkRecords.rend(); ++prev)
				if (prev->batchId == batchId && prev->linkId == linkId){
					previousReserve = prev->incumbentReserveBps; break;
				}
			row.reserveReleaseBps = previousReserve > row.incumbentReserveBps ?
				previousReserve - row.incumbentReserveBps : 0;
			row.capacityExcessBps = row.appliedRateSumBps > row.batchBudgetBps ?
				row.appliedRateSumBps - row.batchBudgetBps : 0;
			row.capacityViolation = row.capacityExcessBps > tolerance;
			NS_ASSERT_MSG(!row.capacityViolation,
				"guarded envelope exceeded delegated batch budget");
			s_cbapEnvelopeLinkRecords.push_back(row);
			s_cbapLogicalEnvelopeUpdates++;
			s_cbapLogicalEnvelopeBytes += s_cbapConfig.summaryBytes;
		}
	}
}

void RdmaHw::EvaluateCbapHandoffBatches(uint64_t now)
{
	std::set<uint32_t> candidateBatches;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
		if (flow->second.active && !flow->second.finished && flow->second.qp &&
				(flow->second.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
				 flow->second.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
				 flow->second.hw->m_cc_mode ==
					CC_MODE_CBAP_FULL_GUARDED_DELEGATION))
			candidateBatches.insert(flow->second.batchId);

	for (std::set<uint32_t>::const_iterator batchId =
			candidateBatches.begin(); batchId != candidateBatches.end(); ++batchId){
		CbapHandoffBatchRecord &batch = s_cbapHandoffBatches[*batchId];
		if (batch.handoffOccurred){
			batch.grantsAfterHandoff = s_cbapBatchGrantMessages[*batchId] -
				batch.grantsBeforeHandoff;
			batch.controlBytesAfterHandoff =
				batch.grantsAfterHandoff * s_cbapConfig.grantBytes;
			continue;
		}
		std::vector<CbapFlowRuntime *> flows;
		std::set<uint32_t> links;
		uint32_t mode = 0;
		uint64_t trackingEnter = 0, measuredRtt = 0;
		uint64_t remaining = 0, total = 0, rateSum = 0;
		bool ready = true;
		std::string reason = "stable_epochs";
		for (std::map<uint32_t, CbapFlowRuntime>::iterator it =
				s_cbapFlows.begin(); it != s_cbapFlows.end(); ++it){
			CbapFlowRuntime &flow = it->second;
			if (flow.batchId != *batchId || !flow.active || flow.finished ||
					!flow.qp || flow.qp->cbap.handedOff ||
					flow.qp->cbap.delegatedEnvelope)
				continue;
			flows.push_back(&flow);
			mode = flow.hw->m_cc_mode;
			Ptr<RdmaQueuePair> qp = flow.qp;
			trackingEnter = std::max(trackingEnter,
				qp->cbap.trackingStartNs);
			measuredRtt = std::max(measuredRtt, qp->m_baseRtt);
			uint64_t roundStart = 0, roundEnd = qp->m_size;
			if (flow.roundIndex < qp->crfm.rounds.size()){
				roundStart = qp->crfm.rounds[flow.roundIndex].startSeq;
				roundEnd = qp->crfm.rounds[flow.roundIndex].endSeq;
			}
			total += roundEnd - roundStart;
			remaining += roundEnd > qp->snd_una ? roundEnd - qp->snd_una : 0;
			rateSum += qp->m_rate.GetBitRate();
			const std::vector<uint32_t> &path = s_cbapFlowPaths[flow.flowId];
			links.insert(path.begin(), path.end());
			uint64_t firstSample = 0, completeDelivery = 0;
			bool complete = HasCompletePostReleaseFeedback(flow,
				firstSample, completeDelivery);
			uint64_t staleLimit = std::max(qp->m_baseRtt,
				2 * s_cbapConfig.controlEpochNs);
			if (qp->cbap.phase != RdmaQueuePair::CBAP_TRACKING ||
					qp->cbap.creditGateActive || qp->cbap.zeroGrantPaused){
				ready = false;
				reason = qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY ?
					"recovery" : "not_tracking";
			}else if (!complete || completeDelivery == 0 ||
					now > completeDelivery + staleLimit){
				ready = false;
				reason = "incomplete_or_stale_feedback";
			}else if (qp->cbap.lastCbapCnpNs > 0 &&
					now <= qp->cbap.lastCbapCnpNs + staleLimit){
				ready = false;
				reason = "unresolved_cnp";
			}
		}
		batch.trackingEnterNs = trackingEnter;
		batch.measuredRttNs = measuredRtt;
		batch.minimumTrackingTimeNs = std::max(2 * measuredRtt,
			2 * s_cbapConfig.controlEpochNs);
		batch.activeFlowCount = flows.size();
		batch.remainingBytesTotal = remaining;
		batch.remainingFraction = total ? (double)remaining / total : 0;
		batch.appliedRateSumBefore = rateSum;
		if (flows.empty() || remaining == 0){
			batch.noHandoffReason = "completed_before_handoff";
			continue;
		}

		bool pathStable = !links.empty();
		uint64_t maximumQueue = 0;
		double maximumGradient = 0;
		for (std::set<uint32_t>::const_iterator linkId = links.begin();
				linkId != links.end(); ++linkId){
			CbapLinkRuntime &link = s_cbapLinks[*linkId];
			if (!link.initialized){
				pathStable = false;
				reason = "missing_link_summary";
				continue;
			}
			const CbapPortRecord &port = link.latest;
			maximumQueue = std::max(maximumQueue, port.queueBytes);
			maximumGradient = std::max(maximumGradient,
				port.queueGradientBytesPerSecond);
			uint64_t qLow = (uint64_t)std::floor(0.25 *
				link.config.ecnThresholdBytes);
			double gradientThreshold = s_cbapConfig.epsilonRate *
				link.config.capacityBps / 8.0;
			bool stateStable = port.portState == CBAP_PORT_CLEAR ||
				port.portState == CBAP_PORT_STABLE;
			uint64_t linkStaleLimit = std::max(measuredRtt,
				2 * s_cbapConfig.controlEpochNs);
			bool causalFresh = port.sampleTimeNs > batch.networkReleaseNs &&
				port.deliveryTimeNs > batch.networkReleaseNs &&
				now <= port.deliveryTimeNs + linkStaleLimit;
			bool capacityViolation = false;
			for (std::vector<CbapAppliedRateAuditRecord>::const_reverse_iterator
					audit = s_cbapAppliedRateAuditRecords.rbegin();
					audit != s_cbapAppliedRateAuditRecords.rend(); ++audit)
				if (audit->linkId == *linkId){
					capacityViolation = audit->appliedCapacityViolation;
					break;
				}
			if (!causalFresh || !stateStable || port.queueBytes > qLow ||
					port.queueGradientBytesPerSecond > gradientThreshold ||
					port.arrivalRateBps > (s_cbapConfig.rho +
						s_cbapConfig.epsilonRate) * port.capacityBps ||
					port.pfcEventsDelta > 0 || port.localPaused ||
					port.downstreamPaused || capacityViolation){
				pathStable = false;
				reason = "link_not_clear_stable";
			}
		}
		batch.queueBytesAtHandoff = maximumQueue;
		batch.queueGradientAtHandoff = maximumGradient;
		if (s_cbapConfig.handoffDiagnosticForceRoot){
			pathStable = false;
			reason = "diagnostic_persistent_root";
		}
		if (s_cbapConfig.handoffDiagnosticRecoveryUntilEpoch > 0 &&
				trackingEnter > 0 && now < trackingEnter +
				s_cbapConfig.handoffDiagnosticRecoveryUntilEpoch *
					s_cbapConfig.controlEpochNs){
			ready = false;
			reason = "diagnostic_recovery";
		}
		if (pathStable){
			if (batch.stableEpochCount == 0)
				batch.firstStableEpochNs = now;
			batch.stableEpochCount++;
		}else{
			batch.stableEpochCount = 0;
			batch.firstStableEpochNs = 0;
		}
		if (trackingEnter == 0 || now < trackingEnter +
				batch.minimumTrackingTimeNs){
			ready = false;
			reason = "minimum_tracking_time";
		}
		bool candidate = ready && pathStable &&
			batch.stableEpochCount >= s_cbapConfig.handoffStableEpochsRequired;
		batch.noHandoffReason = candidate ? "none" : reason;
		if (!candidate)
			continue;
		if (mode == CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX){
			if (batch.shadowHandoffCandidateNs == 0){
				batch.shadowHandoffCandidateNs = now;
				batch.shadowRemainingBytes = remaining;
				batch.shadowRemainingFraction = batch.remainingFraction;
				batch.shadowQueueBytes = maximumQueue;
				batch.shadowRateSumBps = rateSum;
				batch.noHandoffReason = "v13_shadow_only";
			}
		}else if (mode == CC_MODE_CBAP_FULL_STABLE_HANDOFF){
			batch.handoffCandidateNs = now;
			ExecuteCbapBatchHandoff(*batchId, now);
		}else if (mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION){
			batch.handoffCandidateNs = now;
			ExecuteCbapBatchDelegation(*batchId, now);
		}
	}
}

void RdmaHw::RecomputeCbapTracking()
{
	if (!s_cbapConfig.enabled)
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	bool hasSba = false;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
		if (flow->second.qp && flow->second.qp->cbap.sbaEnabled &&
				!flow->second.finished) {
			hasSba = true;
			break;
		}
	if (hasSba) {
		EvaluateCbapSbaReadmission(now, "control_tick");
		return;
	}
	EvaluateCbapV20Batches(now);
	std::vector<uint32_t> active;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator flow =
			s_cbapFlows.begin(); flow != s_cbapFlows.end(); ++flow)
		if (flow->second.active && !flow->second.finished &&
				flow->second.qp && !flow->second.qp->cbap.handedOff &&
				!flow->second.qp->cbap.delegatedEnvelope &&
				!flow->second.qp->cbap.v20Enabled)
			active.push_back(flow->first);
	if (active.empty()){
		EvaluateCbapHandoffBatches(now);
		ProjectCbapDelegatedEnvelope(now);
		return;
	}
	std::map<uint32_t, uint64_t> capacities;
	for (std::map<uint32_t, CbapLinkRuntime>::const_iterator link =
			s_cbapLinks.begin(); link != s_cbapLinks.end(); ++link)
		capacities[link->first] = link->second.initialized ?
			link->second.latest.effectiveCapacityBps :
			link->second.previousEffectiveCapacityBps;
	for (std::map<uint32_t, uint64_t>::const_iterator capacity =
			capacities.begin(); capacity != capacities.end(); ++capacity){
		// plannerCapacityBps is an audit contract, not a controller input.
		// While any flow on this link remains in Admission Hold, its applied
		// rate is still governed by the admission plan (including the frozen
		// queue-credit allowance).  Do not relabel that plan with the later
		// tracking capacity before the hold actually exits.
		bool admissionActive = false;
		for (uint32_t i = 0; i < active.size() && !admissionActive; ++i){
			Ptr<RdmaQueuePair> qp = s_cbapFlows[active[i]].qp;
			const std::vector<uint32_t> &path =
				s_cbapFlowPaths[active[i]];
			admissionActive = qp->cbap.phase ==
					RdmaQueuePair::CBAP_ADMISSION_HOLD &&
				std::find(path.begin(), path.end(), capacity->first) !=
					path.end();
		}
		if (!admissionActive)
			s_cbapLinks[capacity->first].plannerCapacityBps =
				capacity->second;
	}
	std::map<uint32_t, uint64_t> floors;
	for (uint32_t i = 0; i < active.size(); ++i){
		Ptr<RdmaQueuePair> qp = s_cbapFlows[active[i]].qp;
		uint64_t floor = 0;
		if (qp->cbap.protectionFloorBps > 0 &&
				now < qp->cbap.rebalanceEndNs){
			if (now <= qp->cbap.rebalanceStartNs)
				floor = qp->cbap.protectionFloorBps;
			else{
				uint64_t span = qp->cbap.rebalanceEndNs -
					qp->cbap.rebalanceStartNs;
				uint64_t left = qp->cbap.rebalanceEndNs - now;
				floor = (uint64_t)((long double)
					qp->cbap.protectionFloorBps * left / span);
			}
		}
		floors[active[i]] = floor;
	}
	std::map<uint32_t, uint64_t> targets =
		ComputeCbapProgressiveFill(active, capacities, floors);
	for (uint32_t i = 0; i < active.size(); ++i){
		CbapFlowRuntime &flow = s_cbapFlows[active[i]];
		Ptr<RdmaQueuePair> qp = flow.qp;
		const std::vector<uint32_t> &path = s_cbapFlowPaths[active[i]];
		uint64_t firstPostSample = 0, completeDelivery = 0;
		bool allFresh = HasCompletePostReleaseFeedback(
			flow, firstPostSample, completeDelivery);
		if (firstPostSample > 0 &&
				(qp->cbap.firstPostReleaseSampleNs == 0 ||
				 firstPostSample < qp->cbap.firstPostReleaseSampleNs))
			qp->cbap.firstPostReleaseSampleNs = firstPostSample;
		bool stale = false, severe = false;
		bool root = false, propagated = false, mixed = false;
		bool allClearStable = true;
		uint32_t rootId = 0;
		uint64_t newestFeedback = 0;
		for (uint32_t hop = 0; hop < path.size(); ++hop){
			CbapLinkRuntime &link = s_cbapLinks[path[hop]];
			bool postRelease = link.initialized &&
				link.latest.sampleTimeNs > qp->cbap.networkReleaseNs &&
				link.latest.deliveryTimeNs > qp->cbap.networkReleaseNs;
			if (!postRelease){
				allClearStable = false;
				continue;
			}
			if (qp->cbap.firstPostReleaseSampleNs == 0 ||
					link.latest.sampleTimeNs <
						qp->cbap.firstPostReleaseSampleNs)
				qp->cbap.firstPostReleaseSampleNs =
					link.latest.sampleTimeNs;
			if (qp->cbap.firstFreshFeedbackNs == 0 ||
					link.latest.deliveryTimeNs <
						qp->cbap.firstFreshFeedbackNs)
				qp->cbap.firstFreshFeedbackNs =
					link.latest.deliveryTimeNs;
			newestFeedback = std::max(newestFeedback,
				link.latest.deliveryTimeNs);
			uint64_t staleLimit = std::max(qp->m_baseRtt,
				2 * s_cbapConfig.controlEpochNs);
			if (now > link.latest.deliveryTimeNs + staleLimit)
				stale = true;
			uint64_t qHigh = (uint64_t)std::floor(0.80 *
				link.config.ecnThresholdBytes);
			severe = severe || link.latest.queueBytes >= qHigh ||
				link.latest.pfcEventsDelta > 0 ||
				link.latest.localPaused;
			if (link.latest.portState == CBAP_PORT_ROOT_CONGESTED){
				root = true;
				rootId = link.latest.rootId;
			}else if (link.latest.portState == CBAP_PORT_PROPAGATED){
				propagated = true;
				if (rootId == 0)
					rootId = link.latest.rootId;
			}else if (link.latest.portState ==
					CBAP_PORT_MIXED_OR_UNCERTAIN){
				mixed = true;
			}
			allClearStable = allClearStable &&
				(link.latest.portState == CBAP_PORT_CLEAR ||
				 link.latest.portState == CBAP_PORT_STABLE);
		}
		qp->cbap.targetRateBps = targets[active[i]];
		if (s_cbapConfig.rateFloorSemanticZeroTest &&
				flow.flowId == s_cbapConfig.rateFloorSemanticZeroFlow){
			if (s_cbapEpoch >=
					s_cbapConfig.rateFloorSemanticZeroStartEpoch &&
					s_cbapEpoch <
					s_cbapConfig.rateFloorSemanticZeroEndEpoch){
				qp->cbap.targetRateBps = 0;
				SetCbapRate(flow, 0, 6, 0, false);
				continue;
			}
			if (s_cbapEpoch ==
					s_cbapConfig.rateFloorSemanticZeroEndEpoch &&
					qp->cbap.zeroGrantPaused){
				SetCbapRate(flow, targets[active[i]], 6, 0, false);
				continue;
			}
		}
		if (qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD &&
				!allFresh){
			qp->cbap.stableEpochCount = 0;
			uint32_t emergencyRoot = 0;
			if (HasPostReleaseEmergencyEvidence(flow, emergencyRoot)){
				uint64_t current = qp->m_rate.GetBitRate();
				uint64_t emergency = std::min(current / 2,
					(uint64_t)std::floor(0.8L *
						targets[active[i]]));
				SetCbapRate(flow, emergency, 4, emergencyRoot, false);
			}
			// Ordinary tracking decisions are forbidden until every path link
			// has a sample and delivery strictly after network release.
			continue;
		}
		if (qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD){
			ExitCbapAdmission(qp, completeDelivery);
			if (qp->cbap.initOnly){
				qp->mlx.m_targetRate =
					DataRate(qp->m_rate.GetBitRate());
				qp->cbap.currentRateBps =
					qp->m_rate.GetBitRate();
				continue;
			}
		}
		if (!allFresh){
			qp->cbap.stableEpochCount = 0;
		}else{
			qp->cbap.lastFreshFeedbackNs = newestFeedback;
			qp->cbap.stableEpochCount = allClearStable ?
				qp->cbap.stableEpochCount + 1 : 0;
		}
		if (qp->cbap.initOnly)
			continue;
		if (stale){
			qp->cbap.staleFeedbackCount++;
			if (!severe){
				SetCbapRate(flow, qp->m_rate.GetBitRate(),
					5, rootId, true);
				continue;
			}
		}
		uint64_t current = qp->m_rate.GetBitRate();
		uint64_t target = targets[active[i]];
		if (qp->cbap.increaseFreezeEpochs > 0)
			qp->cbap.increaseFreezeEpochs--;
		if (severe){
			qp->cbap.phase = RdmaQueuePair::CBAP_RECOVERY;
			qp->cbap.creditGateActive = false;
			if (qp->cbap.creditGateEnterNs > 0 &&
					qp->cbap.creditGateExitNs == 0)
				qp->cbap.creditGateExitNs = now;
			qp->cbap.creditRemainingBytes = 0;
			qp->cbap.increaseFreezeEpochs = 2;
			uint64_t emergency = std::min(current / 2,
				(uint64_t)std::floor(0.8L * target));
			SetCbapRate(flow, emergency, 4, rootId, stale);
			continue;
		}
		if (qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY){
			if (qp->cbap.handoffEnabled &&
					s_cbapConfig.handoffDiagnosticRecoveryUntilEpoch > 0 &&
					now < qp->cbap.trackingStartNs +
					s_cbapConfig.handoffDiagnosticRecoveryUntilEpoch *
						s_cbapConfig.controlEpochNs){
				SetCbapRate(flow, std::min(current, target),
					5, rootId, stale);
				continue;
			}
			if (qp->cbap.stableEpochCount >= 2)
				qp->cbap.phase = RdmaQueuePair::CBAP_TRACKING;
			else{
				SetCbapRate(flow, std::min(current, target),
					5, rootId, stale);
				continue;
			}
		}
		if (root || target * 100 < current * 95){
			SetCbapRate(flow, target, root ? 2 : 2, rootId, stale);
		}else if (mixed || propagated || !allFresh){
			SetCbapRate(flow, std::min(current, target),
				5, rootId, stale);
		}else if (qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING &&
				qp->cbap.increaseFreezeEpochs == 0 &&
				qp->cbap.stableEpochCount >= 2 &&
				target * 100 > current * 105){
			// Keep the legacy candidate bit-for-bit identical to CBAP-v1.
			uint64_t fractionalCandidate = (uint64_t)std::floor(
				1.10L * current);
			uint64_t absoluteCandidate = current <=
				std::numeric_limits<uint64_t>::max() -
					s_cbapConfig.increaseAbsoluteBps ?
				current + s_cbapConfig.increaseAbsoluteBps :
				std::numeric_limits<uint64_t>::max();
			uint64_t policyCandidate =
				s_cbapConfig.increasePolicy ==
					CBAP_INCREASE_ADAPTIVE_V11 ?
				std::max(fractionalCandidate, absoluteCandidate) :
				std::min(fractionalCandidate, absoluteCandidate);
			uint64_t increased = std::min(target,
				std::min(qp->m_max_rate.GetBitRate(), policyCandidate));
			uint32_t limitingLink = 0;
			long double smallestSlack =
				std::numeric_limits<long double>::max();
			for (uint32_t hop = 0; hop < path.size(); ++hop){
				uint64_t used = 0;
				for (uint32_t peer = 0; peer < active.size(); ++peer){
					const std::vector<uint32_t> &peerPath =
						s_cbapFlowPaths[active[peer]];
					if (std::find(peerPath.begin(), peerPath.end(),
							path[hop]) != peerPath.end())
						used += targets[active[peer]];
				}
				long double slack = capacities[path[hop]] > used ?
					capacities[path[hop]] - used : 0;
				if (slack < smallestSlack){
					smallestSlack = slack;
					limitingLink = path[hop];
				}
			}
			NS_ASSERT_MSG(increased >= current && increased <= target &&
				increased <= qp->m_max_rate.GetBitRate(),
				"CBAP increase violates rate bounds");
			CbapIncreaseRecord increase = {};
			increase.timestampNs = now;
			increase.scenario = s_cbapConfig.scenario;
			increase.algorithm = s_cbapConfig.algorithm;
			increase.cbapVersion = s_cbapConfig.cbapVersion;
			increase.increasePolicy = s_cbapConfig.increasePolicy;
			increase.flowId = flow.flowId;
			increase.batchId = qp->cbap.batchId;
			increase.phase = qp->cbap.phase;
			increase.currentRateBeforeBps = current;
			increase.targetRateBps = target;
			increase.maxRateBps = qp->m_max_rate.GetBitRate();
			increase.fractionalCandidateBps = fractionalCandidate;
			increase.absoluteCandidateBps = absoluteCandidate;
			increase.selectedDeltaBps = increased - current;
			increase.newRateBps = increased;
			increase.stableEpochCount = qp->cbap.stableEpochCount;
			increase.feedbackAgeNs = qp->cbap.lastFreshFeedbackNs > 0 &&
				now >= qp->cbap.lastFreshFeedbackNs ?
				now - qp->cbap.lastFreshFeedbackNs : 0;
			increase.staleFeedback = stale;
			increase.limitingLink = limitingLink;
			increase.reason = 3;
			s_cbapIncreaseRecords.push_back(increase);
			SetCbapRate(flow, increased, 3, rootId, stale);
		}else{
			SetCbapRate(flow, current, 5, rootId, stale);
		}
		uint64_t updated = qp->m_rate.GetBitRate();
		if (target > 0){
			if (qp->cbap.firstFair80Ns == 0 &&
					updated * 100 >= target * 80)
				qp->cbap.firstFair80Ns = now;
			if (qp->cbap.firstFair90Ns == 0 &&
					updated * 100 >= target * 90)
				qp->cbap.firstFair90Ns = now;
			if (qp->cbap.firstFair95Ns == 0 &&
					updated * 100 >= target * 95)
				qp->cbap.firstFair95Ns = now;
		}
	}
	s_cbapGrantMessages += active.size();
	std::set<uint32_t> grantedBatches;
	for (uint32_t i = 0; i < active.size(); ++i){
		uint32_t batchId = s_cbapFlows[active[i]].batchId;
		s_cbapBatchGrantMessages[batchId]++;
		grantedBatches.insert(batchId);
	}
	EvaluateCbapHandoffBatches(now);
	ProjectCbapDelegatedEnvelope(now);
	std::set<uint32_t> messageBatches = grantedBatches;
	for (std::map<uint32_t, CbapHandoffBatchRecord>::const_iterator batch =
			s_cbapHandoffBatches.begin(); batch != s_cbapHandoffBatches.end();
			++batch)
		if (batch->second.handoffOccurred)
			messageBatches.insert(batch->first);
	for (std::set<uint32_t>::const_iterator batch = messageBatches.begin();
			batch != messageBatches.end(); ++batch){
		CbapControlMessageRecord row = {};
		row.timeNs = now;
		row.epoch = s_cbapEpoch;
		row.batchId = *batch;
		row.activeControlSummaries = s_cbapBatchActiveSummaries[*batch];
		row.monitoringOnlySummaries =
			s_cbapBatchMonitoringSummaries[*batch];
		row.grants = s_cbapBatchGrantMessages[*batch];
		s_cbapControlMessageRecords.push_back(row);
	}
}

void RdmaHw::FinishCbapFlow(Ptr<RdmaQueuePair> qp)
{
	if (!qp || !qp->cbap.enabled)
		return;
	std::map<uint32_t, CbapFlowRuntime>::iterator flow =
		s_cbapFlows.find(qp->crfm.flowId);
	if (flow != s_cbapFlows.end()){
		flow->second.active = false;
		flow->second.finished = true;
	}
	uint64_t finishNs = Simulator::Now().GetTimeStep();
	// Release any capacity-migration envelope so a completed flow never
	// leaves a stale cap behind.
	qp->cbap.migrationActive = false;
	const bool sbaFlow = qp->cbap.sbaEnabled;
	if (sbaFlow)
		s_cbapSbaController.Finish(qp->crfm.flowId, finishNs);
	std::map<uint32_t, CbapHandoffBatchRecord>::iterator handoffIt =
		s_cbapHandoffBatches.find(qp->cbap.batchId);
	if (handoffIt != s_cbapHandoffBatches.end() &&
			handoffIt->second.shadowHandoffCandidateNs > 0 &&
			finishNs > handoffIt->second.shadowHandoffCandidateNs)
		handoffIt->second.shadowControlledAfterCandidateNs = std::max(
			handoffIt->second.shadowControlledAfterCandidateNs,
			finishNs - handoffIt->second.shadowHandoffCandidateNs);
	if (handoffIt != s_cbapHandoffBatches.end() &&
			handoffIt->second.handoffOccurred){
		handoffIt->second.grantsAfterHandoff =
			s_cbapBatchGrantMessages[qp->cbap.batchId] -
			handoffIt->second.grantsBeforeHandoff;
		handoffIt->second.controlBytesAfterHandoff =
			handoffIt->second.grantsAfterHandoff *
				s_cbapConfig.grantBytes;
	}
	bool batchStillActive = false;
	for (std::map<uint32_t, CbapFlowRuntime>::const_iterator peer =
			s_cbapFlows.begin(); peer != s_cbapFlows.end(); ++peer)
		if (peer->second.batchId == qp->cbap.batchId &&
				peer->second.active && !peer->second.finished){
			batchStillActive = true;
			break;
		}
	if (!batchStillActive && handoffIt != s_cbapHandoffBatches.end() &&
			!handoffIt->second.handoffOccurred &&
			handoffIt->second.shadowHandoffCandidateNs == 0)
		handoffIt->second.noHandoffReason = "completed_before_handoff";
	UpdateCbapTrackingRateIntegral(qp, finishNs);
	qp->cbap.creditGateActive = false;
	if (qp->cbap.creditGateEnterNs > 0 &&
			qp->cbap.creditGateExitNs == 0)
		qp->cbap.creditGateExitNs = finishNs;
	qp->cbap.phase = RdmaQueuePair::CBAP_FINISHED;
	CbapFlowRecord record = {};
	record.flowId = qp->crfm.flowId;
	record.batchId = qp->cbap.batchId;
	record.applicationReadyNs = qp->cbap.applicationReadyNs;
	record.networkReleaseNs = qp->cbap.networkReleaseNs;
	record.firstFreshFeedbackNs = qp->cbap.firstFreshFeedbackNs;
	record.admissionEnterNs = qp->cbap.admissionEnterNs;
	record.admissionExitNs = qp->cbap.admissionExitNs;
	record.firstDataTxNs = qp->cbap.firstDataTxNs;
	record.firstPostReleaseSampleNs =
		qp->cbap.firstPostReleaseSampleNs;
	record.firstCompleteFreshFeedbackNs =
		qp->cbap.firstCompleteFreshFeedbackNs;
	record.initialAdmitRateBps = qp->cbap.initialAdmitRateBps;
	uint64_t admissionSpan = qp->cbap.admissionExitNs >
		qp->cbap.admissionEnterNs ? qp->cbap.admissionExitNs -
		qp->cbap.admissionEnterNs : 0;
	record.actualAdmissionMeanRateBps = admissionSpan > 0 ?
		(double)qp->cbap.bytesSentBeforeFreshFeedback * 8e9 /
		admissionSpan : 0;
	record.bytesSentBeforeFreshFeedback =
		qp->cbap.bytesSentBeforeFreshFeedback;
	record.rateUpdatesBeforeFirstTx =
		qp->cbap.rateUpdatesBeforeFirstTx;
	record.ordinaryRateUpdatesDuringAdmission =
		qp->cbap.ordinaryRateUpdatesDuringAdmission;
	record.emergencyRateUpdatesDuringAdmission =
		qp->cbap.emergencyRateUpdatesDuringAdmission;
	record.creditGateEnterNs = qp->cbap.creditGateEnterNs;
	record.creditGateExitNs = qp->cbap.creditGateExitNs;
	record.creditGateActiveAtFinish = qp->cbap.creditGateActive;
	record.creditRemainingAtAdmissionExit =
		qp->cbap.creditRemainingAtAdmissionExit;
	uint64_t trackingSpan = qp->cbap.trackingStartNs > 0 &&
		finishNs > qp->cbap.trackingStartNs ?
		finishNs - qp->cbap.trackingStartNs : 0;
	record.trackingActualRateBps = trackingSpan > 0 ?
		(double)qp->cbap.trackingBytesSent * 8e9 / trackingSpan : 0;
	record.trackingCurrentRateBps = trackingSpan > 0 ?
		(double)(qp->cbap.trackingRateIntegral / trackingSpan) : 0;
	record.trackingBaseRateBps = qp->cbap.baseRateBps;
	record.pacingViolations = qp->cbap.pacingViolationCount;
	record.estimatedFirstFeedbackNs =
		qp->cbap.estimatedFirstFeedbackNs;
	record.finishNs = finishNs;
	record.bytesSent = qp->snd_nxt;
	record.bytesAcked = qp->snd_una;
	record.baseRateBps = qp->cbap.baseRateBps;
	record.admitRateBps = qp->cbap.admitRateBps;
	record.finalRateBps = qp->m_rate.GetBitRate();
	record.initialCreditBytes = qp->cbap.creditInitialBytes;
	record.remainingCreditBytes = qp->cbap.creditRemainingBytes;
	record.excessBytes = qp->cbap.excessBytes;
	record.capacityViolations = qp->cbap.capacityViolationCount;
	record.creditViolations = qp->cbap.creditViolationCount;
	record.staleFeedback = qp->cbap.staleFeedbackCount;
	record.rateIncreases = qp->cbap.rateIncreaseCount;
	record.rateDecreases = qp->cbap.rateDecreaseCount;
	record.rateHolds = qp->cbap.rateHoldCount;
	record.reschedules = qp->cbap.rescheduleCount;
	record.fair80Ns = qp->cbap.firstFair80Ns;
	record.fair90Ns = qp->cbap.firstFair90Ns;
	record.fair95Ns = qp->cbap.firstFair95Ns;
	s_cbapFlowRecords.push_back(record);
	if (sbaFlow)
		EvaluateCbapSbaReadmission(finishNs,
			"flow_completed_capacity_release");
}

TypeId RdmaHw::GetTypeId (void)
{
	static TypeId tid = TypeId ("ns3::RdmaHw")
		.SetParent<Object> ()
		.AddAttribute("MinRate",
				"Minimum rate of a throttled flow",
				DataRateValue(DataRate("100Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_minRate),
				MakeDataRateChecker())
		.AddAttribute("Mtu",
				"Mtu.",
				UintegerValue(1000),
				MakeUintegerAccessor(&RdmaHw::m_mtu),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute ("CcMode",
				"which mode of DCQCN is running",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_cc_mode),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("NACK Generation Interval",
				"The NACK Generation interval",
				DoubleValue(500.0),
				MakeDoubleAccessor(&RdmaHw::m_nack_interval),
				MakeDoubleChecker<double>())
		.AddAttribute("L2ChunkSize",
				"Layer 2 chunk size. Disable chunk mode if equals to 0.",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_chunk),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("L2AckInterval",
				"Layer 2 Ack intervals. Disable ack if equals to 0.",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_ack_interval),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("L2BackToZero",
				"Layer 2 go back to zero transmission.",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_backto0),
				MakeBooleanChecker())
		.AddAttribute("EwmaGain",
				"Control gain parameter which determines the level of rate decrease",
				DoubleValue(1.0 / 16),
				MakeDoubleAccessor(&RdmaHw::m_g),
				MakeDoubleChecker<double>())
		.AddAttribute ("RateOnFirstCnp",
				"the fraction of rate on first CNP",
				DoubleValue(1.0),
				MakeDoubleAccessor(&RdmaHw::m_rateOnFirstCNP),
				MakeDoubleChecker<double> ())
		.AddAttribute("ClampTargetRate",
				"Clamp target rate.",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_EcnClampTgtRate),
				MakeBooleanChecker())
		.AddAttribute("RPTimer",
				"The rate increase timer at RP in microseconds",
				DoubleValue(1500.0),
				MakeDoubleAccessor(&RdmaHw::m_rpgTimeReset),
				MakeDoubleChecker<double>())
		.AddAttribute("RateDecreaseInterval",
				"The interval of rate decrease check",
				DoubleValue(4.0),
				MakeDoubleAccessor(&RdmaHw::m_rateDecreaseInterval),
				MakeDoubleChecker<double>())
		.AddAttribute("FastRecoveryTimes",
				"The rate increase timer at RP",
				UintegerValue(5),
				MakeUintegerAccessor(&RdmaHw::m_rpgThreshold),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("AlphaResumInterval",
				"The interval of resuming alpha",
				DoubleValue(55.0),
				MakeDoubleAccessor(&RdmaHw::m_alpha_resume_interval),
				MakeDoubleChecker<double>())
		.AddAttribute("RateAI",
				"Rate increment unit in AI period",
				DataRateValue(DataRate("5Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_rai),
				MakeDataRateChecker())
		.AddAttribute("RateHAI",
				"Rate increment unit in hyperactive AI period",
				DataRateValue(DataRate("50Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_rhai),
				MakeDataRateChecker())
		.AddAttribute("VarWin",
				"Use variable window size or not",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_var_win),
				MakeBooleanChecker())
		.AddAttribute("FastReact",
				"Fast React to congestion feedback",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_fast_react),
				MakeBooleanChecker())
		.AddAttribute("MiThresh",
				"Threshold of number of consecutive AI before MI",
				UintegerValue(5),
				MakeUintegerAccessor(&RdmaHw::m_miThresh),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("TargetUtil",
				"The Target Utilization of the bottleneck bandwidth, by default 95%",
				DoubleValue(0.95),
				MakeDoubleAccessor(&RdmaHw::m_targetUtil),
				MakeDoubleChecker<double>())
		.AddAttribute("UtilHigh",
				"The upper bound of Target Utilization of the bottleneck bandwidth, by default 98%",
				DoubleValue(0.98),
				MakeDoubleAccessor(&RdmaHw::m_utilHigh),
				MakeDoubleChecker<double>())
		.AddAttribute("RateBound",
				"Bound packet sending by rate, for test only",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_rateBound),
				MakeBooleanChecker())
		.AddAttribute("AppCapTrace",
				"Trace controller rate, app cap and effective pacing "
				"rate for flows that have an application rate cap",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_appCapTrace),
				MakeBooleanChecker())
		.AddAttribute("MultiRate",
				"Maintain multiple rates in HPCC",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_multipleRate),
				MakeBooleanChecker())
		.AddAttribute("SampleFeedback",
				"Whether sample feedback or not",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_sampleFeedback),
				MakeBooleanChecker())
		.AddAttribute("TimelyAlpha",
				"Alpha of TIMELY",
				DoubleValue(0.875),
				MakeDoubleAccessor(&RdmaHw::m_tmly_alpha),
				MakeDoubleChecker<double>())
		.AddAttribute("TimelyBeta",
				"Beta of TIMELY",
				DoubleValue(0.8),
				MakeDoubleAccessor(&RdmaHw::m_tmly_beta),
				MakeDoubleChecker<double>())
		.AddAttribute("TimelyTLow",
				"TLow of TIMELY (ns)",
				UintegerValue(50000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_TLow),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("TimelyTHigh",
				"THigh of TIMELY (ns)",
				UintegerValue(500000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_THigh),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("TimelyMinRtt",
				"MinRtt of TIMELY (ns)",
				UintegerValue(20000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_minRtt),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("RoundMode",
				"Enable release-gated rounds on a persistent QP",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_roundMode),
				MakeBooleanChecker())
		.AddAttribute("BopRho",
				"BOP usable bottleneck capacity fraction",
				DoubleValue(1.0),
				MakeDoubleAccessor(&RdmaHw::m_bopRho),
				MakeDoubleChecker<double>())
		.AddAttribute("BopBackgroundBps",
				"BOP configured bottleneck background load",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_bopBackgroundBps),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("BopPhaseStagger",
				"Stagger only the first packet of each BOP round",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_bopPhaseStagger),
				MakeBooleanChecker())
		.AddAttribute("BopPacketBytes",
				"Packet bytes used to calculate BOP phase spacing",
				UintegerValue(1024),
				MakeUintegerAccessor(&RdmaHw::m_bopPacketBytes),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("BopBottleneckBps",
				"Explicit single shared bottleneck capacity for BOP-v1",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_bopBottleneckBps),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("BopMultilinkEnable",
				"Use explicit fixed-path per-link BOP planning",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_bopMultilinkEnable),
				MakeBooleanChecker())
		.AddAttribute("BopQcBdpFactor",
				"BOP-QC group BDP credit multiplier",
				DoubleValue(1.0),
				MakeDoubleAccessor(&RdmaHw::m_bopQcBdpFactor),
				MakeDoubleChecker<double>())
		.AddAttribute("BopQcDefaultTauUs",
				"BOP-QC feedback delay before an EWMA sample exists",
				DoubleValue(10.0),
				MakeDoubleAccessor(&RdmaHw::m_bopQcDefaultTauUs),
				MakeDoubleChecker<double>())
		.AddAttribute("BopQcTauEwmaAlpha",
				"BOP-QC feedback-delay EWMA alpha",
				DoubleValue(0.20),
				MakeDoubleAccessor(&RdmaHw::m_bopQcTauEwmaAlpha),
				MakeDoubleChecker<double>())
		.AddAttribute("BopQcQueueLimitMode",
				"BOP-QC queue limit mode; one selects the ECN threshold",
				UintegerValue(1),
				MakeUintegerAccessor(&RdmaHw::m_bopQcQueueLimitMode),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("BopQcPacketMargin",
				"BOP-QC packets of safety margin per participant",
				UintegerValue(1),
				MakeUintegerAccessor(&RdmaHw::m_bopQcPacketMargin),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("BopQcEnablePhaseStagger",
				"Apply the original BOP first-packet phase stagger to BOP-QC",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_bopQcEnablePhaseStagger),
				MakeBooleanChecker())
			.AddAttribute("BopQcEcnThresholdBytes",
					"Actual shared-bottleneck ECN kmin in bytes",
					UintegerValue(0),
					MakeUintegerAccessor(&RdmaHw::m_bopQcEcnThresholdBytes),
					MakeUintegerChecker<uint64_t>())
			.AddAttribute("BopQbQueueFraction",
					"BOP-QB target queue as a fraction of ECN kmin",
					DoubleValue(0.50),
					MakeDoubleAccessor(&RdmaHw::m_bopQbQueueFraction),
					MakeDoubleChecker<double>())
			.AddAttribute("BopQbPacketMargin",
					"BOP-QB packets of safety margin per participant",
					UintegerValue(1),
					MakeUintegerAccessor(&RdmaHw::m_bopQbPacketMargin),
					MakeUintegerChecker<uint32_t>())
			.AddAttribute("BopQbEnablePhaseStagger",
					"Apply the original BOP first-packet phase stagger to BOP-QB",
					BooleanValue(true),
					MakeBooleanAccessor(&RdmaHw::m_bopQbEnablePhaseStagger),
					MakeBooleanChecker())
			.AddAttribute("BopQbEcnThresholdBytes",
					"Actual shared-bottleneck ECN kmin in bytes for BOP-QB",
					UintegerValue(0),
					MakeUintegerAccessor(&RdmaHw::m_bopQbEcnThresholdBytes),
					MakeUintegerChecker<uint64_t>())
			.AddAttribute("BopQbMaxPacketMargin",
					"BOP-QB-Max packets of ECN safety margin per participant",
					UintegerValue(1),
					MakeUintegerAccessor(&RdmaHw::m_bopQbMaxPacketMargin),
					MakeUintegerChecker<uint32_t>())
			.AddAttribute("BopQbMaxEnablePhaseStagger",
					"Apply the original BOP first-packet phase stagger to BOP-QB-Max",
					BooleanValue(true),
					MakeBooleanAccessor(&RdmaHw::m_bopQbMaxEnablePhaseStagger),
					MakeBooleanChecker())
			.AddAttribute("BopQbMaxEcnThresholdBytes",
					"Actual shared-bottleneck ECN kmin in bytes for BOP-QB-Max",
					UintegerValue(0),
					MakeUintegerAccessor(&RdmaHw::m_bopQbMaxEcnThresholdBytes),
					MakeUintegerChecker<uint64_t>())
			.AddAttribute("FinalPrimerFirstFlow",
					"First diagnostic primer flow id; UINT32_MAX disables it",
					UintegerValue(std::numeric_limits<uint32_t>::max()),
					MakeUintegerAccessor(&RdmaHw::m_finalPrimerFirstFlow),
					MakeUintegerChecker<uint32_t>())
		.AddAttribute("DctcpRateAI",
				"DCTCP's Rate increment unit in AI period",
				DataRateValue(DataRate("1000Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_dctcp_rai),
				MakeDataRateChecker())
		.AddAttribute("PintSmplThresh",
				"PINT's sampling threshold in rand()%65536",
				UintegerValue(65536),
				MakeUintegerAccessor(&RdmaHw::pint_smpl_thresh),
				MakeUintegerChecker<uint32_t>())
		;
	return tid;
}

RdmaHw::RdmaHw(){
}

void RdmaHw::SetNode(Ptr<Node> node){
	m_node = node;
}
void RdmaHw::Setup(QpCompleteCallback cb){
	for (uint32_t i = 0; i < m_nic.size(); i++){
		Ptr<QbbNetDevice> dev = m_nic[i].dev;
		if (dev == NULL)
			continue;
		// share data with NIC
		dev->m_rdmaEQ->m_qpGrp = m_nic[i].qpGrp;
		// setup callback
		dev->m_rdmaReceiveCb = MakeCallback(&RdmaHw::Receive, this);
		dev->m_rdmaLinkDownCb = MakeCallback(&RdmaHw::SetLinkDown, this);
		dev->m_rdmaPktSent = MakeCallback(&RdmaHw::PktSent, this);
		// config NIC
		dev->m_rdmaEQ->m_rdmaGetNxtPkt = MakeCallback(&RdmaHw::GetNxtPacket, this);
	}
	// setup qp complete callback
	m_qpCompleteCallback = cb;
}

uint32_t RdmaHw::GetNicIdxOfQp(Ptr<RdmaQueuePair> qp){
	auto &v = m_rtTable[qp->dip.Get()];
	if (v.size() > 0){
		return v[qp->GetHash() % v.size()];
	}else{
		NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
	}
}
uint64_t RdmaHw::GetQpKey(uint32_t dip, uint16_t sport, uint16_t pg){
	return ((uint64_t)dip << 32) | ((uint64_t)sport << 16) | (uint64_t)pg;
}	//这个不是verbs里的rkey，lkey这些东西，而是一个QP的哈希/索引key
Ptr<RdmaQueuePair> RdmaHw::GetQp(uint32_t dip, uint16_t sport, uint16_t pg){
	uint64_t key = GetQpKey(dip, sport, pg);
	auto it = m_qpMap.find(key);
	if (it != m_qpMap.end())
		return it->second;
	return NULL;
}
void RdmaHw::AddQueuePair(uint64_t size, uint16_t pg, Ipv4Address sip, Ipv4Address dip, uint16_t sport, uint16_t dport, uint32_t win, uint64_t baseRtt, Callback<void> notifyAppFinish){
	// create qp
	Ptr<RdmaQueuePair> qp = CreateObject<RdmaQueuePair>(pg, sip, dip, sport, dport);
	qp->SetSize(size);
	qp->SetWin(win);
	qp->SetBaseRtt(baseRtt);
	qp->SetVarWin(m_var_win);
	qp->SetAppNotifyCallback(notifyAppFinish);

	// add qp
	uint32_t nic_idx = GetNicIdxOfQp(qp);
	m_nic[nic_idx].qpGrp->AddQp(qp);
	uint64_t key = GetQpKey(dip.Get(), sport, pg);
	m_qpMap[key] = qp;

	// set init variables
	DataRate m_bps = m_nic[nic_idx].dev->GetDataRate();
	qp->m_rate = m_bps;
	qp->m_max_rate = m_bps;
	if (IsDcqcnMode(m_cc_mode)){
		qp->mlx.m_targetRate = m_bps;
		}else if (UsesHpccTelemetryMode(m_cc_mode)){
		qp->hp.m_curRate = m_bps;
		if (m_multipleRate){
			for (uint32_t i = 0; i < IntHeader::maxHop; i++)
				qp->hp.hopState[i].Rc = m_bps;
		}
	}else if (m_cc_mode == 7){
		qp->tmly.m_curRate = m_bps;
	}else if (m_cc_mode == 10){
		qp->hpccPint.m_curRate = m_bps;
	}

	if (m_roundMode){
		auto pending = m_pendingRoundSchedules.find(key);
		NS_ASSERT_MSG(pending != m_pendingRoundSchedules.end(),
				"ROUND_MODE QP has no registered round schedule");
		qp->crfm.enabled = true;
		qp->crfm.flowId = pending->second.flowId;
		qp->crfm.rounds = pending->second.rounds;
		qp->crfm.releasedBytes = 0;
		qp->crfm.minimumRate = m_bps.GetBitRate();
		qp->crfm.maximumRate = m_bps.GetBitRate();
		uint64_t sequence = 0;
		for (uint32_t i = 0; i < qp->crfm.rounds.size(); ++i){
			RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[i];
			round.startSeq = sequence;
			sequence += round.roundBytes;
			round.endSeq = sequence;
		}
		NS_ASSERT_MSG(sequence == size,
				"round byte total differs from QP total size");
		m_pendingRoundSchedules.erase(pending);
		RegisterRoundGroups(qp);
	}
//RdmaEgressQueue
	// Notify Nic
	m_nic[nic_idx].dev->NewQp(qp);//这个只是通知这个QP所属的网卡来了一个新的QP，然后就可以开始尝试发包了
	// The group coordinator releases round zero only after every participant
	// QP has registered. Later rounds are released from the global ACK barrier.
}

void RdmaHw::RegisterRoundSchedule(uint32_t dip, uint16_t sport, uint16_t pg,
		uint32_t flowId,
		const std::vector<RdmaQueuePair::CrfmRoundState> &rounds){
	NS_ASSERT_MSG(m_roundMode, "round schedule registered while ROUND_MODE=0");
	NS_ASSERT_MSG(!rounds.empty(), "round schedule must not be empty");
	uint64_t key = GetQpKey(dip, sport, pg);
	NS_ASSERT_MSG(m_pendingRoundSchedules.find(key) ==
			m_pendingRoundSchedules.end(), "duplicate round schedule key");
	CrfmPendingSchedule schedule;
	schedule.flowId = flowId;
	schedule.rounds = rounds;
	m_pendingRoundSchedules[key] = schedule;
}

void RdmaHw::SetCrfmRate(Ptr<RdmaQueuePair> qp, uint64_t rate){
	if (rate == 0)
		rate = 1;
	uint64_t before = qp->m_rate.GetBitRate();
	if (before == rate)
		return;
	if (qp->lastPktSize == 0)
		qp->m_rate = DataRate(rate);
	else
		ChangeRate(qp, DataRate(rate));
	qp->crfm.rateTotalVariation += std::fabs((double)rate - before);
	qp->crfm.minimumRate = std::min(qp->crfm.minimumRate, rate);
	qp->crfm.maximumRate = std::max(qp->crfm.maximumRate, rate);
}

void RdmaHw::SetRoundStartRate(Ptr<RdmaQueuePair> qp, uint64_t rate){
	SetCrfmRate(qp, rate);
	qp->hp.m_curRate = DataRate(rate);
	if (m_multipleRate)
		for (uint32_t i = 0; i < IntHeader::maxHop; ++i)
			qp->hp.hopState[i].Rc = DataRate(rate);
}

void RdmaHw::RegisterRoundGroups(Ptr<RdmaQueuePair> qp){
	for (uint32_t i = 0; i < qp->crfm.rounds.size(); ++i){
		RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[i];
		RoundGroupRuntime &group = s_roundGroups[round.roundGroupId];
		if (group.members.empty()){
			group.participantCount = round.participantCount;
			group.roundIndex = i;
		}
		NS_ASSERT_MSG(group.participantCount == round.participantCount &&
				group.roundIndex == i, "round group metadata mismatch");
			RoundGroupMember member = {this, qp, i};
			group.members.push_back(member);
			bool complete = group.members.size() == group.participantCount;
			bool multilinkRoot = false;
			if (m_bopMultilinkEnable && s_bopMultilinkConfigured) {
				std::map<uint32_t, int64_t>::const_iterator predecessor =
					s_bopMultilinkGroupPredecessors.find(
						round.roundGroupId);
				NS_ASSERT_MSG(predecessor !=
						s_bopMultilinkGroupPredecessors.end(),
						"round group has no multilink dependency entry");
				multilinkRoot = predecessor->second < 0;
			}
			if (complete && ((!m_bopMultilinkEnable && i == 0) ||
					(m_bopMultilinkEnable && multilinkRoot))){
				NS_ASSERT_MSG(round.commonReleaseHintNs > Simulator::Now().GetTimeStep(),
						"first common release must be after QP registration");
				ScheduleRoundGroup(round.roundGroupId,
						round.commonReleaseHintNs);
		}
	}
}

void RdmaHw::ScheduleRoundGroup(uint32_t groupId,
		uint64_t commonReleaseNs){
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.members.size() == group.participantCount,
			"cannot schedule an incomplete round group");
	NS_ASSERT_MSG(!group.planScheduled && !group.planned,
			"round group planned more than once");
	int64_t minimumJitter = 0;
	for (uint32_t i = 0; i < group.members.size(); ++i)
		minimumJitter = std::min(minimumJitter,
			group.members[i].qp->crfm.rounds[
				group.members[i].roundIndex].jitterNs);
	RdmaHw *owner = group.members.front().hw;
	bool cbap = IsCbapMode(owner->m_cc_mode);
	group.applicationReadyNs = commonReleaseNs;
	uint64_t networkReleaseNs = cbap ?
		commonReleaseNs + s_cbapConfig.planningDelayNs :
		commonReleaseNs;
	int64_t earliest = (int64_t)networkReleaseNs + minimumJitter;
	NS_ASSERT_MSG(earliest >= (int64_t)Simulator::Now().GetTimeStep(),
			"group plan would require a past release");
	group.commonReleaseNs = networkReleaseNs;
	group.earliestReleaseNs = earliest;
	group.planScheduled = true;
	bool primerGroup = owner->m_finalPrimerFirstFlow !=
		std::numeric_limits<uint32_t>::max();
	for (uint32_t i = 0; primerGroup && i < group.members.size(); ++i)
		primerGroup = group.members[i].qp->crfm.flowId >=
			owner->m_finalPrimerFirstFlow;
	if (owner->m_cc_mode == CC_MODE_BOP_QB_PRT && !primerGroup){
		uint64_t now = Simulator::Now().GetTimeStep();
		uint64_t rttHat = 0;
		for (uint32_t i = 0; i < group.members.size(); ++i){
			Ptr<RdmaQueuePair> qp = group.members[i].qp;
			uint64_t candidate = qp->crfm.bopQcTauValid ?
				(uint64_t)std::ceil(qp->crfm.bopQcTauEwmaNs) :
				qp->m_baseRtt;
			rttHat = std::max(rttHat, candidate);
		}
		group.prtRttHatNs = std::max((uint64_t)1, rttHat);
		if (now < (uint64_t)earliest){
			Simulator::ScheduleNow(&RdmaHw::SendPrtProbe, groupId, 0);
			if ((uint64_t)earliest > now + group.prtRttHatNs){
				uint64_t second = (uint64_t)earliest -
					group.prtRttHatNs;
				Simulator::Schedule(NanoSeconds(second - now),
					&RdmaHw::SendPrtProbe, groupId, 1);
			}
		}
	}
	if (cbap){
		NS_ASSERT_MSG(s_cbapConfig.enabled,
			"CBAP mode has no coordinator configuration");
		if (IsCbapSbaMode(owner->m_cc_mode))
			Simulator::Schedule(NanoSeconds(commonReleaseNs -
				Simulator::Now().GetTimeStep()),
				&RdmaHw::PlanCbapSbaBatch, groupId);
		else if (IsCbapV20Mode(owner->m_cc_mode))
			Simulator::Schedule(NanoSeconds(commonReleaseNs -
				Simulator::Now().GetTimeStep()),
				&RdmaHw::PlanCbapV20Batch, groupId);
		else if (owner->m_cc_mode == CC_MODE_CBAP_FULL_SCOPED ||
				owner->m_cc_mode ==
					CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
				owner->m_cc_mode ==
					CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
				owner->m_cc_mode ==
					CC_MODE_CBAP_FULL_GUARDED_DELEGATION)
			Simulator::Schedule(NanoSeconds(commonReleaseNs -
				Simulator::Now().GetTimeStep()),
				&RdmaHw::PlanScopedCbapBatch, groupId);
		else 
			Simulator::Schedule(NanoSeconds(commonReleaseNs -
				Simulator::Now().GetTimeStep()),
				&RdmaHw::PlanCbapBatch, groupId);
	}else{
		Simulator::Schedule(NanoSeconds(
			(uint64_t)earliest - Simulator::Now().GetTimeStep()),
			&RdmaHw::PlanRoundGroup, groupId);
	}
}

void RdmaHw::SendPrtProbe(uint32_t groupId, uint8_t probeId)
{
	RoundGroupRuntime &group = s_roundGroups[groupId];
	if (probeId >= 2 || group.planned ||
			Simulator::Now().GetTimeStep() >= group.earliestReleaseNs)
		return;
	RoundGroupMember &member = group.members.front();
	RdmaHw *hw = member.hw;
	if (hw->m_cc_mode != CC_MODE_BOP_QB_PRT)
		return;
	Ptr<RdmaQueuePair> qp = member.qp;
	Ptr<Packet> packet = Create<Packet>(0);
	SeqTsHeader seq;
	seq.SetSeq(qp->snd_nxt);
	seq.SetPG(qp->m_pg);
	packet->AddHeader(seq);
	UdpHeader udp;
	udp.SetDestinationPort(qp->dport);
	udp.SetSourcePort(qp->sport);
	packet->AddHeader(udp);
	Ipv4Header ip;
	ip.SetSource(qp->sip);
	ip.SetDestination(qp->dip);
	ip.SetProtocol(0x11);
	ip.SetPayloadSize(packet->GetSize());
	ip.SetTtl(64);
	ip.SetIdentification(qp->m_ipid++);
	packet->AddHeader(ip);
	hw->AddHeader(packet, 0x800);
	packet->AddPacketTag(PrtProbeTag(groupId, probeId));
	group.prtProbe[probeId].sendNs = Simulator::Now().GetTimeStep();
	group.prtProbeCountSent =
		std::max(group.prtProbeCountSent, (uint32_t)probeId + 1);
	uint32_t nic = hw->GetNicIdxOfQp(qp);
	hw->m_nic[nic].dev->RdmaEnqueueHighPrioQ(packet);
	hw->m_nic[nic].dev->TriggerTransmit();
}

bool RdmaHw::ReadPrtQueueSample(IntHeader &ih,
		uint64_t &queueBytes, uint64_t &sampleTimeNs,
		uint64_t &capacityBps)
{
	if (ih.nhop == 0 || ih.nhop > IntHeader::maxHop)
		return false;
	uint32_t selected = 0;
	for (uint32_t i = 1; i < ih.nhop; ++i)
		if (ih.hop[i].GetQlen() > ih.hop[selected].GetQlen())
			selected = i;
	if (ih.hop[selected].GetLineRate() == 0)
		return false;
	uint64_t now = Simulator::Now().GetTimeStep();
	uint64_t modulus = (uint64_t)1 << IntHop::timeWidth;
	uint64_t sample = (now / modulus) * modulus +
		ih.hop[selected].GetTime();
	if (sample > now)
		sample -= modulus;
	queueBytes = ih.hop[selected].GetQlen();
	sampleTimeNs = sample;
	capacityBps = ih.hop[selected].GetLineRate();
	return true;
}

void RdmaHw::RecordPrtProbeAck(uint32_t groupId, uint8_t probeId,
		IntHeader &ih)
{
	std::map<uint32_t, RoundGroupRuntime>::iterator found =
		s_roundGroups.find(groupId);
	if (found == s_roundGroups.end() || probeId >= 2)
		return;
	RoundGroupRuntime &group = found->second;
	uint64_t now = Simulator::Now().GetTimeStep();
	if (now >= group.earliestReleaseNs)
		return;
	uint64_t queue = 0, sample = 0, capacity = 0;
	if (!ReadPrtQueueSample(ih, queue, sample, capacity))
		return;
	RoundGroupRuntime::PrtProbeSample &record =
		group.prtProbe[probeId];
	record.returned = true;
	record.ackNs = now;
	record.queueSampleNs = sample;
	record.queueBytes = queue;
	record.capacityBps = capacity;
}

void RdmaHw::PlanRoundGroup(uint32_t groupId){
	RoundGroupRuntime &group = s_roundGroups[groupId];
	NS_ASSERT_MSG(group.planScheduled && !group.planned,
			"group plan callback executed more than once");
	NS_ASSERT_MSG(Simulator::Now().GetTimeStep() == group.earliestReleaseNs,
			"group plan did not run at earliest release");
	RdmaHw *owner = group.members.front().hw;
	bool isBop = owner->m_cc_mode == CC_MODE_BOP;
	bool isBopQc = owner->m_cc_mode == CC_MODE_BOP_QC;
	bool isBopQbOracle =
		owner->m_cc_mode == CC_MODE_BOP_QB_ORACLE_Q0;
	bool isBopPrt = owner->m_cc_mode == CC_MODE_BOP_QB_PRT;
	bool isBopQb = UsesBopQbCredit(owner->m_cc_mode);
	bool isBopQbMax = owner->m_cc_mode == CC_MODE_BOP_QB_MAX;
	bool isBopFamily = isBop || isBopQc || isBopQb || isBopQbMax;
	bool isPrimerGroup = owner->m_finalPrimerFirstFlow !=
		std::numeric_limits<uint32_t>::max();
	for (uint32_t i = 0; isPrimerGroup && i < group.members.size(); ++i)
		isPrimerGroup = group.members[i].qp->crfm.flowId >=
			owner->m_finalPrimerFirstFlow;
	if (isPrimerGroup){
		isBop = isBopQc = isBopQb = isBopQbMax = false;
		isBopQbOracle = false;
		isBopPrt = false;
		isBopFamily = false;
	}
	uint64_t capacity = owner->m_bopBottleneckBps;
	uint64_t background = owner->m_bopBackgroundBps;
	uint64_t queue = 0, newestArrival = 0, queueSampleTime = 0;
	bool telemetry = false;
	bool tauValid = false;
	double tauEwmaNs = 0;
	double maximumLine = 0;
	uint64_t totalBytes = 0;
	for (uint32_t i = 0; i < group.members.size(); ++i){
		RdmaHw *hw = group.members[i].hw;
		Ptr<RdmaQueuePair> qp = group.members[i].qp;
		RdmaQueuePair::CrfmRoundState &round =
			qp->crfm.rounds[group.members[i].roundIndex];
		NS_ASSERT_MSG(hw->m_cc_mode == owner->m_cc_mode,
				"mixed algorithms in one round group");
		NS_ASSERT_MSG(!isBopFamily ||
			(hw->m_bopRho == owner->m_bopRho &&
			 hw->m_bopBackgroundBps == background &&
			 hw->m_bopBottleneckBps == capacity),
			"inconsistent BOP configuration in group");
		NS_ASSERT_MSG(!isBopQc ||
			(hw->m_bopQcBdpFactor == owner->m_bopQcBdpFactor &&
			 hw->m_bopQcDefaultTauUs == owner->m_bopQcDefaultTauUs &&
			 hw->m_bopQcTauEwmaAlpha == owner->m_bopQcTauEwmaAlpha &&
			 hw->m_bopQcQueueLimitMode == owner->m_bopQcQueueLimitMode &&
			 hw->m_bopQcPacketMargin == owner->m_bopQcPacketMargin &&
			 hw->m_bopQcEnablePhaseStagger ==
				owner->m_bopQcEnablePhaseStagger &&
			 hw->m_bopQcEcnThresholdBytes ==
				owner->m_bopQcEcnThresholdBytes),
			"inconsistent BOP-QC configuration in group");
		NS_ASSERT_MSG(!isBopQb ||
			(hw->m_bopQbQueueFraction ==
				owner->m_bopQbQueueFraction &&
			 hw->m_bopQbPacketMargin ==
				owner->m_bopQbPacketMargin &&
			 hw->m_bopQbEnablePhaseStagger ==
				owner->m_bopQbEnablePhaseStagger &&
			 hw->m_bopQbEcnThresholdBytes ==
				owner->m_bopQbEcnThresholdBytes),
			"inconsistent BOP-QB configuration in group");
		NS_ASSERT_MSG(!isBopQbMax ||
			(hw->m_bopQbMaxPacketMargin ==
				owner->m_bopQbMaxPacketMargin &&
			 hw->m_bopQbMaxEnablePhaseStagger ==
				owner->m_bopQbMaxEnablePhaseStagger &&
			 hw->m_bopQbMaxEcnThresholdBytes ==
				owner->m_bopQbMaxEcnThresholdBytes),
			"inconsistent BOP-QB-Max configuration in group");
		totalBytes += round.roundBytes;
		maximumLine = std::max(maximumLine,
			round.roundBytes * 8.0 / qp->m_max_rate.GetBitRate());
		bool arrivedBeforePlan = (isBopQc || isBopQb || isBopQbMax) ?
			qp->crfm.bopLastArrivalTimeNs < group.earliestReleaseNs :
			qp->crfm.bopLastArrivalTimeNs <=
				Simulator::Now().GetTimeStep();
		if (qp->crfm.bopTelemetryValid &&
				arrivedBeforePlan &&
				qp->crfm.bopLastArrivalTimeNs >= newestArrival){
			newestArrival = qp->crfm.bopLastArrivalTimeNs;
			queue = qp->crfm.bopLastQueueBytes;
			queueSampleTime = qp->crfm.bopLastSampleTimeNs;
			if (qp->crfm.bopLastBottleneckBps)
				capacity = qp->crfm.bopLastBottleneckBps;
			telemetry = true;
			tauValid = qp->crfm.bopQcTauValid;
			tauEwmaNs = qp->crfm.bopQcTauEwmaNs;
		}
	}
	if (group.roundIndex == 0){
		queue = 0;
		telemetry = false;
		queueSampleTime = 0;
		tauValid = false;
	}
	uint64_t estimatedQueue = queue;
	uint64_t actualQueue = 0;
	bool actualQueueValid = !s_roundQueueRead.IsNull();
	if (actualQueueValid)
		actualQueue = s_roundQueueRead();
	if (isBopQbOracle){
		queue = actualQueue;
		estimatedQueue = actualQueue;
		telemetry = actualQueueValid;
		queueSampleTime = Simulator::Now().GetTimeStep();
	}
	uint64_t originalBopQueue = queue;
	uint64_t prtQueue = queue;
	double prtSlope = 0;
	uint32_t prtReturned = 0;
	uint32_t prtFallback = 0;
	if (isBopPrt){
		std::vector<RoundGroupRuntime::PrtProbeSample> samples;
		for (uint32_t i = 0; i < 2; ++i)
			if (group.prtProbe[i].returned &&
					group.prtProbe[i].ackNs < group.earliestReleaseNs)
				samples.push_back(group.prtProbe[i]);
		prtReturned = samples.size();
		if (samples.size() >= 2){
			if (samples[1].queueSampleNs > samples[0].queueSampleNs)
				prtSlope = std::max(0.0,
					(double)((int64_t)samples[1].queueBytes -
						(int64_t)samples[0].queueBytes) /
					(samples[1].queueSampleNs -
						samples[0].queueSampleNs));
			long double extrapolated = samples[1].queueBytes +
				prtSlope * (group.earliestReleaseNs -
					samples[1].queueSampleNs);
			prtQueue = extrapolated >=
				std::numeric_limits<uint64_t>::max() ?
				std::numeric_limits<uint64_t>::max() :
				(uint64_t)std::ceil(extrapolated);
		}else if (samples.size() == 1){
			uint64_t age = group.earliestReleaseNs >
				samples[0].queueSampleNs ?
				group.earliestReleaseNs -
					samples[0].queueSampleNs : 0;
			long double margin =
				(long double)(samples[0].capacityBps ?
					samples[0].capacityBps : capacity) * age / 8e9L;
			long double conservative = samples[0].queueBytes + margin;
			prtQueue = conservative >=
				std::numeric_limits<uint64_t>::max() ?
				std::numeric_limits<uint64_t>::max() :
				(uint64_t)std::ceil(conservative);
			prtFallback = 1; // one_probe_conservative_margin
		}else{
			prtQueue = originalBopQueue;
			prtFallback = 2; // original_bop_q0
		}
	}
	NS_ASSERT_MSG(!isBopFamily || (owner->m_bopRho > 0 &&
			owner->m_bopRho <= 1 && capacity > background),
			"invalid BOP available capacity");
	double available = isBopFamily ?
		owner->m_bopRho * capacity - background : capacity;
	double linkTime = isBopFamily ?
		8.0 * (queue + totalBytes) / available : 0;
	double star = isBopFamily ? std::max(maximumLine, linkTime) : 0;

	uint64_t ecnThreshold = 0, packetMargin = 0, queueRoom = 0;
	uint64_t bdpCredit = 0, groupCredit = 0, allocatedCredit = 0;
	double queueSampleAgeUs = 0;
	double feedbackTauUs = 0;
	uint32_t tauSource = BOP_QC_TAU_NOT_QC;
	uint32_t qcFallback = BOP_QC_FALLBACK_NOT_QC;
	std::vector<uint64_t> credits(group.members.size(), 0);
	if (isBopQc){
		NS_ASSERT_MSG(owner->m_bopQcQueueLimitMode == 1,
				"BOP-QC v1 only supports ECN-threshold queue limit mode");
		ecnThreshold = owner->m_bopQcEcnThresholdBytes;
		NS_ASSERT_MSG(ecnThreshold > 0, "BOP-QC ECN threshold is zero");
		NS_ASSERT_MSG(group.participantCount == group.members.size(),
				"BOP-QC participant count mismatch");
		NS_ASSERT_MSG(owner->m_bopQcPacketMargin == 0 ||
				group.participantCount <=
				std::numeric_limits<uint64_t>::max() /
				owner->m_bopPacketBytes /
				owner->m_bopQcPacketMargin,
				"BOP-QC packet margin overflow");
		packetMargin = (uint64_t)group.participantCount *
			owner->m_bopPacketBytes * owner->m_bopQcPacketMargin;
		queueRoom = queue < ecnThreshold &&
			packetMargin < ecnThreshold - queue ?
			ecnThreshold - queue - packetMargin : 0;
		feedbackTauUs = tauValid ?
			tauEwmaNs / 1000.0 : owner->m_bopQcDefaultTauUs;
		tauSource = tauValid ? BOP_QC_TAU_EWMA :
			BOP_QC_TAU_DEFAULT;
		long double creditValue =
			((long double)(capacity - background) *
			 feedbackTauUs * 1e-6L / 8.0L) *
			owner->m_bopQcBdpFactor;
		NS_ASSERT_MSG(std::isfinite((double)creditValue) &&
				creditValue >= 0,
				"BOP-QC BDP credit is not finite and nonnegative");
		bdpCredit = creditValue >=
			std::numeric_limits<uint64_t>::max() ?
			std::numeric_limits<uint64_t>::max() :
			(uint64_t)std::floor(creditValue);
		groupCredit = std::min(totalBytes,
			std::min(queueRoom, bdpCredit));
		if (telemetry && queueSampleTime <=
				Simulator::Now().GetTimeStep())
			queueSampleAgeUs =
				(Simulator::Now().GetTimeStep() - queueSampleTime) /
				1000.0;
		qcFallback = BOP_QC_FALLBACK_NONE;
		if (!telemetry)
			qcFallback |= BOP_QC_FALLBACK_NO_QUEUE;
		if (!tauValid)
			qcFallback |= BOP_QC_FALLBACK_DEFAULT_TAU;
		if (group.roundIndex == 0)
			qcFallback |= BOP_QC_FALLBACK_FIRST_ROUND;

		for (uint32_t index = 0; index < group.members.size(); ++index){
			uint64_t bytes = group.members[index].qp->crfm.rounds[
				group.members[index].roundIndex].roundBytes;
			credits[index] = (uint64_t)std::floor(
				(long double)groupCredit * bytes / totalBytes);
			NS_ASSERT_MSG(credits[index] <= bytes,
					"BOP-QC per-flow credit exceeds round bytes");
			allocatedCredit += credits[index];
		}
		uint64_t remainder = groupCredit - allocatedCredit;
		for (uint32_t rank = 0; remainder > 0 &&
				rank < group.members.size(); ++rank){
			bool found = false;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				RdmaQueuePair::CrfmRoundState &round =
					group.members[index].qp->crfm.rounds[
						group.members[index].roundIndex];
				if (round.jitterGroup != rank)
					continue;
				NS_ASSERT_MSG(credits[index] < round.roundBytes,
						"BOP-QC remainder would exceed flow bytes");
				credits[index]++;
				allocatedCredit++;
				remainder--;
				found = true;
				break;
			}
			NS_ASSERT_MSG(found, "BOP-QC sender rank is not contiguous");
		}
		NS_ASSERT_MSG(remainder == 0 && allocatedCredit == groupCredit,
				"BOP-QC deterministic credit allocation mismatch");
		NS_ASSERT_MSG(queue <= ecnThreshold &&
				groupCredit <= ecnThreshold - queue &&
				packetMargin <= ecnThreshold - queue - groupCredit,
				"BOP-QC queue safety bound violated");
	}

	uint64_t qbEcnThreshold = 0, qbQueueTarget = 0;
	uint64_t qbPacketMargin = 0, qbQueueRoom = 0;
	uint64_t qbGroupCredit = 0, qbAllocatedCredit = 0;
	uint32_t qbFallback = BOP_QB_FALLBACK_NOT_QB;
	bool qbSafetyBoundValid = false;
	std::vector<uint64_t> qbCredits(group.members.size(), 0);
		if (isBopQb && !owner->m_bopMultilinkEnable){
		qbEcnThreshold = owner->m_bopQbEcnThresholdBytes;
		NS_ASSERT_MSG(qbEcnThreshold > 0,
				"BOP-QB ECN threshold is zero");
		NS_ASSERT_MSG(group.participantCount == group.members.size(),
				"BOP-QB participant count mismatch");
		NS_ASSERT_MSG(owner->m_bopQbPacketMargin == 0 ||
				group.participantCount <=
				std::numeric_limits<uint64_t>::max() /
				owner->m_bopPacketBytes /
				owner->m_bopQbPacketMargin,
				"BOP-QB packet margin overflow");
		long double targetValue =
			(long double)owner->m_bopQbQueueFraction * qbEcnThreshold;
		NS_ASSERT_MSG(std::isfinite((double)targetValue) &&
				targetValue >= 0 &&
				targetValue <= qbEcnThreshold,
				"BOP-QB queue target is invalid");
		qbQueueTarget = (uint64_t)std::floor(targetValue);
		if (isBopPrt)
			prtQueue = std::min(prtQueue, qbQueueTarget);
		uint64_t qbCreditQueue = isBopPrt ? prtQueue : queue;
		qbPacketMargin = (uint64_t)group.participantCount *
			owner->m_bopPacketBytes * owner->m_bopQbPacketMargin;
		qbQueueRoom = qbCreditQueue < qbQueueTarget &&
			qbPacketMargin < qbQueueTarget - qbCreditQueue ?
			qbQueueTarget - qbCreditQueue - qbPacketMargin : 0;
		qbGroupCredit = std::min(qbQueueRoom, totalBytes);
		qbFallback = BOP_QB_FALLBACK_NONE;
		if (!telemetry)
			qbFallback |= BOP_QB_FALLBACK_NO_QUEUE;
		if (group.roundIndex == 0)
			qbFallback |= BOP_QB_FALLBACK_FIRST_ROUND;

		for (uint32_t index = 0; index < group.members.size(); ++index){
			uint64_t bytes = group.members[index].qp->crfm.rounds[
				group.members[index].roundIndex].roundBytes;
			qbCredits[index] = (uint64_t)std::floor(
				(long double)qbGroupCredit * bytes / totalBytes);
			NS_ASSERT_MSG(qbCredits[index] <= bytes,
					"BOP-QB per-flow credit exceeds round bytes");
			qbAllocatedCredit += qbCredits[index];
		}
		uint64_t remainder = qbGroupCredit - qbAllocatedCredit;
		for (uint32_t rank = 0; remainder > 0 &&
				rank < group.members.size(); ++rank){
			bool found = false;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				RdmaQueuePair::CrfmRoundState &round =
					group.members[index].qp->crfm.rounds[
						group.members[index].roundIndex];
				if (round.jitterGroup != rank)
					continue;
				NS_ASSERT_MSG(qbCredits[index] < round.roundBytes,
						"BOP-QB remainder would exceed flow bytes");
				qbCredits[index]++;
				qbAllocatedCredit++;
				remainder--;
				found = true;
				break;
			}
			NS_ASSERT_MSG(found, "BOP-QB sender rank is not contiguous");
		}
		NS_ASSERT_MSG(remainder == 0 &&
				qbAllocatedCredit == qbGroupCredit,
				"BOP-QB deterministic credit allocation mismatch");
		qbSafetyBoundValid =
			qbCreditQueue <= qbQueueTarget &&
			qbGroupCredit <= qbQueueTarget - qbCreditQueue &&
			qbPacketMargin <=
				qbQueueTarget - qbCreditQueue - qbGroupCredit;
		if (isBopPrt){
			// A conservative one-probe estimate may already consume the
			// entire target before this round injects a byte.  PRT cannot
			// repair that pre-existing estimate; its safe action is exactly
			// zero startup credit.  Preserve the false bound in output, but
			// do not abort a run that adds no burst work.
			NS_ASSERT_MSG(qbSafetyBoundValid || qbGroupCredit == 0,
				"BOP-QB-PRT granted credit with no queue room");
		}else{
			NS_ASSERT_MSG(qbSafetyBoundValid,
				"BOP-QB queue target safety bound violated");
			}
		}
		if (isBopQb && owner->m_bopMultilinkEnable){
			NS_ASSERT_MSG(s_bopMultilinkConfigured,
					"BOP multilink mode has no configured link/path inputs");
			struct LinkRuntime {
				BopMultilinkLink link;
				uint32_t flowCount;
				uint64_t workloadBytes;
				uint64_t queueBytes;
				uint64_t queueRoomBytes;
				uint64_t creditSumBytes;
				uint64_t sampleTimeNs;
				uint64_t arrivalTimeNs;
				bool telemetryValid;
				double tLinkSeconds;
				LinkRuntime()
					: flowCount(0), workloadBytes(0), queueBytes(0),
					  queueRoomBytes(0), creditSumBytes(0),
					  sampleTimeNs(0), arrivalTimeNs(0),
					  telemetryValid(false), tLinkSeconds(0) {}
			};
			std::map<uint32_t, LinkRuntime> runtime;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				uint32_t flowId = group.members[index].qp->crfm.flowId;
				std::map<uint32_t, std::vector<uint32_t> >::const_iterator path =
					s_bopMultilinkFlowPaths.find(flowId);
				NS_ASSERT_MSG(path != s_bopMultilinkFlowPaths.end(),
						"BOP multilink group member has no fixed path");
				uint64_t bytes = group.members[index].qp->crfm.rounds[
					group.members[index].roundIndex].roundBytes;
				for (uint32_t hop = 0; hop < path->second.size(); ++hop){
					uint32_t linkId = path->second[hop];
					LinkRuntime &state = runtime[linkId];
					state.link = s_bopMultilinkLinks[linkId];
					state.flowCount++;
					state.workloadBytes += bytes;
				}
			}
			NS_ASSERT_MSG(!runtime.empty(),
					"BOP multilink round group has no controlled links");
			uint64_t alphaNumerator = 1, alphaDenominator = 1;
			double maximumLinkTime = 0;
			uint32_t representativeLink = runtime.begin()->first;
			bool anyTelemetry = false;
			for (std::map<uint32_t, LinkRuntime>::iterator it =
					runtime.begin(); it != runtime.end(); ++it){
				LinkRuntime &state = it->second;
				std::map<uint32_t, BopMultilinkObservation>::const_iterator
					observation = s_bopMultilinkObservations.find(it->first);
				if (observation != s_bopMultilinkObservations.end() &&
						observation->second.valid &&
						observation->second.arrivalTimeNs <
							group.earliestReleaseNs){
					state.telemetryValid = true;
					state.queueBytes = observation->second.queueBytes;
					state.sampleTimeNs = observation->second.sampleTimeNs;
					state.arrivalTimeNs = observation->second.arrivalTimeNs;
					anyTelemetry = true;
				}
				long double targetValue =
					(long double)owner->m_bopQbQueueFraction *
					state.link.ecnThresholdBytes;
				uint64_t target = (uint64_t)std::floor(targetValue);
				uint64_t margin = (uint64_t)state.flowCount *
					owner->m_bopPacketBytes *
					owner->m_bopQbPacketMargin;
				state.queueRoomBytes =
					state.queueBytes < target &&
					margin < target - state.queueBytes ?
					target - state.queueBytes - margin : 0;
				NS_ASSERT_MSG(owner->m_bopRho > 0 &&
						owner->m_bopRho <= 1 &&
						owner->m_bopRho * state.link.capacityBps >
							state.link.backgroundBps,
						"invalid BOP multilink available capacity");
				double available = owner->m_bopRho *
					state.link.capacityBps -
					state.link.backgroundBps;
				state.tLinkSeconds =
					8.0 * (state.queueBytes + state.workloadBytes) /
					available;
				if (state.tLinkSeconds > maximumLinkTime){
					maximumLinkTime = state.tLinkSeconds;
					representativeLink = it->first;
				}
				if ((long double)state.queueRoomBytes *
						alphaDenominator <
						(long double)alphaNumerator *
						state.workloadBytes){
					alphaNumerator = state.queueRoomBytes;
					alphaDenominator = state.workloadBytes;
				}
			}
			linkTime = maximumLinkTime;
			star = std::max(maximumLine, maximumLinkTime);
			NS_ASSERT_MSG(std::isfinite(star) && star > 0,
					"BOP multilink T_star is invalid");
			LinkRuntime &representative = runtime[representativeLink];
			capacity = representative.link.capacityBps;
			background = representative.link.backgroundBps;
			queue = representative.queueBytes;
			estimatedQueue = queue;
			queueSampleTime = representative.sampleTimeNs;
			newestArrival = representative.arrivalTimeNs;
			telemetry = anyTelemetry;
			qbEcnThreshold = representative.link.ecnThresholdBytes;
			qbQueueTarget = (uint64_t)std::floor(
				(long double)owner->m_bopQbQueueFraction *
				qbEcnThreshold);
			qbPacketMargin = (uint64_t)representative.flowCount *
				owner->m_bopPacketBytes *
				owner->m_bopQbPacketMargin;
			qbQueueRoom = representative.queueRoomBytes;

			qbCredits.assign(group.members.size(), 0);
			qbAllocatedCredit = 0;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				uint64_t bytes = group.members[index].qp->crfm.rounds[
					group.members[index].roundIndex].roundBytes;
				unsigned __int128 product =
					(unsigned __int128)alphaNumerator * bytes;
				qbCredits[index] =
					(uint64_t)(product / alphaDenominator);
				qbAllocatedCredit += qbCredits[index];
			}
			unsigned __int128 targetProduct =
				(unsigned __int128)alphaNumerator * totalBytes;
			uint64_t targetCredit =
				(uint64_t)(targetProduct / alphaDenominator);
			uint64_t remainder = targetCredit - qbAllocatedCredit;
			for (std::map<uint32_t, LinkRuntime>::iterator it =
					runtime.begin(); it != runtime.end(); ++it)
				it->second.creditSumBytes = 0;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				const std::vector<uint32_t> &path =
					s_bopMultilinkFlowPaths[
						group.members[index].qp->crfm.flowId];
				for (uint32_t hop = 0; hop < path.size(); ++hop)
					runtime[path[hop]].creditSumBytes += qbCredits[index];
			}
			std::vector<uint32_t> order(group.members.size());
			for (uint32_t index = 0; index < order.size(); ++index)
				order[index] = index;
			std::sort(order.begin(), order.end(),
				[&group](uint32_t left, uint32_t right) {
					RdmaQueuePair::CrfmRoundState &a =
						group.members[left].qp->crfm.rounds[
							group.members[left].roundIndex];
					RdmaQueuePair::CrfmRoundState &b =
						group.members[right].qp->crfm.rounds[
							group.members[right].roundIndex];
					if (a.jitterGroup != b.jitterGroup)
						return a.jitterGroup < b.jitterGroup;
					return group.members[left].qp->crfm.flowId <
						group.members[right].qp->crfm.flowId;
				});
			while (remainder > 0){
				bool progressed = false;
				for (uint32_t position = 0;
						position < order.size() && remainder > 0;
						++position){
					uint32_t index = order[position];
					uint64_t bytes = group.members[index].qp->crfm.rounds[
						group.members[index].roundIndex].roundBytes;
					if (qbCredits[index] >= bytes)
						continue;
					const std::vector<uint32_t> &path =
						s_bopMultilinkFlowPaths[
							group.members[index].qp->crfm.flowId];
					bool fits = true;
					for (uint32_t hop = 0; hop < path.size(); ++hop)
						if (runtime[path[hop]].creditSumBytes >=
								runtime[path[hop]].queueRoomBytes)
							fits = false;
					if (!fits)
						continue;
					qbCredits[index]++;
					qbAllocatedCredit++;
					remainder--;
					for (uint32_t hop = 0; hop < path.size(); ++hop)
						runtime[path[hop]].creditSumBytes++;
					progressed = true;
				}
				NS_ASSERT_MSG(progressed,
						"BOP multilink deterministic remainder is infeasible");
			}
			qbGroupCredit = qbAllocatedCredit;
			qbFallback = BOP_QB_FALLBACK_NONE;
			if (!anyTelemetry)
				qbFallback |= BOP_QB_FALLBACK_NO_QUEUE;
			std::map<uint32_t, int64_t>::const_iterator predecessor =
				s_bopMultilinkGroupPredecessors.find(groupId);
			if (predecessor != s_bopMultilinkGroupPredecessors.end() &&
					predecessor->second < 0)
				qbFallback |= BOP_QB_FALLBACK_FIRST_ROUND;

			bool formulaValid = true;
			bool capacityValid = true;
			bool creditValid = true;
			uint32_t limitingCount = 0;
			for (std::map<uint32_t, LinkRuntime>::iterator it =
					runtime.begin(); it != runtime.end(); ++it){
				LinkRuntime &state = it->second;
				long double baseRateSum = 0;
				for (uint32_t index = 0;
						index < group.members.size(); ++index){
					const std::vector<uint32_t> &path =
						s_bopMultilinkFlowPaths[
							group.members[index].qp->crfm.flowId];
					if (std::find(path.begin(), path.end(), it->first) ==
							path.end())
						continue;
					RdmaQueuePair::CrfmRoundState &memberRound =
						group.members[index].qp->crfm.rounds[
							group.members[index].roundIndex];
					uint64_t selected = (uint64_t)std::floor(
						memberRound.roundBytes * 8.0 / star);
					selected = std::max((uint64_t)1,
						std::min(selected,
							group.members[index].qp->m_max_rate.GetBitRate()));
					baseRateSum += selected;
				}
				long double available = owner->m_bopRho *
					state.link.capacityBps - state.link.backgroundBps;
				bool linkCapacityValid =
					baseRateSum <= available + 1.0L;
				bool linkCreditValid =
					state.creditSumBytes <= state.queueRoomBytes;
				bool limiting = std::fabs(
					state.tLinkSeconds - star) <=
					std::max(1e-15, star * 1e-12);
				if (limiting)
					limitingCount++;
				formulaValid = formulaValid &&
					std::isfinite(state.tLinkSeconds) &&
					state.workloadBytes > 0;
				capacityValid = capacityValid && linkCapacityValid;
				creditValid = creditValid && linkCreditValid;
				BopMultilinkLinkDecision decision;
				decision.groupId = groupId;
				decision.roundIndex = group.roundIndex;
				decision.linkId = it->first;
				decision.capacityBps = state.link.capacityBps;
				decision.queueBytes = state.queueBytes;
				decision.ecnThresholdBytes =
					state.link.ecnThresholdBytes;
				decision.flowCount = state.flowCount;
				decision.workloadBytes = state.workloadBytes;
				decision.queueRoomBytes = state.queueRoomBytes;
				decision.creditSumBytes = state.creditSumBytes;
				decision.tLinkSeconds = state.tLinkSeconds;
				decision.limitingLink = limiting;
				decision.tStarSeconds = star;
				decision.formulaValid = formulaValid;
				decision.capacityValid = linkCapacityValid;
				decision.creditConstraintValid = linkCreditValid;
				s_bopMultilinkLinkDecisions.push_back(decision);
			}
			qbSafetyBoundValid = creditValid;
			NS_ASSERT_MSG(formulaValid && capacityValid && creditValid,
					"BOP multilink formula or constraint check failed");
			BopMultilinkGroupDecision groupDecision;
			groupDecision.groupId = groupId;
			groupDecision.roundIndex = group.roundIndex;
			groupDecision.participantCount = group.participantCount;
			groupDecision.totalRoundBytes = totalBytes;
			groupDecision.alpha = (double)alphaNumerator /
				alphaDenominator;
			groupDecision.tStarSeconds = star;
			groupDecision.limitingLinkCount = limitingCount;
			groupDecision.formulaValid = formulaValid;
			groupDecision.capacityValid = capacityValid;
			groupDecision.creditConstraintValid = creditValid;
			s_bopMultilinkGroupDecisions.push_back(groupDecision);
		}
		double qbQueueSampleAgeUs = telemetry &&
		queueSampleTime <= Simulator::Now().GetTimeStep() ?
		(Simulator::Now().GetTimeStep() - queueSampleTime) / 1000.0 : 0;
	uint32_t qbQueueOrigin = isBopQbOracle ?
		BOP_Q0_ORIGIN_ORACLE_RELEASE :
		(telemetry ? BOP_Q0_ORIGIN_INT : BOP_Q0_ORIGIN_NONE);
	int64_t qbQueueError = (int64_t)estimatedQueue -
		(int64_t)actualQueue;
	double qbQueueErrorRatio = actualQueue ?
		(double)qbQueueError / actualQueue : 0;
	bool qbSafetyUsingActual = isBopQb &&
		actualQueue <= qbQueueTarget &&
		qbGroupCredit <= qbQueueTarget - actualQueue &&
		qbPacketMargin <=
			qbQueueTarget - actualQueue - qbGroupCredit;

	uint64_t qbMaxEcnThreshold = 0, qbMaxPacketMargin = 0;
	uint64_t qbMaxQueueRoom = 0, qbMaxGroupCredit = 0;
	uint64_t qbMaxAllocatedCredit = 0;
	double qbMaxQueueSampleAgeUs = 0;
	uint32_t qbMaxFallback = BOP_QB_MAX_FALLBACK_NOT_QB_MAX;
	bool qbMaxSafetyBoundValid = false;
	std::vector<uint64_t> qbMaxCredits(group.members.size(), 0);
	if (isBopQbMax){
		qbMaxEcnThreshold = owner->m_bopQbMaxEcnThresholdBytes;
		NS_ASSERT_MSG(qbMaxEcnThreshold > 0,
				"BOP-QB-Max ECN threshold is zero");
		NS_ASSERT_MSG(group.participantCount == group.members.size(),
				"BOP-QB-Max participant count mismatch");
		NS_ASSERT_MSG(owner->m_bopQbMaxPacketMargin == 0 ||
				group.participantCount <=
				std::numeric_limits<uint64_t>::max() /
				owner->m_bopPacketBytes /
				owner->m_bopQbMaxPacketMargin,
				"BOP-QB-Max packet margin overflow");
		qbMaxPacketMargin = (uint64_t)group.participantCount *
			owner->m_bopPacketBytes * owner->m_bopQbMaxPacketMargin;
		qbMaxQueueRoom = queue < qbMaxEcnThreshold &&
			qbMaxPacketMargin < qbMaxEcnThreshold - queue ?
			qbMaxEcnThreshold - queue - qbMaxPacketMargin : 0;
		qbMaxGroupCredit = std::min(
			qbMaxQueueRoom, totalBytes);
		if (telemetry && queueSampleTime <=
				Simulator::Now().GetTimeStep())
			qbMaxQueueSampleAgeUs =
				(Simulator::Now().GetTimeStep() - queueSampleTime) /
				1000.0;
		qbMaxFallback = telemetry ? BOP_QB_MAX_FALLBACK_NONE :
			BOP_QB_MAX_FALLBACK_NO_PRE_RELEASE_QUEUE;

		for (uint32_t index = 0; index < group.members.size(); ++index){
			uint64_t bytes = group.members[index].qp->crfm.rounds[
				group.members[index].roundIndex].roundBytes;
			qbMaxCredits[index] = (uint64_t)std::floor(
				(long double)qbMaxGroupCredit * bytes / totalBytes);
			NS_ASSERT_MSG(qbMaxCredits[index] <= bytes,
					"BOP-QB-Max per-flow credit exceeds round bytes");
			qbMaxAllocatedCredit += qbMaxCredits[index];
		}
		uint64_t remainder =
			qbMaxGroupCredit - qbMaxAllocatedCredit;
		for (uint32_t rank = 0; remainder > 0 &&
				rank < group.members.size(); ++rank){
			bool found = false;
			for (uint32_t index = 0; index < group.members.size(); ++index){
				RdmaQueuePair::CrfmRoundState &round =
					group.members[index].qp->crfm.rounds[
						group.members[index].roundIndex];
				if (round.jitterGroup != rank)
					continue;
				NS_ASSERT_MSG(qbMaxCredits[index] < round.roundBytes,
						"BOP-QB-Max remainder would exceed flow bytes");
				qbMaxCredits[index]++;
				qbMaxAllocatedCredit++;
				remainder--;
				found = true;
				break;
			}
			NS_ASSERT_MSG(found,
					"BOP-QB-Max sender rank is not contiguous");
		}
		NS_ASSERT_MSG(remainder == 0 &&
				qbMaxAllocatedCredit == qbMaxGroupCredit,
				"BOP-QB-Max deterministic credit allocation mismatch");
		qbMaxSafetyBoundValid =
			queue <= qbMaxEcnThreshold &&
			qbMaxGroupCredit <= qbMaxEcnThreshold - queue &&
			qbMaxPacketMargin <=
				qbMaxEcnThreshold - queue - qbMaxGroupCredit;
		NS_ASSERT_MSG(qbMaxSafetyBoundValid,
				"BOP-QB-Max ECN safety bound violated");
	}

	for (uint32_t rank = 0; rank < group.members.size(); ++rank){
		RoundGroupMember &member = group.members[rank];
		RdmaQueuePair::CrfmRoundState &round =
			member.qp->crfm.rounds[member.roundIndex];
		round.commonReleaseTimeNs = group.commonReleaseNs;
		round.bopMaxRateBps = member.qp->m_max_rate.GetBitRate();
		round.bopResidualQueueBytes = queue;
		round.bopBottleneckBps = capacity;
		round.bopBackgroundBps = background;
		round.bopTLineSeconds = maximumLine;
		round.bopTLinkSeconds = linkTime;
		round.bopTStarSeconds = star;
		round.bopQbEstimatedQueueBytes = estimatedQueue;
		round.bopQbActualQueueBytes = actualQueue;
		round.bopQbQueueErrorBytes = qbQueueError;
		round.bopQbQueueErrorRatio = qbQueueErrorRatio;
		round.bopQbQueueSampleAgeUs = qbQueueSampleAgeUs;
		round.bopQbQueueSampleOrigin = qbQueueOrigin;
		round.bopQbSafetyBoundUsingActual = qbSafetyUsingActual;
		if (isBopPrt){
			round.prtProbeCountSent = group.prtProbeCountSent;
			round.prtProbeReturnedBeforeRelease = prtReturned;
			round.prtDecisionReleaseNs = group.earliestReleaseNs;
			round.prtProbe1SendNs = group.prtProbe[0].sendNs;
			round.prtProbe1QueueSampleNs =
				group.prtProbe[0].queueSampleNs;
			round.prtProbe1AckNs = group.prtProbe[0].ackNs;
			round.prtProbe1QueueBytes = group.prtProbe[0].queueBytes;
			round.prtProbe2SendNs = group.prtProbe[1].sendNs;
			round.prtProbe2QueueSampleNs =
				group.prtProbe[1].queueSampleNs;
			round.prtProbe2AckNs = group.prtProbe[1].ackNs;
			round.prtProbe2QueueBytes = group.prtProbe[1].queueBytes;
			round.prtQueueSlopeBytesPerNs = prtSlope;
			round.prtQueueHatBytes = prtQueue;
			round.prtActualQueueBytes = actualQueue;
			round.prtQueueErrorBytes =
				(int64_t)prtQueue - (int64_t)actualQueue;
			round.prtFallbackReason = prtFallback;
			uint64_t originalRoom =
				originalBopQueue < qbQueueTarget &&
				qbPacketMargin <
					qbQueueTarget - originalBopQueue ?
				qbQueueTarget - originalBopQueue -
					qbPacketMargin : 0;
			round.prtOriginalBopCreditBytes =
				std::min(originalRoom, totalBytes);
			round.prtCreditBytes = qbGroupCredit;
		}
		round.bopFallbackReason = isBopFamily ?
			(group.roundIndex == 0 ? BOP_FALLBACK_INITIAL_QUEUE_ZERO :
			 (telemetry ? BOP_FALLBACK_NONE :
			  BOP_FALLBACK_NO_VALID_TELEMETRY)) :
			BOP_FALLBACK_NOT_BOP;
		uint64_t selected = member.qp->m_rate.GetBitRate();
		if (isBopFamily){
			selected = (uint64_t)std::floor(
				round.roundBytes * 8.0 / star);
			selected = std::max((uint64_t)1,
				std::min(selected, round.bopMaxRateBps));
			round.bopPlanApplied = true;
			round.bopSelectedRateBps = selected;
			bool phaseStagger = isBop ? owner->m_bopPhaseStagger :
				(isBopQc ? owner->m_bopQcEnablePhaseStagger :
				 (isBopQb ? owner->m_bopQbEnablePhaseStagger :
				  owner->m_bopQbMaxEnablePhaseStagger));
			round.bopPhaseOffsetNs = phaseStagger ?
				(uint64_t)((long double)round.jitterGroup *
				 owner->m_bopPacketBytes * 8000000000.0L / capacity) : 0;
			if (isBop){
				member.hw->SetRoundStartRate(member.qp, selected);
			}else if (isBopQc){
				round.bopQcBaseRateBps = selected;
				round.bopQcCreditBytes = credits[rank];
				round.bopQcCreditEndSeq =
					round.startSeq + credits[rank];
				round.bopQcBurstRateBps =
					member.qp->m_max_rate.GetBitRate();
				round.bopQcQueueSampleAgeUs = queueSampleAgeUs;
				round.bopQcFeedbackTauUs = feedbackTauUs;
				round.bopQcTauSource = tauSource;
				round.bopQcEcnThresholdBytes = ecnThreshold;
				round.bopQcPacketMarginBytes = packetMargin;
				round.bopQcQueueRoomBytes = queueRoom;
				round.bopQcBdpCreditBytes = bdpCredit;
				round.bopQcGroupCreditBytes = groupCredit;
				round.bopQcTotalAllocatedCreditBytes = allocatedCredit;
				round.bopQcFallbackReason = qcFallback;
				member.qp->crfm.bopQcBaseRate = selected;
				member.qp->crfm.bopQcCreditTotal = credits[rank];
				member.qp->crfm.bopQcCreditRemaining = credits[rank];
				member.qp->crfm.bopQcCreditEndSeq =
					round.bopQcCreditEndSeq;
				member.qp->crfm.bopQcPhaseOffsetNs =
					round.bopPhaseOffsetNs;
				member.qp->crfm.bopQcSwitchedToBase = false;
				member.qp->crfm.bopQcSwitchPending = false;
				member.qp->crfm.bopQcActualBurstBytes = 0;
				member.hw->SetRoundStartRate(member.qp,
					credits[rank] > 0 ?
					round.bopQcBurstRateBps : selected);
			}else if (isBopQb){
				round.bopQbBaseRateBps = selected;
				round.bopQbCreditBytes = qbCredits[rank];
				round.bopQbCreditEndSeq =
					round.startSeq + qbCredits[rank];
				round.bopQbBurstRateBps =
					member.qp->m_max_rate.GetBitRate();
				round.bopQbEcnThresholdBytes = qbEcnThreshold;
				round.bopQbQueueTargetBytes = qbQueueTarget;
				round.bopQbPacketMarginBytes = qbPacketMargin;
				round.bopQbQueueRoomBytes = qbQueueRoom;
				round.bopQbGroupCreditBytes = qbGroupCredit;
				round.bopQbTotalAllocatedCreditBytes =
					qbAllocatedCredit;
				round.bopQbFallbackReason = qbFallback;
				round.bopQbSafetyBoundValid = qbSafetyBoundValid;
				round.bopQbEstimatedQueueBytes = estimatedQueue;
				round.bopQbActualQueueBytes = actualQueue;
				round.bopQbQueueErrorBytes = qbQueueError;
				round.bopQbQueueErrorRatio = qbQueueErrorRatio;
				round.bopQbQueueSampleAgeUs = qbQueueSampleAgeUs;
				round.bopQbQueueSampleOrigin = qbQueueOrigin;
				round.bopQbSafetyBoundUsingActual = qbSafetyUsingActual;
				member.qp->crfm.bopQbBaseRate = selected;
				member.qp->crfm.bopQbCreditTotal = qbCredits[rank];
				member.qp->crfm.bopQbCreditRemaining =
					qbCredits[rank];
				member.qp->crfm.bopQbCreditEndSeq =
					round.bopQbCreditEndSeq;
				member.qp->crfm.bopQbPhaseOffsetNs =
					round.bopPhaseOffsetNs;
				member.qp->crfm.bopQbSwitchedToBase = false;
				member.qp->crfm.bopQbSwitchPending = false;
				member.qp->crfm.bopQbActualBurstBytes = 0;
				member.hw->SetRoundStartRate(member.qp,
					qbCredits[rank] > 0 ?
					round.bopQbBurstRateBps : selected);
			}else{
				round.bopQbMaxBaseRateBps = selected;
				round.bopQbMaxCreditBytes = qbMaxCredits[rank];
				round.bopQbMaxCreditEndSeq =
					round.startSeq + qbMaxCredits[rank];
				round.bopQbMaxBurstRateBps =
					member.qp->m_max_rate.GetBitRate();
				round.bopQbMaxQueueSampleTimeNs =
					telemetry ? queueSampleTime : 0;
				round.bopQbMaxQueueSampleAgeUs =
					qbMaxQueueSampleAgeUs;
				round.bopQbMaxEcnThresholdBytes =
					qbMaxEcnThreshold;
				round.bopQbMaxPacketMarginBytes =
					qbMaxPacketMargin;
				round.bopQbMaxQueueRoomBytes =
					qbMaxQueueRoom;
				round.bopQbMaxGroupCreditBytes =
					qbMaxGroupCredit;
				round.bopQbMaxTotalAllocatedCreditBytes =
					qbMaxAllocatedCredit;
				round.bopQbMaxFallbackReason =
					qbMaxFallback;
				round.bopQbMaxSafetyBoundValid =
					qbMaxSafetyBoundValid;
				member.qp->crfm.bopQbMaxBaseRate = selected;
				member.qp->crfm.bopQbMaxCreditTotal =
					qbMaxCredits[rank];
				member.qp->crfm.bopQbMaxCreditRemaining =
					qbMaxCredits[rank];
				member.qp->crfm.bopQbMaxCreditEndSeq =
					round.bopQbMaxCreditEndSeq;
				member.qp->crfm.bopQbMaxPhaseOffsetNs =
					round.bopPhaseOffsetNs;
				member.qp->crfm.bopQbMaxSwitchedToBase = false;
				member.qp->crfm.bopQbMaxSwitchPending = false;
				member.qp->crfm.bopQbMaxActualBurstBytes = 0;
				member.hw->SetRoundStartRate(member.qp,
					qbMaxCredits[rank] > 0 ?
					round.bopQbMaxBurstRateBps : selected);
			}
		}else{
			round.bopSelectedRateBps = selected;
		}
		int64_t actual = (int64_t)group.commonReleaseNs + round.jitterNs;
		NS_ASSERT_MSG(actual >= (int64_t)Simulator::Now().GetTimeStep(),
				"sender release precedes group plan");
		Simulator::Schedule(NanoSeconds(
			(uint64_t)actual - Simulator::Now().GetTimeStep()),
			&RdmaHw::ReleaseRound, member.hw, member.qp,
			member.roundIndex);
	}
	group.planned = true;
}

void RdmaHw::NotifyRoundGroupAck(Ptr<RdmaQueuePair> qp,
		uint32_t roundIndex, uint64_t completionNs){
	RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[roundIndex];
	RoundGroupRuntime &group = s_roundGroups[round.roundGroupId];
	group.ackCompleted++;
	group.barrierNs = std::max(group.barrierNs, completionNs);
	NS_ASSERT_MSG(group.ackCompleted <= group.participantCount,
			"too many ACK completions in round group");
	if (group.ackCompleted != group.participantCount)
		return;
	group.barrierComplete = true;
	for (uint32_t i = 0; i < group.members.size(); ++i){
		RdmaQueuePair::CrfmRoundState &memberRound =
			group.members[i].qp->crfm.rounds[group.members[i].roundIndex];
		memberRound.barrierCompletionTimeNs = group.barrierNs;
		memberRound.groupQueueMaxBytes = group.queueMaxBytes;
		memberRound.groupEcnMarks = group.ecnMarks;
		memberRound.groupPfcEvents = group.pfcEvents;
		memberRound.prtPrimerEcn = group.prtPrimerEcn;
			memberRound.prtCollectiveEcn = group.prtCollectiveEcn;
		}
		if (group.members.front().hw->m_bopMultilinkEnable &&
				s_bopMultilinkConfigured) {
			std::map<uint32_t, uint32_t>::const_iterator successor =
				s_bopMultilinkGroupSuccessors.find(round.roundGroupId);
			if (successor == s_bopMultilinkGroupSuccessors.end())
				return;
			RoundGroupRuntime &next = s_roundGroups[successor->second];
			NS_ASSERT_MSG(next.members.size() == next.participantCount,
					"next multilink round group is incomplete at barrier");
			uint64_t gap = next.members.front().qp->crfm.rounds[
				next.members.front().roundIndex].computeGapNs;
			for (uint32_t i = 0; i < next.members.size(); ++i)
				NS_ASSERT_MSG(next.members[i].qp->crfm.rounds[
					next.members[i].roundIndex].computeGapNs == gap,
					"multilink compute gap differs within round group");
			ScheduleRoundGroup(successor->second, group.barrierNs + gap);
			return;
		}
		if (roundIndex + 1 >= qp->crfm.rounds.size())
		return;
	uint32_t nextGroupId = qp->crfm.rounds[roundIndex + 1].roundGroupId;
	RoundGroupRuntime &next = s_roundGroups[nextGroupId];
	NS_ASSERT_MSG(next.members.size() == next.participantCount,
			"next round group is incomplete at barrier");
	uint64_t gap = next.members.front().qp->crfm.rounds[
		next.members.front().roundIndex].computeGapNs;
	for (uint32_t i = 0; i < next.members.size(); ++i)
		NS_ASSERT_MSG(next.members[i].qp->crfm.rounds[
			next.members[i].roundIndex].computeGapNs == gap,
			"compute gap differs within round group");
	ScheduleRoundGroup(nextGroupId, group.barrierNs + gap);
}

void RdmaHw::ObserveRoundBottleneck(uint64_t queueBytes,
		uint64_t ecnDelta, uint64_t pfcDelta){
	uint64_t now = Simulator::Now().GetTimeStep();
	for (std::map<uint32_t, RoundGroupRuntime>::iterator it =
			s_roundGroups.begin(); it != s_roundGroups.end(); ++it){
		RoundGroupRuntime &group = it->second;
		if (!group.planned || group.barrierComplete ||
				now < group.earliestReleaseNs)
			continue;
		group.queueMaxBytes = std::max(group.queueMaxBytes, queueBytes);
		group.ecnMarks += ecnDelta;
		group.pfcEvents += pfcDelta;
	}
}

void RdmaHw::UpdateBopTelemetry(Ptr<RdmaQueuePair> qp,
		int32_t originRound, const HpFeedbackEstimate &estimate,
		uint64_t feedbackTimeNs){
	if ((m_cc_mode != CC_MODE_BOP &&
			m_cc_mode != CC_MODE_BOP_QC &&
			!UsesBopQbCredit(m_cc_mode) &&
			m_cc_mode != CC_MODE_BOP_QB_MAX) ||
			!estimate.valid || originRound < 0)
		return;
	qp->crfm.bopTelemetryValid = true;
	qp->crfm.bopTelemetryOriginRound = originRound;
	qp->crfm.bopLastQueueBytes = estimate.maximumQueueBytes;
	qp->crfm.bopLastSampleTimeNs = estimate.bottleneckSampleTimeNs;
	qp->crfm.bopLastArrivalTimeNs = feedbackTimeNs;
	qp->crfm.bopLastBottleneckBps = estimate.bottleneckCapacityBps;
	if (m_cc_mode == CC_MODE_BOP_QC &&
			estimate.bottleneckSampleTimeNs <= feedbackTimeNs){
		double sampleNs = feedbackTimeNs -
			estimate.bottleneckSampleTimeNs;
		if (!qp->crfm.bopQcTauValid)
			qp->crfm.bopQcTauEwmaNs = sampleNs;
		else
			qp->crfm.bopQcTauEwmaNs =
				m_bopQcTauEwmaAlpha * sampleNs +
				(1 - m_bopQcTauEwmaAlpha) *
				qp->crfm.bopQcTauEwmaNs;
		qp->crfm.bopQcTauValid = true;
	}
}

void RdmaHw::UpdateBopMultilinkTelemetry(Ptr<RdmaQueuePair> qp,
		IntHeader &ih, uint64_t feedbackTimeNs)
{
	if (!m_bopMultilinkEnable || !s_bopMultilinkConfigured ||
			m_cc_mode != CC_MODE_BOP_QB)
		return;
	std::map<uint32_t, std::vector<uint32_t> >::const_iterator path =
		s_bopMultilinkFlowPaths.find(qp->crfm.flowId);
	if (path == s_bopMultilinkFlowPaths.end() ||
			ih.nhop > IntHeader::maxHop)
		return;
	uint32_t telemetryHopCount = 0;
	for (uint32_t index = 0; index < path->second.size(); ++index) {
		std::map<uint32_t, BopMultilinkLink>::const_iterator link =
			s_bopMultilinkLinks.find(path->second[index]);
		if (link != s_bopMultilinkLinks.end() &&
				link->second.telemetryEligible)
			telemetryHopCount++;
	}
	if (ih.nhop != telemetryHopCount)
		return;
	uint64_t modulus = (uint64_t)1 << IntHop::timeWidth;
	uint32_t hop = 0;
	for (uint32_t index = 0; index < path->second.size(); ++index) {
		uint32_t linkId = path->second[index];
		std::map<uint32_t, BopMultilinkLink>::const_iterator link =
			s_bopMultilinkLinks.find(linkId);
		if (link == s_bopMultilinkLinks.end() ||
				!link->second.telemetryEligible)
			continue;
		if (hop >= ih.nhop ||
				ih.hop[hop].GetLineRate() != link->second.capacityBps)
			return;
		uint64_t sample = (feedbackTimeNs / modulus) * modulus +
			ih.hop[hop].GetTime();
		if (sample > feedbackTimeNs)
			sample -= modulus;
		BopMultilinkObservation &observation =
			s_bopMultilinkObservations[linkId];
		if (!observation.valid ||
				feedbackTimeNs >= observation.arrivalTimeNs) {
			observation.valid = true;
			observation.queueBytes = ih.hop[hop].GetQlen();
			observation.sampleTimeNs = sample;
			observation.arrivalTimeNs = feedbackTimeNs;
		}
		hop++;
	}
}

void RdmaHw::ResetHpccForRound(Ptr<RdmaQueuePair> qp){
	qp->hp.m_lastUpdateSeq = 0;
	qp->hp.m_incStage = 0;
	qp->hp.m_lastGap = 0;
	qp->hp.u = 1;
	qp->hp.m_curRate = qp->m_max_rate;
	for (uint32_t i = 0; i < IntHeader::maxHop; ++i){
		qp->hp.hop[i].buf[0] = 0;
		qp->hp.hop[i].buf[1] = 0;
		qp->hp.keep[i] = 0;
		qp->hp.hopState[i].u = 1;
		qp->hp.hopState[i].Rc = qp->m_max_rate;
		qp->hp.hopState[i].incStage = 0;
	}
	SetCrfmRate(qp, qp->m_max_rate.GetBitRate());
}

void RdmaHw::ReleaseRound(Ptr<RdmaQueuePair> qp, uint32_t roundIndex){
	NS_ASSERT_MSG(qp->crfm.enabled, "release callback on non-round QP");
	NS_ASSERT_MSG(roundIndex < qp->crfm.rounds.size(),
			"round release index out of range");
	NS_ASSERT_MSG((int32_t)roundIndex == qp->crfm.currentRoundIndex + 1,
			"round releases must be ordered for each QP");
	uint64_t now = Simulator::Now().GetTimeStep();
	RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[roundIndex];
	NS_ASSERT_MSG(round.releaseTimeNs == 0, "round released more than once");
	if (roundIndex > 0){
		NS_ASSERT_MSG(qp->crfm.rounds[roundIndex - 1].
				barrierCompletionTimeNs > 0,
				"next round released before global ACK barrier");
	}
	NS_ASSERT_MSG(now == (uint64_t)((int64_t)round.commonReleaseTimeNs +
			round.jitterNs), "release does not match barrier plan plus jitter");
	round.releaseTimeNs = now;

	if (roundIndex > 0){
		RdmaQueuePair::CrfmRoundState &previous =
			qp->crfm.rounds[roundIndex - 1];
		previous.endRate = qp->m_rate.GetBitRate();
	}

	if (m_cc_mode == CC_MODE_HPCC_ROUND_RESET){
		ResetHpccForRound(qp);
	}

	qp->crfm.currentRoundIndex = roundIndex;
	qp->crfm.releasedBytes = round.endSeq;
	if (IsCbapMode(m_cc_mode) && qp->cbap.enabled){
		NS_ASSERT_MSG(qp->cbap.enabled &&
			qp->cbap.phase == RdmaQueuePair::CBAP_PREPARE,
			"CBAP release without completed batch plan");
		if (qp->cbap.sbaEnabled) {
			const CbapSbaController::FlowState *state =
				s_cbapSbaController.GetFlow(qp->crfm.flowId);
			NS_ASSERT_MSG(state, "CBAP-SBA release has no admission state");
			qp->cbap.phase = state->state ==
				CbapSbaController::ADMISSION_HOLD ?
				RdmaQueuePair::CBAP_ADMISSION_HOLD :
				RdmaQueuePair::CBAP_STARTUP_ADMISSION;
		} else if (qp->cbap.v20Enabled)
			qp->cbap.phase = qp->cbap.handedOff ?
				RdmaQueuePair::CBAP_BASE_CC_ONLY :
				RdmaQueuePair::CBAP_STARTUP_ADMISSION;
		else
			qp->cbap.phase = RdmaQueuePair::CBAP_ADMISSION_HOLD;
		qp->cbap.admissionEnterNs = now;
		qp->cbap.admissionExitNs = 0;
		qp->cbap.firstDataTxNs = 0;
		qp->cbap.firstPostReleaseSampleNs = 0;
		qp->cbap.firstCompleteFreshFeedbackNs = 0;
		qp->cbap.bytesSentBeforeFreshFeedback = 0;
		qp->cbap.creditRemainingAtAdmissionExit = 0;
		qp->cbap.creditGateActive = qp->cbap.fullCredit &&
			!qp->cbap.v20Enabled;
		qp->cbap.creditGateEnterNs = qp->cbap.fullCredit ? now : 0;
		qp->cbap.creditGateExitNs = 0;
		qp->cbap.bytesSentAtRelease = qp->snd_nxt;
		qp->cbap.bytesAckedAtRelease = qp->snd_una;
		qp->cbap.lastEpochSndNxt = qp->snd_nxt;
		qp->cbap.baseEligibilityLastNs = now;
		qp->cbap.baseEligibleBytes = 0;
		CbapFlowRuntime &flow = s_cbapFlows[qp->crfm.flowId];
		flow.active = true;
	}
	round.startRate = qp->m_rate.GetBitRate();
	round.minimumRate = round.startRate;
	round.endRate = round.startRate;
	round.dcqcnStartAlpha = qp->mlx.m_alpha;
	round.dcqcnEndAlpha = qp->mlx.m_alpha;
	round.dcqcnStartRecoveryStage = qp->mlx.m_rpTimeStage;
	round.dcqcnEndRecoveryStage = qp->mlx.m_rpTimeStage;
	if (roundIndex > 0)
		qp->crfm.rounds[roundIndex - 1].nextRoundStartRate =
			round.startRate;
	if ((m_cc_mode == CC_MODE_BOP ||
			m_cc_mode == CC_MODE_BOP_QC ||
			UsesBopQbCredit(m_cc_mode) ||
			m_cc_mode == CC_MODE_BOP_QB_MAX) &&
			round.bopPhaseOffsetNs > 0){
		Time firstPacket = Simulator::Now() +
			NanoSeconds(round.bopPhaseOffsetNs);
		if (qp->m_nextAvail < firstPacket)
			qp->m_nextAvail = firstPacket;
	}
	uint32_t nicIndex = GetNicIdxOfQp(qp);
	m_nic[nicIndex].dev->TriggerTransmit();
}

void RdmaHw::DeleteQueuePair(Ptr<RdmaQueuePair> qp){
	// remove qp from the m_qpMap
	uint64_t key = GetQpKey(qp->dip.Get(), qp->sport, qp->m_pg);
	m_qpMap.erase(key);
}

Ptr<RdmaRxQueuePair> RdmaHw::GetRxQp(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport, uint16_t pg, bool create){
	uint64_t key = ((uint64_t)dip << 32) | ((uint64_t)pg << 16) | (uint64_t)dport;
	auto it = m_rxQpMap.find(key);
	if (it != m_rxQpMap.end())
		return it->second;
	if (create){
		// create new rx qp
		Ptr<RdmaRxQueuePair> q = CreateObject<RdmaRxQueuePair>();
		// init the qp
		q->sip = sip;
		q->dip = dip;
		q->sport = sport;
		q->dport = dport;
		q->m_ecn_source.qIndex = pg;
		// store in map
		m_rxQpMap[key] = q;
		return q;
	}
	return NULL;
}
uint32_t RdmaHw::GetNicIdxOfRxQp(Ptr<RdmaRxQueuePair> q){
	auto &v = m_rtTable[q->dip];
	if (v.size() > 0){
		return v[q->GetHash() % v.size()];
	}else{
		NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
	}
}
void RdmaHw::DeleteRxQp(uint32_t dip, uint16_t pg, uint16_t dport){
	uint64_t key = ((uint64_t)dip << 32) | ((uint64_t)pg << 16) | (uint64_t)dport;
	m_rxQpMap.erase(key);
}

int RdmaHw::ReceiveUdp(Ptr<Packet> p, CustomHeader &ch){
	PrtProbeTag probe;
	if (p->PeekPacketTag(probe)){
		Ptr<RdmaRxQueuePair> rxQp = GetRxQp(ch.dip, ch.sip,
			ch.udp.dport, ch.udp.sport, ch.udp.pg, true);
		qbbHeader ack;
		ack.SetSeq(ch.udp.seq);
		ack.SetPG(ch.udp.pg);
		ack.SetSport(ch.udp.dport);
		ack.SetDport(ch.udp.sport);
		ack.SetIntHeader(ch.udp.ih);
		Ptr<Packet> reply = Create<Packet>(
			std::max(60 - 14 - 20 - (int)ack.GetSerializedSize(), 0));
		reply->AddHeader(ack);
		Ipv4Header ip;
		ip.SetDestination(Ipv4Address(ch.sip));
		ip.SetSource(Ipv4Address(ch.dip));
		ip.SetProtocol(0xFC);
		ip.SetTtl(64);
		ip.SetPayloadSize(reply->GetSize());
		ip.SetIdentification(rxQp->m_ipid++);
		reply->AddHeader(ip);
		AddHeader(reply, 0x800);
		reply->AddPacketTag(probe);
		uint32_t nic = GetNicIdxOfRxQp(rxQp);
		m_nic[nic].dev->RdmaEnqueueHighPrioQ(reply);
		m_nic[nic].dev->TriggerTransmit();
		return 0;
	}
	uint8_t ecnbits = ch.GetIpv4EcnBits();

	if (m_cc_mode == CC_MODE_DCQCN_WIRE_EQUALIZED){
		NS_ASSERT_MSG(p->GetSize() >=
				ch.GetSerializedSize() + WirePaddingHeader::SIZE,
				"wire-equalized DATA is missing diagnostic padding");
		p->RemoveAtEnd(WirePaddingHeader::SIZE);
	}
	uint32_t payload_size = p->GetSize() - ch.GetSerializedSize();

	// TODO find corresponding rx queue pair
	Ptr<RdmaRxQueuePair> rxQp = GetRxQp(ch.dip, ch.sip, ch.udp.dport, ch.udp.sport, ch.udp.pg, true);
	if (ecnbits != 0){
		rxQp->m_ecn_source.ecnbits |= ecnbits;
		rxQp->m_ecn_source.qfb++;
	}
	rxQp->m_ecn_source.total++;
	rxQp->m_milestone_rx = m_ack_interval;

	int x = ReceiverCheckSeq(ch.udp.seq, rxQp, payload_size);
	if (x == 1 || x == 2){ //generate ACK or NACK
		qbbHeader seqh;
		seqh.SetSeq(rxQp->ReceiverNextExpectedSeq);
		seqh.SetPG(ch.udp.pg);
		seqh.SetSport(ch.udp.dport);
		seqh.SetDport(ch.udp.sport);
		seqh.SetIntHeader(ch.udp.ih);
		if (ecnbits)
			seqh.SetCnp();

		Ptr<Packet> newp = Create<Packet>(std::max(60-14-20-(int)seqh.GetSerializedSize(), 0));
		newp->AddHeader(seqh);

		Ipv4Header head;	// Prepare IPv4 header
		head.SetDestination(Ipv4Address(ch.sip));
		head.SetSource(Ipv4Address(ch.dip));
		head.SetProtocol(x == 1 ? 0xFC : 0xFD); //ack=0xFC nack=0xFD
		head.SetTtl(64);
		head.SetPayloadSize(newp->GetSize());
		head.SetIdentification(rxQp->m_ipid++);

		newp->AddHeader(head);
		AddHeader(newp, 0x800);	// Attach PPP header
		// send
		uint32_t nic_idx = GetNicIdxOfRxQp(rxQp);
		m_nic[nic_idx].dev->RdmaEnqueueHighPrioQ(newp);
		m_nic[nic_idx].dev->TriggerTransmit();
	}
	return 0;
}

int RdmaHw::ReceiveCnp(Ptr<Packet> p, CustomHeader &ch){
	// QCN on NIC
	// This is a Congestion signal
	// Then, extract data from the congestion packet.
	// We assume, without verify, the packet is destinated to me
	uint32_t qIndex = ch.cnp.qIndex;
	if (qIndex == 1){		//DCTCP
		std::cout << "TCP--ignore\n";
		return 0;
	}
	uint16_t udpport = ch.cnp.fid; // corresponds to the sport
	uint8_t ecnbits = ch.cnp.ecnBits;
	uint16_t qfb = ch.cnp.qfb;
	uint16_t total = ch.cnp.total;

	uint32_t i;
	// get qp
	Ptr<RdmaQueuePair> qp = GetQp(ch.sip, udpport, qIndex);//根据udp的port和qindex找到qp队列对
	if (qp == NULL)
		std::cout << "ERROR: QCN NIC cannot find the flow\n";
	// get nic
	uint32_t nic_idx = GetNicIdxOfQp(qp);//再找到对应的nic
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;

	if (qp->m_rate == 0)			//lazy initialization	
	{
		qp->m_rate = dev->GetDataRate();
		if (IsDcqcnMode(m_cc_mode)){
			qp->mlx.m_targetRate = dev->GetDataRate();
			}else if (UsesHpccTelemetryMode(m_cc_mode)){
			qp->hp.m_curRate = dev->GetDataRate();
			if (m_multipleRate){
				for (uint32_t i = 0; i < IntHeader::maxHop; i++)
					qp->hp.hopState[i].Rc = dev->GetDataRate();
			}
		}else if (m_cc_mode == 7){
			qp->tmly.m_curRate = dev->GetDataRate();
		}else if (m_cc_mode == 10){
			qp->hpccPint.m_curRate = dev->GetDataRate();
		}
	}
	return 0;
}

int RdmaHw::ReceiveAck(Ptr<Packet> p, CustomHeader &ch){
	uint16_t qIndex = ch.ack.pg;
	uint16_t port = ch.ack.dport;
	uint32_t seq = ch.ack.seq;
	uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
	int i;
	Ptr<RdmaQueuePair> qp = GetQp(ch.sip, port, qIndex);
	if (qp == NULL){
		std::cout << "ERROR: " << "node:" << m_node->GetId() << ' ' << (ch.l3Prot == 0xFC ? "ACK" : "NACK") << " NIC cannot find the flow\n";
		return 0;
	}
	PrtProbeTag probe;
	if (p->PeekPacketTag(probe)){
		if (m_cc_mode == CC_MODE_BOP_QB_PRT)
			RecordPrtProbeAck(probe.GetGroupId(),
				probe.GetProbeId(), ch.ack.ih);
		return 0;
	}

	uint32_t nic_idx = GetNicIdxOfQp(qp);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	bool finished = false;
	if (m_ack_interval == 0)
		std::cout << "ERROR: shouldn't receive ack\n";
	else {
		if (!m_backto0){
			qp->Acknowledge(seq);
		}else {
			uint32_t goback_seq = seq / m_chunk * m_chunk;
			qp->Acknowledge(goback_seq);
		}
		finished = qp->IsFinished();
		if (qp->crfm.enabled)
			RecordRoundAckCompletion(qp);
		if (finished && !qp->crfm.enabled){
			QpComplete(qp);
		}
	}
	if (ch.l3Prot == 0xFD) // NACK
		RecoverQueue(qp);

	// handle cnp
	if (cnp){
		if (m_cc_mode == CC_MODE_BOP_QB_PRT &&
				qp->crfm.enabled){
			for (std::map<uint32_t, RoundGroupRuntime>::iterator it =
					s_roundGroups.begin(); it != s_roundGroups.end();
					++it){
				RoundGroupRuntime &group = it->second;
				if (!group.planned || group.barrierComplete ||
						Simulator::Now().GetTimeStep() <
						group.earliestReleaseNs)
					continue;
				if (m_finalPrimerFirstFlow !=
						std::numeric_limits<uint32_t>::max() &&
						qp->crfm.flowId >= m_finalPrimerFirstFlow)
					group.prtPrimerEcn++;
				else
					group.prtCollectiveEcn++;
			}
		}
		bool cbapInitHolding =
			m_cc_mode == CC_MODE_CBAP_INIT_ONLY &&
			qp->cbap.enabled &&
			qp->cbap.firstFreshFeedbackNs == 0;
		bool scopedCbapHolding =
			(m_cc_mode == CC_MODE_CBAP_FULL_SCOPED ||
			 m_cc_mode == CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX ||
			 m_cc_mode == CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
			 m_cc_mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION) &&
			qp->cbap.enabled && !qp->cbap.handedOff &&
			!qp->cbap.delegatedEnvelope;
		bool v20CbapHolding = IsCbapV20Mode(m_cc_mode) &&
			qp->cbap.enabled && qp->cbap.v20Enabled &&
			!qp->cbap.handedOff;
		bool sbaStartupOwned = IsCbapSbaMode(m_cc_mode) &&
			qp->cbap.enabled && qp->cbap.sbaEnabled &&
			!qp->cbap.handedOff;
		if (sbaStartupOwned &&
				qp->cbap.phase == RdmaQueuePair::CBAP_STARTUP_ADMISSION &&
				Simulator::Now().GetTimeStep() >=
					qp->cbap.networkReleaseNs &&
				ch.ack.seq > qp->cbap.bytesSentAtRelease)
			HandoffCbapSbaFlow(qp, Simulator::Now().GetTimeStep());
		sbaStartupOwned = sbaStartupOwned && !qp->cbap.handedOff;
		if ((m_cc_mode == CC_MODE_CBAP_FULL_STABLE_HANDOFF ||
				m_cc_mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION) &&
				scopedCbapHolding)
			RecordCbapObservedCnp(qp);
		if (IsDcqcnMode(m_cc_mode) && !cbapInitHolding &&
				!scopedCbapHolding && !v20CbapHolding &&
				!sbaStartupOwned){
			// Exact Mellanox/DCQCN path.  CBAP-INIT-ONLY deliberately
			// hands off only after the first causally fresh summary.
			if (qp->crfm.enabled && ch.ack.seq > 0){
				int32_t origin =
					qp->GetRoundIndexForSequence(ch.ack.seq - 1);
				if (origin >= 0 &&
						(uint32_t)origin < qp->crfm.rounds.size())
					qp->crfm.rounds[origin].cnpCount++;
			}
			cnp_received_mlx(qp);
		} 
	}

	if (qp->crfm.enabled && UsesHpccTelemetryMode(m_cc_mode)){
		HandleAckCrfm(qp, p, ch);
	}else if (m_cc_mode == 3){
		HandleAckHp(qp, p, ch);
	}else if (m_cc_mode == 7){
		HandleAckTimely(qp, p, ch);
	}else if (m_cc_mode == 8){
		HandleAckDctcp(qp, p, ch);
	}else if (m_cc_mode == 10){
		HandleAckHpPint(qp, p, ch);
	}
	if (finished && qp->crfm.enabled)
		QpComplete(qp);
	// ACK may advance the on-the-fly window, allowing more packets to send
	dev->TriggerTransmit();
	return 0;
}

int RdmaHw::Receive(Ptr<Packet> p, CustomHeader &ch){
	if (ch.l3Prot == 0x11){ // UDP
		ReceiveUdp(p, ch);
	}else if (ch.l3Prot == 0xFF){ // CNP
		ReceiveCnp(p, ch);
	}else if (ch.l3Prot == 0xFD){ // NACK
		ReceiveAck(p, ch);
	}else if (ch.l3Prot == 0xFC){ // ACK
		ReceiveAck(p, ch);
	}
	return 0;
}

int RdmaHw::ReceiverCheckSeq(uint32_t seq, Ptr<RdmaRxQueuePair> q, uint32_t size){
	uint32_t expected = q->ReceiverNextExpectedSeq;
	if (seq == expected){
		q->ReceiverNextExpectedSeq = expected + size;
		if (q->ReceiverNextExpectedSeq >= q->m_milestone_rx){
			q->m_milestone_rx += m_ack_interval;
			return 1; //Generate ACK
		}else if (q->ReceiverNextExpectedSeq % m_chunk == 0){
			return 1;
		}else {
			return 5;
		}
	} else if (seq > expected) {
		// Generate NACK
		if (Simulator::Now() >= q->m_nackTimer || q->m_lastNACK != expected){
			q->m_nackTimer = Simulator::Now() + MicroSeconds(m_nack_interval);
			q->m_lastNACK = expected;
			if (m_backto0){
				q->ReceiverNextExpectedSeq = q->ReceiverNextExpectedSeq / m_chunk*m_chunk;
			}
			return 2;
		}else
			return 4;
	}else {
		// Duplicate. 
		return 3;
	}
}
void RdmaHw::AddHeader (Ptr<Packet> p, uint16_t protocolNumber){
	PppHeader ppp;
	ppp.SetProtocol (EtherToPpp (protocolNumber));
	p->AddHeader (ppp);
}
uint16_t RdmaHw::EtherToPpp (uint16_t proto){
	switch(proto){
		case 0x0800: return 0x0021;   //IPv4
		case 0x86DD: return 0x0057;   //IPv6
		default: NS_ASSERT_MSG (false, "PPP Protocol number not defined!");
	}
	return 0;
}

void RdmaHw::RecoverQueue(Ptr<RdmaQueuePair> qp){
	// Go-back-N: everything between snd_una and snd_nxt will be sent again.
	// Count it here because this rewind is the only place retransmission
	// originates, and nothing downstream can distinguish a resent byte from a
	// fresh one.
	if (qp->snd_nxt > qp->snd_una){
		qp->retxBytes += qp->snd_nxt - qp->snd_una;
		qp->retxEvents++;
	}
	qp->snd_nxt = qp->snd_una;
}

void RdmaHw::QpComplete(Ptr<RdmaQueuePair> qp){
	NS_ASSERT(!m_qpCompleteCallback.IsNull());
	if (IsCbapMode(m_cc_mode) && qp->cbap.enabled)
		FinishCbapFlow(qp);
	if (IsDcqcnMode(m_cc_mode)){
		Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
		Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
		Simulator::Cancel(qp->mlx.m_rpTimer);
	}

	// This callback will log info
	// It may also delete the rxQp on the receiver
	m_qpCompleteCallback(qp);

	qp->m_notifyAppFinish();

	// delete the qp
	DeleteQueuePair(qp);
}

void RdmaHw::SetLinkDown(Ptr<QbbNetDevice> dev){
	printf("RdmaHw: node:%u a link down\n", m_node->GetId());
}

void RdmaHw::AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx){
	uint32_t dip = dstAddr.Get();
	m_rtTable[dip].push_back(intf_idx);
}

void RdmaHw::ClearTable(){
	m_rtTable.clear();
}

void RdmaHw::RedistributeQp(){
	// clear old qpGrp
	for (uint32_t i = 0; i < m_nic.size(); i++){
		if (m_nic[i].dev == NULL)
			continue;
		m_nic[i].qpGrp->Clear();
	}

	// redistribute qp
	for (auto &it : m_qpMap){
		Ptr<RdmaQueuePair> qp = it.second;
		uint32_t nic_idx = GetNicIdxOfQp(qp);
		m_nic[nic_idx].qpGrp->AddQp(qp);
		// Notify Nic
		m_nic[nic_idx].dev->ReassignedQp(qp);
	}
}

Ptr<Packet> RdmaHw::GetNxtPacket(Ptr<RdmaQueuePair> qp){
	uint32_t payload_size = qp->GetBytesLeft();
	if (m_mtu < payload_size)
		payload_size = m_mtu;
	bool bopQcBurstPacket = m_cc_mode == CC_MODE_BOP_QC &&
		qp->crfm.enabled && qp->crfm.currentRoundIndex >= 0 &&
		qp->crfm.bopQcCreditTotal > 0 &&
		!qp->crfm.bopQcSwitchedToBase &&
		qp->snd_nxt < qp->crfm.bopQcCreditEndSeq;
	bool bopQbBurstPacket = UsesBopQbCredit(m_cc_mode) &&
		qp->crfm.enabled && qp->crfm.currentRoundIndex >= 0 &&
		qp->crfm.bopQbCreditTotal > 0 &&
		!qp->crfm.bopQbSwitchedToBase &&
		qp->snd_nxt < qp->crfm.bopQbCreditEndSeq;
	bool bopQbMaxBurstPacket = m_cc_mode == CC_MODE_BOP_QB_MAX &&
		qp->crfm.enabled && qp->crfm.currentRoundIndex >= 0 &&
		qp->crfm.bopQbMaxCreditTotal > 0 &&
		!qp->crfm.bopQbMaxSwitchedToBase &&
		qp->snd_nxt < qp->crfm.bopQbMaxCreditEndSeq;
	NS_ASSERT_MSG(!bopQcBurstPacket ||
			qp->m_rate.GetBitRate() == qp->m_max_rate.GetBitRate(),
			"BOP-QC credit packet is not sent at maximum rate");
	NS_ASSERT_MSG(!bopQbBurstPacket ||
			qp->m_rate.GetBitRate() == qp->m_max_rate.GetBitRate(),
			"BOP-QB credit packet is not sent at maximum rate");
	NS_ASSERT_MSG(!bopQbMaxBurstPacket ||
			qp->m_rate.GetBitRate() == qp->m_max_rate.GetBitRate(),
			"BOP-QB-Max credit packet is not sent at maximum rate");
	Ptr<Packet> p = Create<Packet> (payload_size);
	if (m_cc_mode == CC_MODE_DCQCN_WIRE_EQUALIZED){
		WirePaddingHeader header;
		Ptr<Packet> padding = Create<Packet>();
		padding->AddHeader(header);
		p->AddAtEnd(padding);
	}
	// add SeqTsHeader
	SeqTsHeader seqTs;
	seqTs.SetSeq (qp->snd_nxt);
	seqTs.SetPG (qp->m_pg);
	p->AddHeader (seqTs);
	// add udp header
	UdpHeader udpHeader;
	udpHeader.SetDestinationPort (qp->dport);
	udpHeader.SetSourcePort (qp->sport);
	p->AddHeader (udpHeader);
	// add ipv4 header
	Ipv4Header ipHeader;
	ipHeader.SetSource (qp->sip);
	ipHeader.SetDestination (qp->dip);
	ipHeader.SetProtocol (0x11);
	ipHeader.SetPayloadSize (p->GetSize());
	ipHeader.SetTtl (64);
	ipHeader.SetTos (0);
	ipHeader.SetIdentification (qp->m_ipid);
	p->AddHeader(ipHeader);
	// add ppp header
	PppHeader ppp;
	ppp.SetProtocol (0x0021); // EtherToPpp(0x800), see point-to-point-net-device.cc
	p->AddHeader (ppp);
	if (qp->cbap.enabled && qp->cbap.fullCredit &&
			qp->cbap.creditGateActive &&
			qp->cbap.phase == RdmaQueuePair::CBAP_ADMISSION_HOLD){
		qp->UpdateCbapEligibility(Simulator::Now().GetTimeStep());
		uint64_t wireBytes = p->GetSize();
		long double baseUse = std::min(qp->cbap.baseEligibleBytes,
			(long double)wireBytes);
		qp->cbap.baseEligibleBytes -= baseUse;
		uint64_t excess = (uint64_t)std::ceil(std::max(0.0L,
			(long double)wireBytes - baseUse - 1e-9L));
		if (excess > qp->cbap.creditRemainingBytes){
			qp->cbap.creditViolationCount++;
			excess = qp->cbap.creditRemainingBytes;
		}
		qp->cbap.creditRemainingBytes -= excess;
		qp->cbap.excessBytes += excess;
		NS_ASSERT_MSG(qp->cbap.excessBytes <=
			qp->cbap.creditInitialBytes,
			"CBAP startup credit exceeded");
	}

	// update state
	if (qp->cbap.enabled){
		qp->cbap.lastPacketSeq = qp->snd_nxt;
		qp->cbap.lastPacketWireBytes = p->GetSize();
		if (qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING ||
				qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY ||
				qp->cbap.phase == RdmaQueuePair::CBAP_STARTUP_ADMISSION)
			qp->cbap.trackingBytesSent += payload_size;
	}
	qp->snd_nxt += payload_size;
	qp->m_ipid++;
	if (qp->cbap.enabled){
		qp->cbap.phaseAtLastPacket =
			(RdmaQueuePair::CbapPhase)qp->cbap.phase;
	}
	if (bopQcBurstPacket){
		qp->crfm.bopQcActualBurstBytes += payload_size;
		qp->crfm.bopQcCreditRemaining =
			qp->snd_nxt < qp->crfm.bopQcCreditEndSeq ?
			qp->crfm.bopQcCreditEndSeq - qp->snd_nxt : 0;
		if (qp->snd_nxt >= qp->crfm.bopQcCreditEndSeq)
			qp->crfm.bopQcSwitchPending = true;
		RdmaQueuePair::CrfmRoundState &current =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		current.bopQcActualBurstBytes =
			qp->crfm.bopQcActualBurstBytes;
		NS_ASSERT_MSG(current.bopQcActualBurstBytes <=
				current.bopQcCreditBytes + m_mtu,
				"BOP-QC crossed the credit boundary by more than one packet");
	}
	if (bopQbBurstPacket){
		qp->crfm.bopQbActualBurstBytes += payload_size;
		qp->crfm.bopQbCreditRemaining =
			qp->snd_nxt < qp->crfm.bopQbCreditEndSeq ?
			qp->crfm.bopQbCreditEndSeq - qp->snd_nxt : 0;
		if (qp->snd_nxt >= qp->crfm.bopQbCreditEndSeq)
			qp->crfm.bopQbSwitchPending = true;
		RdmaQueuePair::CrfmRoundState &current =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		current.bopQbActualBurstBytes =
			qp->crfm.bopQbActualBurstBytes;
		NS_ASSERT_MSG(current.bopQbActualBurstBytes <=
				current.bopQbCreditBytes + m_mtu,
				"BOP-QB crossed the credit boundary by more than one packet");
	}
	if (bopQbMaxBurstPacket){
		qp->crfm.bopQbMaxActualBurstBytes += payload_size;
		qp->crfm.bopQbMaxCreditRemaining =
			qp->snd_nxt < qp->crfm.bopQbMaxCreditEndSeq ?
			qp->crfm.bopQbMaxCreditEndSeq - qp->snd_nxt : 0;
		if (qp->snd_nxt >= qp->crfm.bopQbMaxCreditEndSeq)
			qp->crfm.bopQbMaxSwitchPending = true;
		RdmaQueuePair::CrfmRoundState &current =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		current.bopQbMaxActualBurstBytes =
			qp->crfm.bopQbMaxActualBurstBytes;
		NS_ASSERT_MSG(current.bopQbMaxActualBurstBytes <=
				current.bopQbMaxCreditBytes + m_mtu,
				"BOP-QB-Max crossed the credit boundary by more than one packet");
	}
	if (qp->crfm.enabled && qp->snd_nxt > 0){
		uint64_t now = Simulator::Now().GetTimeStep();
		int32_t sentRound =
			qp->GetRoundIndexForSequence(qp->snd_nxt - 1);
		if (sentRound >= 0){
			RdmaQueuePair::CrfmRoundState &round =
				qp->crfm.rounds[sentRound];
			round.minimumRate = std::min(
				round.minimumRate, qp->m_rate.GetBitRate());
			round.endRate = qp->m_rate.GetBitRate();
		}
		// Record the first send-side crossing of each contiguous round
		// boundary. ACK-aligned scheduling normally exposes one boundary here.
		for (uint32_t i = 0; i < qp->crfm.rounds.size(); ++i){
			RdmaQueuePair::CrfmRoundState &round =
				qp->crfm.rounds[i];
			if (round.injectionEndTimeNs == 0 &&
					qp->snd_nxt >= round.endSeq)
				round.injectionEndTimeNs = now;
		}
	}

	// return
	return p;
}

void RdmaHw::PktSent(Ptr<RdmaQueuePair> qp, Ptr<Packet> pkt, Time interframeGap){
	qp->lastPktSize = pkt->GetSize();
	if (qp->cbap.enabled){
		uint64_t now = Simulator::Now().GetTimeStep();
		uint64_t previous = qp->cbap.lastTxTimeNs;
		uint64_t expected = qp->cbap.exactGrantPacing ?
			CbapPacketGapNs(pkt->GetSize(), qp->m_rate.GetBitRate()) :
			Seconds(qp->m_rate.CalculateTxTime(
				pkt->GetSize())).GetTimeStep();
		uint64_t actual = previous > 0 && now >= previous ?
			now - previous : 0;
		if (qp->cbap.handedOff && qp->cbap.firstTxAfterHandoffNs == 0){
			qp->cbap.firstTxAfterHandoffNs = now;
			if (qp->cbap.handoffFlowRecordIndex <
					s_cbapHandoffFlowRecords.size()){
				CbapHandoffFlowRecord &handoff = s_cbapHandoffFlowRecords[
					qp->cbap.handoffFlowRecordIndex];
				handoff.firstTxAfterHandoffNs = now;
				handoff.packetGapActualNs = actual;
				handoff.catchupBurstDetected = previous > 0 &&
					actual + 1 < handoff.packetGapRequiredNs;
			}
		}
		// This counter audits CBAP exact-grant pacing only.  Once stable
		// handoff transfers ownership, a DCQCN decrease can legitimately make
		// the gap computed at the new rate larger than the just-finished gap.
		// Counting that retrospective comparison as a CBAP pacing violation
		// crosses the controller ownership boundary and is a false positive.
		if (qp->cbap.exactGrantPacing && !qp->cbap.handedOff &&
				previous > 0 && actual + 1 < expected)
			qp->cbap.pacingViolationCount++;
		if (qp->cbap.firstDataTxNs == 0)
			qp->cbap.firstDataTxNs = now;
		RecordCbapTxEvent(qp, CBAP_TX_SEND, now, now, previous,
			expected, actual, 0);
		qp->cbap.lastTxTimeNs = now;
		if (qp->cbap.phase == RdmaQueuePair::CBAP_TRACKING ||
				qp->cbap.phase == RdmaQueuePair::CBAP_RECOVERY)
			qp->cbap.txTraceTrackingPackets++;
	}
	UpdateNextAvail(qp, interframeGap, pkt->GetSize());
	if (qp->cbap.enabled){
		uint64_t expected = qp->cbap.exactGrantPacing ?
			CbapPacketGapNs(pkt->GetSize(), qp->m_rate.GetBitRate()) :
			Seconds(qp->m_rate.CalculateTxTime(
				pkt->GetSize())).GetTimeStep();
		RecordCbapTxEvent(qp, CBAP_TX_SCHEDULE,
			qp->m_nextAvail.GetTimeStep(), 0,
			qp->cbap.lastTxTimeNs, expected, 0, 0);
	}
	if (m_cc_mode == CC_MODE_BOP_QC &&
			qp->crfm.bopQcSwitchPending){
		NS_ASSERT_MSG(!qp->crfm.bopQcSwitchedToBase,
				"BOP-QC switched from burst to base more than once");
		uint64_t before = qp->m_rate.GetBitRate();
		uint64_t base = qp->crfm.bopQcBaseRate;
		NS_ASSERT_MSG(base > 0 && base <=
				qp->m_max_rate.GetBitRate(),
				"invalid BOP-QC base rate");
		// Preserve the just-sent burst packet's pacing timestamp. ChangeRate
		// would retroactively price that packet at the base rate.
		qp->m_rate = DataRate(base);
		qp->hp.m_curRate = DataRate(base);
		if (m_multipleRate)
			for (uint32_t i = 0; i < IntHeader::maxHop; ++i)
				qp->hp.hopState[i].Rc = DataRate(base);
		qp->crfm.bopQcSwitchPending = false;
		qp->crfm.bopQcSwitchedToBase = true;
		RdmaQueuePair::CrfmRoundState &round =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		NS_ASSERT_MSG(!round.bopQcSwitchedToBase,
				"BOP-QC round recorded more than one switch");
		round.bopQcSwitchedToBase = true;
		round.bopQcActualBurstBytes =
			qp->crfm.bopQcActualBurstBytes;
		round.minimumRate = std::min(round.minimumRate, base);
		round.endRate = base;
		if (before != base){
			qp->crfm.rateTotalVariation +=
				std::fabs((double)before - base);
			qp->crfm.minimumRate =
				std::min(qp->crfm.minimumRate, base);
			qp->crfm.maximumRate =
				std::max(qp->crfm.maximumRate, before);
			}
	}
	if (UsesBopQbCredit(m_cc_mode) &&
			qp->crfm.bopQbSwitchPending){
		NS_ASSERT_MSG(!qp->crfm.bopQbSwitchedToBase,
				"BOP-QB switched from burst to base more than once");
		uint64_t before = qp->m_rate.GetBitRate();
		uint64_t base = qp->crfm.bopQbBaseRate;
		NS_ASSERT_MSG(base > 0 && base <=
				qp->m_max_rate.GetBitRate(),
				"invalid BOP-QB base rate");
		// Keep the burst packet's pacing timestamp at the maximum rate.
		qp->m_rate = DataRate(base);
		qp->hp.m_curRate = DataRate(base);
		if (m_multipleRate)
			for (uint32_t i = 0; i < IntHeader::maxHop; ++i)
				qp->hp.hopState[i].Rc = DataRate(base);
		qp->crfm.bopQbSwitchPending = false;
		qp->crfm.bopQbSwitchedToBase = true;
		RdmaQueuePair::CrfmRoundState &round =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		NS_ASSERT_MSG(!round.bopQbSwitchedToBase,
				"BOP-QB round recorded more than one switch");
		round.bopQbSwitchedToBase = true;
		round.bopQbActualBurstBytes =
			qp->crfm.bopQbActualBurstBytes;
		round.minimumRate = std::min(round.minimumRate, base);
		round.endRate = base;
		if (before != base){
			qp->crfm.rateTotalVariation +=
				std::fabs((double)before - base);
			qp->crfm.minimumRate =
				std::min(qp->crfm.minimumRate, base);
			qp->crfm.maximumRate =
				std::max(qp->crfm.maximumRate, before);
			}
	}
	if (m_cc_mode == CC_MODE_BOP_QB_MAX &&
			qp->crfm.bopQbMaxSwitchPending){
		NS_ASSERT_MSG(!qp->crfm.bopQbMaxSwitchedToBase,
				"BOP-QB-Max switched from burst to base more than once");
		uint64_t before = qp->m_rate.GetBitRate();
		uint64_t base = qp->crfm.bopQbMaxBaseRate;
		NS_ASSERT_MSG(base > 0 && base <=
				qp->m_max_rate.GetBitRate(),
				"invalid BOP-QB-Max base rate");
		// Keep the just-sent burst packet paced at the maximum rate.
		qp->m_rate = DataRate(base);
		qp->hp.m_curRate = DataRate(base);
		if (m_multipleRate)
			for (uint32_t i = 0; i < IntHeader::maxHop; ++i)
				qp->hp.hopState[i].Rc = DataRate(base);
		qp->crfm.bopQbMaxSwitchPending = false;
		qp->crfm.bopQbMaxSwitchedToBase = true;
		RdmaQueuePair::CrfmRoundState &round =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		NS_ASSERT_MSG(!round.bopQbMaxSwitchedToBase,
				"BOP-QB-Max round recorded more than one switch");
		round.bopQbMaxSwitchedToBase = true;
		round.bopQbMaxActualBurstBytes =
			qp->crfm.bopQbMaxActualBurstBytes;
		round.minimumRate = std::min(round.minimumRate, base);
		round.endRate = base;
		if (before != base){
			qp->crfm.rateTotalVariation +=
				std::fabs((double)before - base);
			qp->crfm.minimumRate =
				std::min(qp->crfm.minimumRate, base);
			qp->crfm.maximumRate =
				std::max(qp->crfm.maximumRate, before);
		}
	}
}

uint64_t RdmaHw::EffectivePacingRateBps(Ptr<RdmaQueuePair> qp) const {
	// The rate that actually paces the wire, for every branch and every CC
	// algorithm.  Which rate the controller owns depends on m_rateBound:
	// rate-bound flows are paced by the controller's per-flow rate, others by
	// the NIC line rate.  The application cap is independent of that choice --
	// it is a property of the flow, not of a controller decision -- so it
	// applies to both.  Keeping the min() in one place is the point: two
	// branches previously duplicated the cap check and a third silently
	// skipped it, which let a flow configured for 8Gbps pace at 10Gbps.
	uint64_t controllerRate = m_rateBound ?
		qp->m_rate.GetBitRate() : qp->m_max_rate.GetBitRate();
	if (qp->m_appRateCapBps > 0 && qp->m_appRateCapBps < controllerRate)
		return qp->m_appRateCapBps;
	return controllerRate;
}

void RdmaHw::UpdateNextAvail(Ptr<RdmaQueuePair> qp, Time interframeGap, uint32_t pkt_size){
	Time sendingTime;
	uint64_t effectiveRate = EffectivePacingRateBps(qp);
	// Invariant: pacing never exceeds a configured application cap, whatever
	// the controller asked for and whichever branch computes the gap.
	NS_ASSERT_MSG(qp->m_appRateCapBps == 0 ||
			effectiveRate <= qp->m_appRateCapBps,
		"effective pacing rate exceeds the application rate cap");
	if (m_rateBound && qp->cbap.exactGrantPacing){
		NS_ASSERT_MSG(!qp->cbap.zeroGrantPaused && effectiveRate > 0,
			"zero-grant CBAP flow reached DATA pacing");
		sendingTime = interframeGap + NanoSeconds(
			CbapPacketGapNs(pkt_size, effectiveRate));
	}else
		sendingTime = interframeGap +
			Seconds(DataRate(effectiveRate).CalculateTxTime(pkt_size));
	if (m_appCapTrace && qp->m_appRateCapBps > 0){
		uint64_t now = Simulator::Now().GetTimeStep();
		// One line per cap-limited flow per epoch, not per packet.
		if (now >= qp->cbap.appCapTraceNextNs){
			qp->cbap.appCapTraceNextNs = now + 1000000;   // 1ms
			std::cout << "APP_CAP t=" << now
				<< " sip=" << qp->sip << " dip=" << qp->dip
				<< " rate_bound=" << (m_rateBound ? 1 : 0)
				<< " controller_bps=" << (m_rateBound ?
					qp->m_rate.GetBitRate() : qp->m_max_rate.GetBitRate())
				<< " app_cap_bps=" << qp->m_appRateCapBps
				<< " effective_bps=" << effectiveRate
				<< std::endl;
		}
	}
	qp->m_nextAvail = Simulator::Now() + sendingTime;
}

void RdmaHw::ChangeRate(Ptr<RdmaQueuePair> qp, DataRate new_rate){
	if (qp->m_appRateCapBps > 0 &&
			new_rate.GetBitRate() > qp->m_appRateCapBps)
		new_rate = DataRate(qp->m_appRateCapBps);
	#if 1
	if (qp->cbap.enabled){
		Time next = Simulator::Now();
		if (qp->cbap.lastTxTimeNs > 0 && qp->lastPktSize > 0){
			Time paced = NanoSeconds(qp->cbap.lastTxTimeNs) +
				(qp->cbap.exactGrantPacing ? NanoSeconds(
					CbapPacketGapNs(qp->lastPktSize,
						new_rate.GetBitRate())) : Seconds(
					new_rate.CalculateTxTime(qp->lastPktSize)));
			if (paced > next)
				next = paced;
		}
		// An active startup-credit gate may have already established a
		// later token-eligibility time.  Emergency rate changes must not
		// move that gate earlier.
		if (qp->cbap.creditGateActive && qp->m_nextAvail > next)
			next = qp->m_nextAvail;
		qp->m_nextAvail = next;
	}else{
		Time sendingTime = Seconds(
			qp->m_rate.CalculateTxTime(qp->lastPktSize));
		Time new_sendintTime = Seconds(
			new_rate.CalculateTxTime(qp->lastPktSize));
		qp->m_nextAvail = qp->m_nextAvail +
			new_sendintTime - sendingTime;
	}
	// update nic's next avail event
	uint32_t nic_idx = GetNicIdxOfQp(qp);
	m_nic[nic_idx].dev->UpdateNextAvail(qp->m_nextAvail);
	#endif

	// change to new rate
	qp->m_rate = new_rate;
}

#define PRINT_LOG 0
/******************************
 * Mellanox's version of DCQCN
 *****************************/
void RdmaHw::RecordCbapObservedCnp(Ptr<RdmaQueuePair> q)
{
	if (!q || (!q->cbap.handoffEnabled && !q->cbap.delegationEnabled) ||
			q->cbap.handedOff || q->cbap.delegatedEnvelope)
		return;
	q->cbap.cbapCnpObserved = true;
	q->cbap.lastCbapCnpNs = Simulator::Now().GetTimeStep();
}

void RdmaHw::RecordFirstDcqcnUpdate(Ptr<RdmaQueuePair> q, bool cnp)
{
	if (!q || !((q->cbap.handoffEnabled && q->cbap.handedOff &&
			q->cbap.phase == RdmaQueuePair::CBAP_BASE_CC) ||
		(q->cbap.delegationEnabled && q->cbap.delegatedEnvelope &&
			q->cbap.phase == RdmaQueuePair::CBAP_DELEGATED_ENVELOPE)))
		return;
	uint64_t now = Simulator::Now().GetTimeStep();
	CbapHandoffBatchRecord &batch =
		s_cbapHandoffBatches[q->cbap.batchId];
	if (cnp && q->cbap.firstDcqcnCnpNs == 0){
		q->cbap.firstDcqcnCnpNs = now;
		if (batch.firstDcqcnCnpNs == 0 || now < batch.firstDcqcnCnpNs)
			batch.firstDcqcnCnpNs = now;
	}
	if (q->cbap.firstDcqcnRateUpdateNs == 0){
		q->cbap.firstDcqcnRateUpdateNs = now;
		if (batch.firstDcqcnRateUpdateNs == 0 ||
				now < batch.firstDcqcnRateUpdateNs)
			batch.firstDcqcnRateUpdateNs = now;
	}
	CbapControllerOwnershipRecord owner = {};
	owner.timeNs = now;
	owner.epoch = s_cbapEpoch;
	owner.batchId = q->cbap.batchId;
	owner.flowId = q->crfm.flowId;
	owner.phase = q->cbap.phase;
	owner.owner = "DCQCN";
	owner.cbapRateUpdate = false;
	owner.dcqcnRateUpdate = true;
	s_cbapControllerOwnershipRecords.push_back(owner);
}

bool RdmaHw::IsGuardedDelegated(Ptr<RdmaQueuePair> q) const
{
	return q && m_cc_mode == CC_MODE_CBAP_FULL_GUARDED_DELEGATION &&
		q->cbap.delegationEnabled && q->cbap.delegatedEnvelope &&
		q->cbap.phase == RdmaQueuePair::CBAP_DELEGATED_ENVELOPE;
}

uint64_t RdmaHw::GetDcqcnDesiredOrAppliedRate(Ptr<RdmaQueuePair> q) const
{
	return IsGuardedDelegated(q) ? q->cbap.dcqcnDesiredRateBps :
		q->m_rate.GetBitRate();
}

void RdmaHw::SetDcqcnDesiredOrAppliedRate(Ptr<RdmaQueuePair> q,
		uint64_t rateBps, bool decrease, bool positiveIncrease)
{
	if (!IsGuardedDelegated(q)){
		q->m_rate = DataRate(rateBps);
		return;
	}
	uint64_t now = Simulator::Now().GetTimeStep();
	if (positiveIncrease && q->cbap.envelopeBound){
		q->cbap.positiveAiSuppressed++;
		return;
	}
	q->cbap.dcqcnDesiredRateBps = std::min(rateBps,
		q->m_max_rate.GetBitRate());
	q->cbap.desiredRateLastUpdateNs = now;
	if (decrease)
		q->cbap.decreaseApplied++;
	CbapControllerOwnershipRecord owner = {};
	owner.timeNs = now; owner.epoch = s_cbapEpoch;
	owner.batchId = q->cbap.batchId; owner.flowId = q->crfm.flowId;
	owner.phase = q->cbap.phase; owner.owner = "DCQCN_DESIRED";
	owner.cbapRateUpdate = false; owner.dcqcnRateUpdate = true;
	s_cbapControllerOwnershipRecords.push_back(owner);
}

void RdmaHw::UpdateAlphaMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	//std::cout << Simulator::Now() << " alpha update:" << m_node->GetId() << ' ' << q->mlx.m_alpha << ' ' << (int)q->mlx.m_alpha_cnp_arrived << '\n';
	//printf("%lu alpha update: %08x %08x %u %u %.6lf->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_alpha);
	#endif
	if (q->mlx.m_alpha_cnp_arrived){
		q->mlx.m_alpha = (1 - m_g)*q->mlx.m_alpha + m_g; 	//binary feedback
	}else {
		q->mlx.m_alpha = (1 - m_g)*q->mlx.m_alpha; 	//binary feedback
	}
	#if PRINT_LOG
	//printf("%.6lf\n", q->mlx.m_alpha);
	#endif
	q->mlx.m_alpha_cnp_arrived = false; // clear the CNP_arrived bit
	ScheduleUpdateAlphaMlx(q);
}
void RdmaHw::ScheduleUpdateAlphaMlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_eventUpdateAlpha = Simulator::Schedule(MicroSeconds(m_alpha_resume_interval), &RdmaHw::UpdateAlphaMlx, this, q);
}

void RdmaHw::cnp_received_mlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_alpha_cnp_arrived = true; // set CNP_arrived bit for alpha update
	q->mlx.m_decrease_cnp_arrived = true; // set CNP_arrived bit for rate decrease
	if (q->mlx.m_first_cnp){
		RecordFirstDcqcnUpdate(q, true);
		// init alpha
		q->mlx.m_alpha = 1;
		q->mlx.m_alpha_cnp_arrived = false;
		// schedule alpha update
		ScheduleUpdateAlphaMlx(q);
		// schedule rate decrease
		ScheduleDecreaseRateMlx(q, 1); // add 1 ns to make sure rate decrease is after alpha update
		// set rate on first CNP
		if (IsGuardedDelegated(q)){
			uint64_t current = q->cbap.dcqcnDesiredRateBps;
			uint64_t reduced = (uint64_t)std::floor(m_rateOnFirstCNP * current);
			q->mlx.m_targetRate = DataRate(reduced);
			SetDcqcnDesiredOrAppliedRate(q, reduced, true, false);
		}else{
			// Frozen original Mellanox/DCQCN statement.
			q->mlx.m_targetRate = q->m_rate = m_rateOnFirstCNP * q->m_rate;
		}
		q->mlx.m_first_cnp = false;
	}
}

void RdmaHw::CheckRateDecreaseMlx(Ptr<RdmaQueuePair> q){
	ScheduleDecreaseRateMlx(q, 0);
	if (q->mlx.m_decrease_cnp_arrived){
		RecordFirstDcqcnUpdate(q, false);
		#if PRINT_LOG
		printf("%lu rate dec: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
		#endif
		bool clamp = true;
		if (!m_EcnClampTgtRate){
			if (q->mlx.m_rpTimeStage == 0)
				clamp = false;
		}
		if (IsGuardedDelegated(q)){
			uint64_t current = q->cbap.dcqcnDesiredRateBps;
			if (clamp) q->mlx.m_targetRate = DataRate(current);
			uint64_t reduced = std::max(m_minRate.GetBitRate(),
				(uint64_t)std::floor(current * (1 - q->mlx.m_alpha / 2)));
			SetDcqcnDesiredOrAppliedRate(q, reduced, true, false);
		}else{
			// Frozen original Mellanox/DCQCN statements.
			if (clamp) q->mlx.m_targetRate = q->m_rate;
			q->m_rate = std::max(m_minRate,
				q->m_rate * (1 - q->mlx.m_alpha / 2));
		}
		// reset rate increase related things
		q->mlx.m_rpTimeStage = 0;
		q->mlx.m_decrease_cnp_arrived = false;
		Simulator::Cancel(q->mlx.m_rpTimer);
		q->mlx.m_rpTimer = Simulator::Schedule(MicroSeconds(m_rpgTimeReset), &RdmaHw::RateIncEventTimerMlx, this, q);
		#if PRINT_LOG
		printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
		#endif
	}
}
void RdmaHw::ScheduleDecreaseRateMlx(Ptr<RdmaQueuePair> q, uint32_t delta){
	q->mlx.m_eventDecreaseRate = Simulator::Schedule(MicroSeconds(m_rateDecreaseInterval) + NanoSeconds(delta), &RdmaHw::CheckRateDecreaseMlx, this, q);
}

void RdmaHw::RateIncEventTimerMlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_rpTimer = Simulator::Schedule(MicroSeconds(m_rpgTimeReset), &RdmaHw::RateIncEventTimerMlx, this, q);
	RecordFirstDcqcnUpdate(q, false);
	uint64_t before = q->m_rate.GetBitRate();
	RateIncEventMlx(q);
	uint64_t after = q->m_rate.GetBitRate();
	if (q->cbap.v20Enabled && q->cbap.handedOff &&
			q->cbap.phase == RdmaQueuePair::CBAP_BASE_CC_ONLY &&
			after > 0 && after != before){
		// Native DCQCN updates its rate in place.  Ordinarily the next
		// packet naturally observes that new rate.  A zero-budget CBAP
		// startup can instead leave the sole send event paced at the former
		// 1-bps grant, so explicitly refresh only that v2.0-owned schedule.
		// RateIncEventMlx above remains the only rate-decision logic.  In
		// particular, its integer fast-recovery may transiently produce zero
		// from a 1-bps inherited rate; zero has no finite pacing interval, so
		// wait for a later native positive increase before rescheduling.
		ChangeRate(q, DataRate(after));
		uint32_t nic = GetNicIdxOfQp(q);
		m_nic[nic].dev->InvalidateAndRescheduleRdma();
	}
	q->mlx.m_rpTimeStage++;
}
void RdmaHw::RateIncEventMlx(Ptr<RdmaQueuePair> q){
	// check which increase phase: fast recovery, active increase, hyper increase
	if (q->mlx.m_rpTimeStage < m_rpgThreshold){ // fast recovery
		FastRecoveryMlx(q);
	}else if (q->mlx.m_rpTimeStage == m_rpgThreshold){ // active increase
		ActiveIncreaseMlx(q);
	}else { // hyper increase
		HyperIncreaseMlx(q);
	}
}

void RdmaHw::FastRecoveryMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu fast recovery: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	if (IsGuardedDelegated(q)){
		uint64_t current = q->cbap.dcqcnDesiredRateBps;
		uint64_t candidate = current / 2 +
			q->mlx.m_targetRate.GetBitRate() / 2;
		SetDcqcnDesiredOrAppliedRate(q, candidate, candidate < current,
			candidate > current);
	}else{
		// Frozen original Mellanox/DCQCN statement.
		q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	}
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}
void RdmaHw::ActiveIncreaseMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu active inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	if (IsGuardedDelegated(q) && q->cbap.envelopeBound){
		q->cbap.positiveAiSuppressed++;
		return;
	}
	// get NIC
	uint32_t nic_idx = GetNicIdxOfQp(q);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	// increate rate
	q->mlx.m_targetRate += m_rai;
	if (q->mlx.m_targetRate > dev->GetDataRate())
		q->mlx.m_targetRate = dev->GetDataRate();
	if (IsGuardedDelegated(q)){
		uint64_t current = q->cbap.dcqcnDesiredRateBps;
		uint64_t candidate = current / 2 +
			q->mlx.m_targetRate.GetBitRate() / 2;
		SetDcqcnDesiredOrAppliedRate(q, candidate, false, true);
	}else{
		// Frozen original Mellanox/DCQCN statement.
		q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	}
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}
void RdmaHw::HyperIncreaseMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu hyper inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	if (IsGuardedDelegated(q) && q->cbap.envelopeBound){
		q->cbap.positiveAiSuppressed++;
		return;
	}
	// get NIC
	uint32_t nic_idx = GetNicIdxOfQp(q);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	// increate rate
	q->mlx.m_targetRate += m_rhai;
	if (q->mlx.m_targetRate > dev->GetDataRate())
		q->mlx.m_targetRate = dev->GetDataRate();
	if (IsGuardedDelegated(q)){
		uint64_t current = q->cbap.dcqcnDesiredRateBps;
		uint64_t candidate = current / 2 +
			q->mlx.m_targetRate.GetBitRate() / 2;
		SetDcqcnDesiredOrAppliedRate(q, candidate, false, true);
	}else{
		// Frozen original Mellanox/DCQCN statement.
		q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	}
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}

/***********************
 * High Precision CC
 ***********************/
void RdmaHw::HandleAckHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	// update rate
	if (ack_seq > qp->hp.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
		UpdateRateHp(qp, p, ch, false);
	}else{ // do fast react
		FastReactHp(qp, p, ch);
	}
}

void RdmaHw::UpdateRateHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react){
	uint32_t next_seq = qp->snd_nxt;
	bool print = !fast_react || true;
	if (qp->hp.m_lastUpdateSeq == 0){ // first RTT
		qp->hp.m_lastUpdateSeq = next_seq;
		// store INT
		IntHeader &ih = ch.ack.ih;
		NS_ASSERT(ih.nhop <= IntHeader::maxHop);
		for (uint32_t i = 0; i < ih.nhop; i++)
			qp->hp.hop[i] = ih.hop[i];
		#if PRINT_LOG
		if (print){
			printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(), fast_react? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
			for (uint32_t i = 0; i < ih.nhop; i++)
				printf(" %u %lu %lu", ih.hop[i].GetQlen(), ih.hop[i].GetBytes(), ih.hop[i].GetTime());
			printf("\n");
		}
		#endif
	}else {
		// check packet INT
		IntHeader &ih = ch.ack.ih;
		if (ih.nhop <= IntHeader::maxHop){
			double max_c = 0;
			bool inStable = false;
			#if PRINT_LOG
			if (print)
				printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(), fast_react? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
			#endif
			// check each hop
			double U = 0;
			uint64_t dt = 0;
			bool updated[IntHeader::maxHop] = {false}, updated_any = false;
			NS_ASSERT(ih.nhop <= IntHeader::maxHop);
			for (uint32_t i = 0; i < ih.nhop; i++){
				if (m_sampleFeedback){
					if (ih.hop[i].GetQlen() == 0 && fast_react)
						continue;
				}
				updated[i] = updated_any = true;
				#if PRINT_LOG
				if (print)
					printf(" %u(%u) %lu(%lu) %lu(%lu)", ih.hop[i].GetQlen(), qp->hp.hop[i].GetQlen(), ih.hop[i].GetBytes(), qp->hp.hop[i].GetBytes(), ih.hop[i].GetTime(), qp->hp.hop[i].GetTime());
				#endif
				uint64_t tau = ih.hop[i].GetTimeDelta(qp->hp.hop[i]);;
				double duration = tau * 1e-9;
				double txRate = (ih.hop[i].GetBytesDelta(qp->hp.hop[i])) * 8 / duration;
				double u = txRate / ih.hop[i].GetLineRate() + (double)std::min(ih.hop[i].GetQlen(), qp->hp.hop[i].GetQlen()) * qp->m_max_rate.GetBitRate() / ih.hop[i].GetLineRate() /qp->m_win;
				#if PRINT_LOG
				if (print)
					printf(" %.3lf %.3lf", txRate, u);
				#endif
				if (!m_multipleRate){
					// for aggregate (single R)
					if (u > U){
						U = u;
						dt = tau;
					}
				}else {
					// for per hop (per hop R)
					if (tau > qp->m_baseRtt)
						tau = qp->m_baseRtt;
					qp->hp.hopState[i].u = (qp->hp.hopState[i].u * (qp->m_baseRtt - tau) + u * tau) / double(qp->m_baseRtt);
				}
				qp->hp.hop[i] = ih.hop[i];
			}

			DataRate new_rate;
			int32_t new_incStage;
			DataRate new_rate_per_hop[IntHeader::maxHop];
			int32_t new_incStage_per_hop[IntHeader::maxHop];
			if (!m_multipleRate){
				// for aggregate (single R)
				if (updated_any){
					if (dt > qp->m_baseRtt)
						dt = qp->m_baseRtt;
					qp->hp.u = (qp->hp.u * (qp->m_baseRtt - dt) + U * dt) / double(qp->m_baseRtt);
					max_c = qp->hp.u / m_targetUtil;

					if (max_c >= 1 || qp->hp.m_incStage >= m_miThresh){
						new_rate = qp->hp.m_curRate / max_c + m_rai;
						new_incStage = 0;
					}else{
						new_rate = qp->hp.m_curRate + m_rai;
						new_incStage = qp->hp.m_incStage+1;
					}
					if (new_rate < m_minRate)
						new_rate = m_minRate;
					if (new_rate > qp->m_max_rate)
						new_rate = qp->m_max_rate;
					#if PRINT_LOG
					if (print)
						printf(" u=%.6lf U=%.3lf dt=%u max_c=%.3lf", qp->hp.u, U, dt, max_c);
					#endif
					#if PRINT_LOG
					if (print)
						printf(" rate:%.3lf->%.3lf\n", qp->hp.m_curRate.GetBitRate()*1e-9, new_rate.GetBitRate()*1e-9);
					#endif
				}
			}else{
				// for per hop (per hop R)
				new_rate = qp->m_max_rate;
				for (uint32_t i = 0; i < ih.nhop; i++){
					if (updated[i]){
						double c = qp->hp.hopState[i].u / m_targetUtil;
						if (c >= 1 || qp->hp.hopState[i].incStage >= m_miThresh){
							new_rate_per_hop[i] = qp->hp.hopState[i].Rc / c + m_rai;
							new_incStage_per_hop[i] = 0;
						}else{
							new_rate_per_hop[i] = qp->hp.hopState[i].Rc + m_rai;
							new_incStage_per_hop[i] = qp->hp.hopState[i].incStage+1;
						}
						// bound rate
						if (new_rate_per_hop[i] < m_minRate)
							new_rate_per_hop[i] = m_minRate;
						if (new_rate_per_hop[i] > qp->m_max_rate)
							new_rate_per_hop[i] = qp->m_max_rate;
						// find min new_rate
						if (new_rate_per_hop[i] < new_rate)
							new_rate = new_rate_per_hop[i];
						#if PRINT_LOG
						if (print)
							printf(" [%u]u=%.6lf c=%.3lf", i, qp->hp.hopState[i].u, c);
						#endif
						#if PRINT_LOG
						if (print)
							printf(" %.3lf->%.3lf", qp->hp.hopState[i].Rc.GetBitRate()*1e-9, new_rate.GetBitRate()*1e-9);
						#endif
					}else{
						if (qp->hp.hopState[i].Rc < new_rate)
							new_rate = qp->hp.hopState[i].Rc;
					}
				}
				#if PRINT_LOG
				printf("\n");
				#endif
			}
			if (updated_any)
				ChangeRate(qp, new_rate);
			if (!fast_react){
				if (updated_any){
					qp->hp.m_curRate = new_rate;
					qp->hp.m_incStage = new_incStage;
				}
				if (m_multipleRate){
					// for per hop (per hop R)
					for (uint32_t i = 0; i < ih.nhop; i++){
						if (updated[i]){
							qp->hp.hopState[i].Rc = new_rate_per_hop[i];
							qp->hp.hopState[i].incStage = new_incStage_per_hop[i];
						}
					}
				}
			}
		}
		if (!fast_react){
			if (next_seq > qp->hp.m_lastUpdateSeq)
				qp->hp.m_lastUpdateSeq = next_seq; //+ rand() % 2 * m_mtu;
		}
	}
}

void RdmaHw::FastReactHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	if (m_fast_react)
		UpdateRateHp(qp, p, ch, true);
}

/**********************
 * TIMELY
 *********************/
void RdmaHw::HandleAckTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	// update rate
	if (ack_seq > qp->tmly.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
		UpdateRateTimely(qp, p, ch, false);
	}else{ // do fast react
		FastReactTimely(qp, p, ch);
	}
}
void RdmaHw::UpdateRateTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool us){
	uint32_t next_seq = qp->snd_nxt;
	uint64_t rtt = Simulator::Now().GetTimeStep() - ch.ack.ih.ts;
	bool print = !us;
	if (qp->tmly.m_lastUpdateSeq != 0){ // not first RTT
		int64_t new_rtt_diff = (int64_t)rtt - (int64_t)qp->tmly.lastRtt;
		double rtt_diff = (1 - m_tmly_alpha) * qp->tmly.rttDiff + m_tmly_alpha * new_rtt_diff;
		double gradient = rtt_diff / m_tmly_minRtt;
		bool inc = false;
		double c = 0;
		#if PRINT_LOG
		if (print)
			printf("%lu node:%u rtt:%lu rttDiff:%.0lf gradient:%.3lf rate:%.3lf", Simulator::Now().GetTimeStep(), m_node->GetId(), rtt, rtt_diff, gradient, qp->tmly.m_curRate.GetBitRate() * 1e-9);
		#endif
		if (rtt < m_tmly_TLow){
			inc = true;
		}else if (rtt > m_tmly_THigh){
			c = 1 - m_tmly_beta * (1 - (double)m_tmly_THigh / rtt);
			inc = false;
		}else if (gradient <= 0){
			inc = true;
		}else{
			c = 1 - m_tmly_beta * gradient;
			if (c < 0)
				c = 0;
			inc = false;
		}
		if (inc){
			if (qp->tmly.m_incStage < 5){
				qp->m_rate = qp->tmly.m_curRate + m_rai;
			}else{
				qp->m_rate = qp->tmly.m_curRate + m_rhai;
			}
			if (qp->m_rate > qp->m_max_rate)
				qp->m_rate = qp->m_max_rate;
			if (!us){
				qp->tmly.m_curRate = qp->m_rate;
				qp->tmly.m_incStage++;
				qp->tmly.rttDiff = rtt_diff;
			}
		}else{
			qp->m_rate = std::max(m_minRate, qp->tmly.m_curRate * c); 
			if (!us){
				qp->tmly.m_curRate = qp->m_rate;
				qp->tmly.m_incStage = 0;
				qp->tmly.rttDiff = rtt_diff;
			}
		}
		#if PRINT_LOG
		if (print){
			printf(" %c %.3lf\n", inc? '^':'v', qp->m_rate.GetBitRate() * 1e-9);
		}
		#endif
	}
	if (!us && next_seq > qp->tmly.m_lastUpdateSeq){
		qp->tmly.m_lastUpdateSeq = next_seq;
		// update
		qp->tmly.lastRtt = rtt;
	}
}
void RdmaHw::FastReactTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
}

/************************
 * Cross-round feedback
 ************************/
void RdmaHw::RecordRoundAckCompletion(Ptr<RdmaQueuePair> qp){
	uint64_t now = Simulator::Now().GetTimeStep();
	for (uint32_t i = 0; i < qp->crfm.rounds.size(); ++i){
		RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[i];
		if (round.ackCompletionTimeNs == 0 && qp->snd_una >= round.endSeq){
			round.ackCompletionTimeNs = now;
			round.endRate = qp->m_rate.GetBitRate();
			round.dcqcnEndAlpha = qp->mlx.m_alpha;
			round.dcqcnEndRecoveryStage = qp->mlx.m_rpTimeStage;
			qp->crfm.lastCompletedRound = i;
			NS_ASSERT_MSG((int32_t)i == qp->crfm.currentRoundIndex,
					"ACK completed a round other than the current round");
			NotifyRoundGroupAck(qp, i, now);
		}
	}
}

RdmaHw::HpFeedbackEstimate RdmaHw::EvaluateHpFeedback(
		Ptr<RdmaQueuePair> qp, CustomHeader &ch, bool fastReact,
		RdmaQueuePair::CrfmRoundState &round) const {
	HpFeedbackEstimate estimate;
	IntHeader &ih = ch.ack.ih;
	if (round.feedbackBaselineHops == 0 ||
			ih.nhop > IntHeader::maxHop ||
			ih.nhop != round.feedbackBaselineHops)
		return estimate;

	double maximumNormalized = 0;
	bool updatedAny = false;
	uint32_t bottleneckIndex = IntHeader::maxHop;
	if (!m_multipleRate){
		double maximumU = 0;
		uint64_t maximumDt = 0;
		for (uint32_t i = 0; i < ih.nhop; ++i){
			if (m_sampleFeedback && fastReact &&
					ih.hop[i].GetQlen() == 0)
				continue;
			uint64_t tau =
				ih.hop[i].GetTimeDelta(round.feedbackHop[i]);
			if (tau == 0 || ih.hop[i].GetLineRate() == 0)
				continue;
			double duration = tau * 1e-9;
			double txRate =
				ih.hop[i].GetBytesDelta(round.feedbackHop[i]) *
				8.0 / duration;
			double queueTerm = 0;
			if (qp->m_win > 0)
				queueTerm =
					(double)std::min(ih.hop[i].GetQlen(),
						round.feedbackHop[i].GetQlen()) *
					qp->m_max_rate.GetBitRate() /
					ih.hop[i].GetLineRate() / qp->m_win;
			double utilization =
				txRate / ih.hop[i].GetLineRate() + queueTerm;
			if (!updatedAny || utilization > maximumU ||
					(utilization == maximumU &&
					 ih.hop[i].GetQlen() >
					 ih.hop[bottleneckIndex].GetQlen())){
				maximumU = utilization;
				maximumDt = tau;
				bottleneckIndex = i;
			}
			updatedAny = true;
		}
		if (!updatedAny)
			return estimate;
		if (maximumDt > qp->m_baseRtt)
			maximumDt = qp->m_baseRtt;
		double smoothed = qp->m_baseRtt > 0 ?
			(qp->hp.u * (qp->m_baseRtt - maximumDt) +
			 maximumU * maximumDt) / qp->m_baseRtt : maximumU;
		maximumNormalized = smoothed / m_targetUtil;
	}else{
		for (uint32_t i = 0; i < ih.nhop; ++i){
			if (m_sampleFeedback && fastReact &&
					ih.hop[i].GetQlen() == 0)
				continue;
			uint64_t tau =
				ih.hop[i].GetTimeDelta(round.feedbackHop[i]);
			if (tau == 0 || ih.hop[i].GetLineRate() == 0)
				continue;
			double duration = tau * 1e-9;
			double txRate =
				ih.hop[i].GetBytesDelta(round.feedbackHop[i]) *
				8.0 / duration;
			double queueTerm = 0;
			if (qp->m_win > 0)
				queueTerm =
					(double)std::min(ih.hop[i].GetQlen(),
						round.feedbackHop[i].GetQlen()) *
					qp->m_max_rate.GetBitRate() /
					ih.hop[i].GetLineRate() / qp->m_win;
			double utilization =
				txRate / ih.hop[i].GetLineRate() + queueTerm;
			if (tau > qp->m_baseRtt)
				tau = qp->m_baseRtt;
			double smoothed = qp->m_baseRtt > 0 ?
				(qp->hp.hopState[i].u * (qp->m_baseRtt - tau) +
				 utilization * tau) / qp->m_baseRtt : utilization;
			double normalized = smoothed / m_targetUtil;
			if (!updatedAny || normalized > maximumNormalized ||
					(normalized == maximumNormalized &&
					 ih.hop[i].GetQlen() >
					 ih.hop[bottleneckIndex].GetQlen())){
				maximumNormalized = normalized;
				bottleneckIndex = i;
			}
			updatedAny = true;
		}
		if (!updatedAny)
			return estimate;
	}
	if (bottleneckIndex >= ih.nhop)
		return estimate;
	uint64_t now = Simulator::Now().GetTimeStep();
	uint64_t modulus = (uint64_t)1 << IntHop::timeWidth;
	uint64_t sample = (now / modulus) * modulus +
		ih.hop[bottleneckIndex].GetTime();
	if (sample > now)
		sample -= modulus;
	estimate.valid = std::isfinite(maximumNormalized) &&
		ih.hop[bottleneckIndex].GetLineRate() > 0;
	estimate.normalizedLoad = maximumNormalized;
	estimate.maximumQueueBytes =
		ih.hop[bottleneckIndex].GetQlen();
	estimate.bottleneckCapacityBps =
		ih.hop[bottleneckIndex].GetLineRate();
	estimate.bottleneckSampleTimeNs = sample;
	return estimate;
}

void RdmaHw::HandleAckCrfm(Ptr<RdmaQueuePair> qp, Ptr<Packet> p,
		CustomHeader &ch){
	if (ch.ack.seq == 0)
		return;
	int32_t origin = qp->GetRoundIndexForSequence(ch.ack.seq - 1);
	if (origin < 0 || (uint32_t)origin >= qp->crfm.rounds.size())
		return;
	RdmaQueuePair::CrfmRoundState &round = qp->crfm.rounds[origin];
	uint32_t classification = RdmaQueuePair::CRFM_FEEDBACK_NONE;
	if (origin == qp->crfm.currentRoundIndex &&
			qp->snd_nxt < round.endSeq)
		classification = RdmaQueuePair::CRFM_ACTIONABLE_CURRENT;
	else if (origin == qp->crfm.currentRoundIndex)
		classification = RdmaQueuePair::CRFM_LATE_SAME_ROUND;
	else if (origin < qp->crfm.currentRoundIndex)
		classification = RdmaQueuePair::CRFM_STALE_OLDER_ROUND;
	else
		return;

	qp->crfm.latestFeedbackOriginRound = origin;
	qp->crfm.latestFeedbackClass = classification;
	uint64_t now = Simulator::Now().GetTimeStep();
	round.totalFeedback++;
	if (round.firstFeedbackTimeNs == 0)
		round.firstFeedbackTimeNs = now;
	round.lastFeedbackTimeNs = now;
	if (classification == RdmaQueuePair::CRFM_ACTIONABLE_CURRENT)
		round.actionableFeedback++;
	else if (classification == RdmaQueuePair::CRFM_LATE_SAME_ROUND)
		round.lateSameRoundFeedback++;
	else
		round.staleOlderRoundFeedback++;
	if (classification == RdmaQueuePair::CRFM_LATE_SAME_ROUND &&
			round.injectionEndTimeNs > 0 &&
			now >= round.injectionEndTimeNs)
		round.feedbackDuringOff++;

	uint64_t remainingBytes = round.endSeq > qp->snd_nxt ?
		round.endSeq - qp->snd_nxt : 0;
	double remaining = round.roundBytes > 0 ?
		(double)remainingBytes / round.roundBytes : 0;
	round.remainingUnsentRatioSum += remaining;
	round.minimumRemainingUnsentRatio =
		std::min(round.minimumRemainingUnsentRatio, remaining);
	round.remainingUnsentBytesSum += remainingBytes;
	if (round.totalFeedback == 1)
		round.minimumRemainingUnsentBytes = remainingBytes;
	else
		round.minimumRemainingUnsentBytes = std::min(
			round.minimumRemainingUnsentBytes, remainingBytes);

	bool fastReact = ch.ack.seq <= qp->hp.m_lastUpdateSeq;
	HpFeedbackEstimate estimate =
		EvaluateHpFeedback(qp, ch, fastReact, round);
	if (ch.ack.ih.nhop <= IntHeader::maxHop){
		round.feedbackBaselineHops = ch.ack.ih.nhop;
		for (uint32_t i = 0; i < ch.ack.ih.nhop; ++i)
			round.feedbackHop[i] = ch.ack.ih.hop[i];
	}
	if (estimate.valid){
		round.maximumNormalizedLoad = std::max(
			round.maximumNormalizedLoad, estimate.normalizedLoad);
		round.normalizedLoadSum += estimate.normalizedLoad;
		round.normalizedLoadSamples++;
			round.maximumQueueBytes = std::max(
				round.maximumQueueBytes, estimate.maximumQueueBytes);
			UpdateBopTelemetry(qp, origin, estimate, now);
			UpdateBopMultilinkTelemetry(qp, ch.ack.ih, now);
		}

	uint64_t before = qp->m_rate.GetBitRate();
	if (round.totalFeedback == 1)
		round.firstFeedbackRateBefore = before;
	bool executeHpcc = false;
	if (m_cc_mode == 3 ||
			m_cc_mode == CC_MODE_HPCC_ROUND_RESET){
		executeHpcc = true;
	}else if (m_cc_mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC &&
			qp->cbap.v20Enabled && qp->cbap.handedOff &&
			qp->cbap.phase == RdmaQueuePair::CBAP_BASE_CC_ONLY){
		// The first post-handoff ACK is handled by the unmodified HPCC
		// routine. During STARTUP_ADMISSION ACKs are diagnostic only.
		executeHpcc = true;
	}else if (m_cc_mode == CC_MODE_CRFM_GATE && classification ==
			RdmaQueuePair::CRFM_ACTIONABLE_CURRENT){
		executeHpcc = true;
	}else if (m_cc_mode == CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC){
		// Startup feedback updates the shared telemetry estimate only.
	}else if (classification ==
			RdmaQueuePair::CRFM_LATE_SAME_ROUND){
		qp->crfm.gatedLateUpdates++;
	}else{
		qp->crfm.gatedStaleUpdates++;
	}
	if (executeHpcc){
		HandleAckHp(qp, p, ch);
		qp->crfm.directHpccUpdates++;
	}
	uint64_t after = qp->m_rate.GetBitRate();
	round.lastFeedbackRateAfter = after;
	if (after != before){
		round.feedbackChangedLiveRate++;
		qp->crfm.rateTotalVariation +=
			std::fabs((double)after - before);
		qp->crfm.minimumRate = std::min(qp->crfm.minimumRate, after);
		qp->crfm.maximumRate = std::max(qp->crfm.maximumRate, after);
		if (classification == RdmaQueuePair::CRFM_LATE_SAME_ROUND)
			round.liveRateChangesDuringOff++;
	}
	if (qp->crfm.currentRoundIndex >= 0){
		RdmaQueuePair::CrfmRoundState &current =
			qp->crfm.rounds[qp->crfm.currentRoundIndex];
		current.minimumRate = std::min(current.minimumRate, after);
		current.endRate = after;
	}
}

/**********************
 * DCTCP
 *********************/
void RdmaHw::HandleAckDctcp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
	bool new_batch = false;

	// update alpha
	qp->dctcp.m_ecnCnt += (cnp > 0);
	if (ack_seq > qp->dctcp.m_lastUpdateSeq){ // if full RTT feedback is ready, do alpha update
		#if PRINT_LOG
		printf("%lu %s %08x %08x %u %u [%u,%u,%u] %.3lf->", Simulator::Now().GetTimeStep(), "alpha", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->dctcp.m_lastUpdateSeq, ch.ack.seq, qp->snd_nxt, qp->dctcp.m_alpha);
		#endif
		new_batch = true;
		if (qp->dctcp.m_lastUpdateSeq == 0){ // first RTT
			qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
			qp->dctcp.m_batchSizeOfAlpha = qp->snd_nxt / m_mtu + 1;
		}else {
			double frac = std::min(1.0, double(qp->dctcp.m_ecnCnt) / qp->dctcp.m_batchSizeOfAlpha);
			qp->dctcp.m_alpha = (1 - m_g) * qp->dctcp.m_alpha + m_g * frac;
			qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
			qp->dctcp.m_ecnCnt = 0;
			qp->dctcp.m_batchSizeOfAlpha = (qp->snd_nxt - ack_seq) / m_mtu + 1;
			#if PRINT_LOG
			printf("%.3lf F:%.3lf", qp->dctcp.m_alpha, frac);
			#endif
		}
		#if PRINT_LOG
		printf("\n");
		#endif
	}

	// check cwr exit
	if (qp->dctcp.m_caState == 1){
		if (ack_seq > qp->dctcp.m_highSeq)
			qp->dctcp.m_caState = 0;
	}

	// check if need to reduce rate: ECN and not in CWR
	if (cnp && qp->dctcp.m_caState == 0){
		#if PRINT_LOG
		printf("%lu %s %08x %08x %u %u %.3lf->", Simulator::Now().GetTimeStep(), "rate", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->m_rate.GetBitRate()*1e-9);
		#endif
		qp->m_rate = std::max(m_minRate, qp->m_rate * (1 - qp->dctcp.m_alpha / 2));
		#if PRINT_LOG
		printf("%.3lf\n", qp->m_rate.GetBitRate() * 1e-9);
		#endif
		qp->dctcp.m_caState = 1;
		qp->dctcp.m_highSeq = qp->snd_nxt;
	}

	// additive inc
	if (qp->dctcp.m_caState == 0 && new_batch)
		qp->m_rate = std::min(qp->m_max_rate, qp->m_rate + m_dctcp_rai);
}

/*********************
 * HPCC-PINT
 ********************/
void RdmaHw::SetPintSmplThresh(double p){
       pint_smpl_thresh = (uint32_t)(65536 * p);
}
void RdmaHw::HandleAckHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
       uint32_t ack_seq = ch.ack.seq;
       if (rand() % 65536 >= pint_smpl_thresh)
               return;
       // update rate
       if (ack_seq > qp->hpccPint.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
               UpdateRateHpPint(qp, p, ch, false);
       }else{ // do fast react
               UpdateRateHpPint(qp, p, ch, true);
       }
}

void RdmaHw::UpdateRateHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react){
       uint32_t next_seq = qp->snd_nxt;
       if (qp->hpccPint.m_lastUpdateSeq == 0){ // first RTT
               qp->hpccPint.m_lastUpdateSeq = next_seq;
       }else {
               // check packet INT
               IntHeader &ih = ch.ack.ih;
               double U = Pint::decode_u(ih.GetPower());

               DataRate new_rate;
               int32_t new_incStage;
               double max_c = U / m_targetUtil;

               if (max_c >= 1 || qp->hpccPint.m_incStage >= m_miThresh){
                       new_rate = qp->hpccPint.m_curRate / max_c + m_rai;
                       new_incStage = 0;
               }else{
                       new_rate = qp->hpccPint.m_curRate + m_rai;
                       new_incStage = qp->hpccPint.m_incStage+1;
               }
               if (new_rate < m_minRate)
                       new_rate = m_minRate;
               if (new_rate > qp->m_max_rate)
                       new_rate = qp->m_max_rate;
               ChangeRate(qp, new_rate);
               if (!fast_react){
                       qp->hpccPint.m_curRate = new_rate;
                       qp->hpccPint.m_incStage = new_incStage;
               }
               if (!fast_react){
                       if (next_seq > qp->hpccPint.m_lastUpdateSeq)
                               qp->hpccPint.m_lastUpdateSeq = next_seq; //+ rand() % 2 * m_mtu;
               }
       }
}

}
