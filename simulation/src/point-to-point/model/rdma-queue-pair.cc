#include <ns3/hash.h>
#include <ns3/uinteger.h>
#include <ns3/seq-ts-header.h>
#include <ns3/udp-header.h>
#include <ns3/ipv4-header.h>
#include <ns3/simulator.h>
#include "ns3/ppp-header.h"
#include "rdma-queue-pair.h"
#include <limits>

namespace ns3 {

RdmaQueuePair::CrfmRoundState::CrfmRoundState()
	: roundId(0), roundGroupId(0), participantCount(0),
	  jitterGroup(0), computeGapNs(0), jitterNs(0),
	  releaseTimeNs(0), roundBytes(0),
	  startSeq(0), endSeq(0), injectionEndTimeNs(0),
	  ackCompletionTimeNs(0), startRate(0), minimumRate(0), endRate(0),
	  nextRoundStartRate(0), selectedLinkPeakQueue(0), totalFeedback(0),
	  actionableFeedback(0), lateSameRoundFeedback(0),
	  staleOlderRoundFeedback(0), feedbackDuringOff(0),
	  liveRateChangesDuringOff(0), firstFeedbackTimeNs(0),
	  lastFeedbackTimeNs(0), remainingUnsentRatioSum(0),
	  minimumRemainingUnsentRatio(1.0), remainingUnsentBytesSum(0),
	  minimumRemainingUnsentBytes(0), maximumNormalizedLoad(0),
	  normalizedLoadSum(0), normalizedLoadSamples(0), maximumQueueBytes(0),
	  feedbackBaselineHops(0),
	  firstFeedbackRateBefore(0), lastFeedbackRateAfter(0),
	  feedbackChangedLiveRate(0), cnpCount(0), dcqcnStartAlpha(0),
	  dcqcnEndAlpha(0), dcqcnStartRecoveryStage(0),
	  dcqcnEndRecoveryStage(0), commonReleaseHintNs(0),
	  commonReleaseTimeNs(0), barrierCompletionTimeNs(0),
	  bopPlanApplied(false), bopSelectedRateBps(0), bopMaxRateBps(0),
	  bopPhaseOffsetNs(0), bopResidualQueueBytes(0),
	  bopBottleneckBps(0), bopBackgroundBps(0), bopTLineSeconds(0),
	  bopTLinkSeconds(0), bopTStarSeconds(0), bopFallbackReason(0),
	  bopQcBaseRateBps(0), bopQcCreditBytes(0), bopQcCreditEndSeq(0),
	  bopQcBurstRateBps(0), bopQcSwitchedToBase(false),
	  bopQcActualBurstBytes(0), bopQcQueueSampleAgeUs(0),
	  bopQcFeedbackTauUs(0), bopQcTauSource(0),
	  bopQcEcnThresholdBytes(0), bopQcPacketMarginBytes(0),
	  bopQcQueueRoomBytes(0), bopQcBdpCreditBytes(0),
	  bopQcGroupCreditBytes(0), bopQcTotalAllocatedCreditBytes(0),
	  bopQcFallbackReason(0),
	  bopQbBaseRateBps(0), bopQbCreditBytes(0), bopQbCreditEndSeq(0),
	  bopQbBurstRateBps(0), bopQbSwitchedToBase(false),
	  bopQbActualBurstBytes(0), bopQbEcnThresholdBytes(0),
	  bopQbQueueTargetBytes(0), bopQbPacketMarginBytes(0),
	  bopQbQueueRoomBytes(0), bopQbGroupCreditBytes(0),
	  bopQbTotalAllocatedCreditBytes(0), bopQbFallbackReason(0),
	  bopQbSafetyBoundValid(false), bopQbEstimatedQueueBytes(0),
	  bopQbActualQueueBytes(0), bopQbQueueErrorBytes(0),
	  bopQbQueueErrorRatio(0), bopQbQueueSampleAgeUs(0),
	  bopQbQueueSampleOrigin(0), bopQbSafetyBoundUsingActual(false),
	  prtProbeCountSent(0), prtProbeReturnedBeforeRelease(0),
	  prtDecisionReleaseNs(0),
	  prtProbe1SendNs(0), prtProbe1QueueSampleNs(0), prtProbe1AckNs(0),
	  prtProbe1QueueBytes(0), prtProbe2SendNs(0),
	  prtProbe2QueueSampleNs(0), prtProbe2AckNs(0),
	  prtProbe2QueueBytes(0), prtQueueSlopeBytesPerNs(0),
	  prtQueueHatBytes(0), prtActualQueueBytes(0),
	  prtQueueErrorBytes(0), prtFallbackReason(0),
	  prtOriginalBopCreditBytes(0), prtCreditBytes(0),
	  prtPrimerEcn(0), prtCollectiveEcn(0),
	  bopQbMaxBaseRateBps(0), bopQbMaxCreditBytes(0),
	  bopQbMaxCreditEndSeq(0), bopQbMaxBurstRateBps(0),
	  bopQbMaxSwitchedToBase(false), bopQbMaxActualBurstBytes(0),
	  bopQbMaxQueueSampleTimeNs(0), bopQbMaxQueueSampleAgeUs(0),
	  bopQbMaxEcnThresholdBytes(0), bopQbMaxPacketMarginBytes(0),
	  bopQbMaxQueueRoomBytes(0), bopQbMaxGroupCreditBytes(0),
	  bopQbMaxTotalAllocatedCreditBytes(0),
	  bopQbMaxFallbackReason(0), bopQbMaxSafetyBoundValid(false),
	  groupQueueMaxBytes(0), groupEcnMarks(0), groupPfcEvents(0)
{
}

/**************************
 * RdmaQueuePair
 *************************/
TypeId RdmaQueuePair::GetTypeId (void)
{
	static TypeId tid = TypeId ("ns3::RdmaQueuePair")
		.SetParent<Object> ()
		;
	return tid;
}

RdmaQueuePair::RdmaQueuePair(uint16_t pg, Ipv4Address _sip, Ipv4Address _dip, uint16_t _sport, uint16_t _dport){
	startTime = Simulator::Now();
	sip = _sip;
	dip = _dip;
	sport = _sport;
	dport = _dport;
	m_size = 0;
	snd_nxt = snd_una = 0;
	m_pg = pg;
	m_ipid = 0;
	m_win = 0;
	m_baseRtt = 0;
	m_max_rate = 0;
	m_var_win = false;
	m_rate = 0;
	m_nextAvail = Time(0);
	lastPktSize = 0;
	mlx.m_alpha = 1;
	mlx.m_alpha_cnp_arrived = false;
	mlx.m_first_cnp = true;
	mlx.m_decrease_cnp_arrived = false;
	mlx.m_rpTimeStage = 0;
	hp.m_lastUpdateSeq = 0;
	for (uint32_t i = 0; i < sizeof(hp.keep) / sizeof(hp.keep[0]); i++)
		hp.keep[i] = 0;
	hp.m_incStage = 0;
	hp.m_lastGap = 0;
	hp.u = 1;
	for (uint32_t i = 0; i < IntHeader::maxHop; i++){
		hp.hopState[i].u = 1;
		hp.hopState[i].incStage = 0;
	}

	tmly.m_lastUpdateSeq = 0;
	tmly.m_incStage = 0;
	tmly.lastRtt = 0;
	tmly.rttDiff = 0;
	crfm.enabled = false;
	crfm.flowId = 0;
	crfm.releasedBytes = 0;
	crfm.currentRoundIndex = -1;
	crfm.lastCompletedRound = -1;
	crfm.latestFeedbackOriginRound = -1;
	crfm.latestFeedbackClass = CRFM_FEEDBACK_NONE;
	crfm.directHpccUpdates = 0;
	crfm.gatedLateUpdates = 0;
	crfm.gatedStaleUpdates = 0;
	crfm.rateTotalVariation = 0;
	crfm.minimumRate = 0;
	crfm.maximumRate = 0;
	crfm.bopTelemetryValid = false;
	crfm.bopTelemetryOriginRound = -1;
	crfm.bopLastQueueBytes = 0;
	crfm.bopLastSampleTimeNs = 0;
	crfm.bopLastArrivalTimeNs = 0;
	crfm.bopLastBottleneckBps = 0;
	crfm.bopQcTauValid = false;
	crfm.bopQcTauEwmaNs = 0;
	crfm.bopQcBaseRate = 0;
	crfm.bopQcCreditTotal = 0;
	crfm.bopQcCreditRemaining = 0;
	crfm.bopQcCreditEndSeq = 0;
	crfm.bopQcPhaseOffsetNs = 0;
	crfm.bopQcSwitchedToBase = false;
	crfm.bopQcSwitchPending = false;
	crfm.bopQcActualBurstBytes = 0;
	crfm.bopQbBaseRate = 0;
	crfm.bopQbCreditTotal = 0;
	crfm.bopQbCreditRemaining = 0;
	crfm.bopQbCreditEndSeq = 0;
	crfm.bopQbPhaseOffsetNs = 0;
	crfm.bopQbSwitchedToBase = false;
	crfm.bopQbSwitchPending = false;
	crfm.bopQbActualBurstBytes = 0;
	crfm.bopQbMaxBaseRate = 0;
	crfm.bopQbMaxCreditTotal = 0;
	crfm.bopQbMaxCreditRemaining = 0;
	crfm.bopQbMaxCreditEndSeq = 0;
	crfm.bopQbMaxPhaseOffsetNs = 0;
	crfm.bopQbMaxSwitchedToBase = false;
	crfm.bopQbMaxSwitchPending = false;
	crfm.bopQbMaxActualBurstBytes = 0;

	dctcp.m_lastUpdateSeq = 0;
	dctcp.m_caState = 0;
	dctcp.m_highSeq = 0;
	dctcp.m_alpha = 1;
	dctcp.m_ecnCnt = 0;
	dctcp.m_batchSizeOfAlpha = 0;

	hpccPint.m_lastUpdateSeq = 0;
	hpccPint.m_incStage = 0;
	cbap.enabled = false;
	cbap.fullCredit = false;
	cbap.initOnly = false;
	cbap.independentDiagnostic = false;
	cbap.batchId = 0;
	cbap.phase = CBAP_DISABLED;
	cbap.stableEpochCount = 0;
	cbap.increaseFreezeEpochs = 0;
	cbap.rootId = 0;
	cbap.lastRateDecisionEpoch = 0;
	cbap.lastDecreaseEpoch = 0;
	cbap.applicationReadyNs = 0;
	cbap.networkReleaseNs = 0;
	cbap.currentRateBps = 0;
	cbap.targetRateBps = 0;
	cbap.requestedRateBps = 0;
	cbap.admitRateBps = 0;
	cbap.baseRateBps = 0;
	cbap.creditInitialBytes = 0;
	cbap.creditRemainingBytes = 0;
	cbap.creditGateActive = false;
	cbap.creditRemainingAtAdmissionExit = 0;
	cbap.bytesSentAtRelease = 0;
	cbap.bytesAckedAtRelease = 0;
	cbap.lastTxTimeNs = 0;
	cbap.lastPacketSeq = 0;
	cbap.lastPacketWireBytes = 0;
	cbap.lastFreshFeedbackNs = 0;
	cbap.firstFreshFeedbackNs = 0;
	cbap.admissionEnterNs = 0;
	cbap.admissionExitNs = 0;
	cbap.firstDataTxNs = 0;
	cbap.firstPostReleaseSampleNs = 0;
	cbap.firstCompleteFreshFeedbackNs = 0;
	cbap.initialAdmitRateBps = 0;
	cbap.bytesSentBeforeFreshFeedback = 0;
	cbap.rateUpdatesBeforeFirstTx = 0;
	cbap.ordinaryRateUpdatesDuringAdmission = 0;
	cbap.emergencyRateUpdatesDuringAdmission = 0;
	cbap.creditGateEnterNs = 0;
	cbap.creditGateExitNs = 0;
	cbap.estimatedFirstFeedbackNs = 0;
	cbap.protectionFloorBps = 0;
	cbap.rebalanceStartNs = 0;
	cbap.rebalanceEndNs = 0;
	cbap.lastEpochSndNxt = 0;
	cbap.recentActualRateBps[0] = 0;
	cbap.recentActualRateBps[1] = 0;
	cbap.baseEligibilityLastNs = 0;
	cbap.baseEligibleBytes = 0;
	cbap.excessBytes = 0;
	cbap.capacityViolationCount = 0;
	cbap.creditViolationCount = 0;
	cbap.staleFeedbackCount = 0;
	cbap.rateIncreaseCount = 0;
	cbap.rateDecreaseCount = 0;
	cbap.rateHoldCount = 0;
	cbap.rescheduleCount = 0;
	cbap.firstFair80Ns = 0;
	cbap.firstFair90Ns = 0;
	cbap.firstFair95Ns = 0;
	cbap.trackingStartNs = 0;
	cbap.trackingBytesSent = 0;
	cbap.trackingRateLastNs = 0;
	cbap.trackingRateIntegral = 0;
	cbap.pacingViolationCount = 0;
	cbap.txTraceTrackingPackets = 0;
	cbap.exactGrantPacing = false;
	cbap.zeroGrantPaused = false;
	cbap.zeroGrantPauseCount = 0;
	cbap.zeroGrantResumeCount = 0;
	cbap.zeroGrantPauseStartNs = 0;
	cbap.zeroGrantPausedNs = 0;
	cbap.handoffEnabled = false;
	cbap.handedOff = false;
	cbap.cbapCnpObserved = false;
	cbap.lastCbapCnpNs = 0;
	cbap.handoffExecuteNs = 0;
	cbap.handoffRateBps = 0;
	cbap.handoffNextTxBeforeNs = 0;
	cbap.handoffNextTxAfterNs = 0;
	cbap.firstTxAfterHandoffNs = 0;
	cbap.firstDcqcnRateUpdateNs = 0;
	cbap.firstDcqcnCnpNs = 0;
	cbap.handoffFlowRecordIndex = std::numeric_limits<uint32_t>::max();
	cbap.delegationEnabled = false;
	cbap.delegatedEnvelope = false;
	cbap.delegationCount = 0;
	cbap.delegationExecuteNs = 0;
	cbap.dcqcnDesiredRateBps = 0;
	cbap.envelopeAppliedRateBps = 0;
	cbap.envelopeScale = 1.0;
	cbap.envelopeBound = false;
	cbap.desiredRateLastUpdateNs = 0;
	cbap.appliedRateLastUpdateNs = 0;
	cbap.positiveAiSuppressed = 0;
	cbap.decreaseApplied = 0;
	cbap.simulatorInternalRateWrites = 0;
	cbap.postDelegationFullGrantCount = 0;
	cbap.timeBelow90TargetNs = 0;
	cbap.timeBelow80TargetNs = 0;
	cbap.timeBelow50TargetNs = 0;
	cbap.incumbentAuditLastNs = 0;
	cbap.phaseAtLastPacket = CBAP_DISABLED;
	cbap.v20Enabled = false;
	cbap.v20Classification = 0;
	cbap.v20BaseCc = 0;
	cbap.v20BlindWindowNs = 0;
	cbap.v20LeaseExpiryNs = 0;
	cbap.v20FirstFreshFeedbackNs = 0;
	cbap.v20HandoffInitialRateBps = 0;
	cbap.v20PostHandoffCbapWriteCount = 0;
	cbap.v20CatchUpBurst = false;
	cbap.sbaEnabled = false;
	cbap.sbaLastAppliedRateBps = 0;
	cbap.sbaFirstFeedbackNs = 0;
	cbap.sbaHandoffCount = 0;
	cbap.sbaLeaseExpiryNs = 0;
	cbap.sbaLeaseExpiryCount = 0;
}

void RdmaQueuePair::SetSize(uint64_t size){
	m_size = size;
}

void RdmaQueuePair::SetWin(uint32_t win){
	m_win = win;
}

void RdmaQueuePair::SetBaseRtt(uint64_t baseRtt){
	m_baseRtt = baseRtt;
}

void RdmaQueuePair::SetVarWin(bool v){
	m_var_win = v;
}

void RdmaQueuePair::SetAppNotifyCallback(Callback<void> notifyAppFinish){
	m_notifyAppFinish = notifyAppFinish;
}

uint64_t RdmaQueuePair::GetBytesLeft(){
	uint64_t limit = crfm.enabled ? crfm.releasedBytes : m_size;
	if (limit > m_size)
		limit = m_size;
	uint64_t remaining = limit >= snd_nxt ? limit - snd_nxt : 0;
	if (remaining == 0 || !cbap.enabled || !cbap.fullCredit ||
			!cbap.creditGateActive ||
			cbap.phase != CBAP_ADMISSION_HOLD)
		return remaining;
	UpdateCbapEligibility(Simulator::Now().GetTimeStep());
	uint64_t payload = std::min((uint64_t)1000, remaining);
	// CBAP DATA uses no INT.  The current repository's DATA framing is
	// payload plus PPP/IPv4/UDP/SeqTs; use a conservative 64-byte allowance
	// so the scheduler never admits a packet on optimistic byte accounting.
	uint64_t wire = payload + 64;
	long double available = cbap.baseEligibleBytes +
		cbap.creditRemainingBytes;
	if (available + 1e-9L < wire && cbap.baseRateBps > 0){
		long double missing = wire - available;
		uint64_t waitNs = (uint64_t)std::ceil(
			missing * 8.0e9L / cbap.baseRateBps);
		Time eligible = NanoSeconds(Simulator::Now().GetTimeStep() +
			std::max((uint64_t)1, waitNs));
		if (m_nextAvail < eligible)
			m_nextAvail = eligible;
	}
	return remaining;
}

void RdmaQueuePair::UpdateCbapEligibility(uint64_t nowNs){
	if (!cbap.enabled || !cbap.fullCredit ||
			!cbap.creditGateActive ||
			cbap.phase != CBAP_ADMISSION_HOLD ||
			cbap.baseEligibilityLastNs == 0 ||
			nowNs <= cbap.baseEligibilityLastNs)
		return;
	uint64_t elapsed = nowNs - cbap.baseEligibilityLastNs;
	cbap.baseEligibleBytes +=
		(long double)cbap.baseRateBps * elapsed / 8.0e9L;
	cbap.baseEligibilityLastNs = nowNs;
}

int32_t RdmaQueuePair::GetRoundIndexForSequence(uint64_t sequence) const {
	if (!crfm.enabled)
		return -1;
	for (uint32_t i = 0; i < crfm.rounds.size(); ++i)
		if (sequence >= crfm.rounds[i].startSeq &&
			sequence < crfm.rounds[i].endSeq)
			return i;
	return -1;
}

uint32_t RdmaQueuePair::GetHash(void){
	union{
		struct {
			uint32_t sip, dip;
			uint16_t sport, dport;
		};
		char c[12];
	} buf;
	buf.sip = sip.Get();
	buf.dip = dip.Get();
	buf.sport = sport;
	buf.dport = dport;
	return Hash32(buf.c, 12);
}

void RdmaQueuePair::Acknowledge(uint64_t ack){
	if (ack > snd_una){
		snd_una = ack;
	}
}

uint64_t RdmaQueuePair::GetOnTheFly(){
	return snd_nxt - snd_una;
}

bool RdmaQueuePair::IsWinBound(){
	uint64_t w = GetWin();
	return w != 0 && GetOnTheFly() >= w;
}

uint64_t RdmaQueuePair::GetWin(){
	if (m_win == 0)
		return 0;
	uint64_t w;
	if (m_var_win){
		w = m_win * m_rate.GetBitRate() / m_max_rate.GetBitRate();
		if (w == 0)
			w = 1; // must > 0
	}else{
		w = m_win;
	}
	return w;
}

uint64_t RdmaQueuePair::HpGetCurWin(){
	if (m_win == 0)
		return 0;
	uint64_t w;
	if (m_var_win){
		w = m_win * hp.m_curRate.GetBitRate() / m_max_rate.GetBitRate();
		if (w == 0)
			w = 1; // must > 0
	}else{
		w = m_win;
	}
	return w;
}

bool RdmaQueuePair::IsFinished(){
	return snd_una >= m_size;
}

/*********************
 * RdmaRxQueuePair
 ********************/
TypeId RdmaRxQueuePair::GetTypeId (void)
{
	static TypeId tid = TypeId ("ns3::RdmaRxQueuePair")
		.SetParent<Object> ()
		;
	return tid;
}

RdmaRxQueuePair::RdmaRxQueuePair(){
	sip = dip = sport = dport = 0;
	m_ipid = 0;
	ReceiverNextExpectedSeq = 0;
	m_nackTimer = Time(0);
	m_milestone_rx = 0;
	m_lastNACK = 0;
}

uint32_t RdmaRxQueuePair::GetHash(void){
	union{
		struct {
			uint32_t sip, dip;
			uint16_t sport, dport;
		};
		char c[12];
	} buf;
	buf.sip = sip;
	buf.dip = dip;
	buf.sport = sport;
	buf.dport = dport;
	return Hash32(buf.c, 12);
}

/*********************
 * RdmaQueuePairGroup
 ********************/
TypeId RdmaQueuePairGroup::GetTypeId (void)
{
	static TypeId tid = TypeId ("ns3::RdmaQueuePairGroup")
		.SetParent<Object> ()
		;
	return tid;
}

RdmaQueuePairGroup::RdmaQueuePairGroup(void){
}

uint32_t RdmaQueuePairGroup::GetN(void){
	return m_qps.size();
}

Ptr<RdmaQueuePair> RdmaQueuePairGroup::Get(uint32_t idx){
	return m_qps[idx];
}

Ptr<RdmaQueuePair> RdmaQueuePairGroup::operator[](uint32_t idx){
	return m_qps[idx];
}

void RdmaQueuePairGroup::AddQp(Ptr<RdmaQueuePair> qp){
	m_qps.push_back(qp);
}

#if 0
void RdmaQueuePairGroup::AddRxQp(Ptr<RdmaRxQueuePair> rxQp){
	m_rxQps.push_back(rxQp);
}
#endif

void RdmaQueuePairGroup::Clear(void){
	m_qps.clear();
}

}
