#ifndef RDMA_QUEUE_PAIR_H
#define RDMA_QUEUE_PAIR_H

#include <ns3/object.h>
#include <ns3/packet.h>
#include <ns3/ipv4-address.h>
#include <ns3/data-rate.h>
#include <ns3/event-id.h>
#include <ns3/custom-header.h>
#include <ns3/int-header.h>
#include <vector>

namespace ns3 {

class RdmaQueuePair : public Object {
public:
	Time startTime;
	Ipv4Address sip, dip;
	uint16_t sport, dport;
	uint64_t m_size;
	uint64_t snd_nxt, snd_una; // next seq to send, the highest unacked seq
	uint16_t m_pg;
	uint16_t m_ipid;
	uint32_t m_win; // bound of on-the-fly packets
	uint64_t m_baseRtt; // base RTT of this qp
	DataRate m_max_rate; // max rate
	// Application-imposed rate ceiling, independent of any congestion
	// controller's decisions.  Zero (default) means no cap is applied.
	uint64_t m_appRateCapBps;
	bool m_var_win; // variable window size
	Time m_nextAvail;	//< Soonest time of next send
	uint32_t wp; // current window of packets
	uint32_t lastPktSize;
	Callback<void> m_notifyAppFinish;

	/******************************
	 * runtime states
	 *****************************/
	DataRate m_rate;	//< Current rate
	struct {
		DataRate m_targetRate;	//< Target rate
		EventId m_eventUpdateAlpha;
		double m_alpha;
		bool m_alpha_cnp_arrived; // indicate if CNP arrived in the last slot
		bool m_first_cnp; // indicate if the current CNP is the first CNP
		EventId m_eventDecreaseRate;
		bool m_decrease_cnp_arrived; // indicate if CNP arrived in the last slot
		uint32_t m_rpTimeStage;
		EventId m_rpTimer;
	} mlx;
	struct {
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		IntHop hop[IntHeader::maxHop];
		uint32_t keep[IntHeader::maxHop];
		uint32_t m_incStage;
		double m_lastGap;
		double u;
		struct {
			double u;
			DataRate Rc;
			uint32_t incStage;
		}hopState[IntHeader::maxHop];
	} hp;
	struct{
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		uint32_t m_incStage;
		uint64_t lastRtt;
		double rttDiff;
	} tmly;
	enum CrfmFeedbackClass {
		CRFM_FEEDBACK_NONE = 0,
		CRFM_ACTIONABLE_CURRENT = 1,
		CRFM_LATE_SAME_ROUND = 2,
		CRFM_STALE_OLDER_ROUND = 3
	};
	struct CrfmRoundState {
			uint32_t roundId;
			uint32_t roundGroupId;
			uint32_t participantCount;
			uint32_t jitterGroup;
			uint64_t computeGapNs;
			int64_t jitterNs;
			uint64_t releaseTimeNs;
		uint64_t roundBytes;
		uint64_t startSeq;
		uint64_t endSeq;
		uint64_t injectionEndTimeNs;
		uint64_t ackCompletionTimeNs;
		uint64_t startRate;
		uint64_t minimumRate;
		uint64_t endRate;
		uint64_t nextRoundStartRate;
		uint64_t selectedLinkPeakQueue;
		uint64_t totalFeedback;
		uint64_t actionableFeedback;
		uint64_t lateSameRoundFeedback;
		uint64_t staleOlderRoundFeedback;
		uint64_t feedbackDuringOff;
		uint64_t liveRateChangesDuringOff;
		uint64_t firstFeedbackTimeNs;
		uint64_t lastFeedbackTimeNs;
		double remainingUnsentRatioSum;
		double minimumRemainingUnsentRatio;
		uint64_t remainingUnsentBytesSum;
		uint64_t minimumRemainingUnsentBytes;
		double maximumNormalizedLoad;
		double normalizedLoadSum;
		uint64_t normalizedLoadSamples;
			uint64_t maximumQueueBytes;
			uint32_t feedbackBaselineHops;
		IntHop feedbackHop[IntHeader::maxHop];
		uint64_t firstFeedbackRateBefore;
		uint64_t lastFeedbackRateAfter;
			uint64_t feedbackChangedLiveRate;
			uint64_t cnpCount;
			double dcqcnStartAlpha;
			double dcqcnEndAlpha;
			uint32_t dcqcnStartRecoveryStage;
			uint32_t dcqcnEndRecoveryStage;
			uint64_t commonReleaseHintNs;
			uint64_t commonReleaseTimeNs;
			uint64_t barrierCompletionTimeNs;
			bool bopPlanApplied;
			uint64_t bopSelectedRateBps;
			uint64_t bopMaxRateBps;
			uint64_t bopPhaseOffsetNs;
			uint64_t bopResidualQueueBytes;
			uint64_t bopBottleneckBps;
			uint64_t bopBackgroundBps;
			double bopTLineSeconds;
			double bopTLinkSeconds;
			double bopTStarSeconds;
			uint32_t bopFallbackReason;
			uint64_t bopQcBaseRateBps;
			uint64_t bopQcCreditBytes;
			uint64_t bopQcCreditEndSeq;
			uint64_t bopQcBurstRateBps;
			bool bopQcSwitchedToBase;
			uint64_t bopQcActualBurstBytes;
			double bopQcQueueSampleAgeUs;
			double bopQcFeedbackTauUs;
			uint32_t bopQcTauSource;
			uint64_t bopQcEcnThresholdBytes;
			uint64_t bopQcPacketMarginBytes;
			uint64_t bopQcQueueRoomBytes;
			uint64_t bopQcBdpCreditBytes;
			uint64_t bopQcGroupCreditBytes;
			uint64_t bopQcTotalAllocatedCreditBytes;
			uint32_t bopQcFallbackReason;
			uint64_t bopQbBaseRateBps;
			uint64_t bopQbCreditBytes;
			uint64_t bopQbCreditEndSeq;
			uint64_t bopQbBurstRateBps;
			bool bopQbSwitchedToBase;
			uint64_t bopQbActualBurstBytes;
			uint64_t bopQbEcnThresholdBytes;
			uint64_t bopQbQueueTargetBytes;
			uint64_t bopQbPacketMarginBytes;
			uint64_t bopQbQueueRoomBytes;
			uint64_t bopQbGroupCreditBytes;
			uint64_t bopQbTotalAllocatedCreditBytes;
			uint32_t bopQbFallbackReason;
			bool bopQbSafetyBoundValid;
			uint64_t bopQbEstimatedQueueBytes;
			uint64_t bopQbActualQueueBytes;
			int64_t bopQbQueueErrorBytes;
			double bopQbQueueErrorRatio;
			double bopQbQueueSampleAgeUs;
			uint32_t bopQbQueueSampleOrigin;
			bool bopQbSafetyBoundUsingActual;
			uint32_t prtProbeCountSent;
			uint32_t prtProbeReturnedBeforeRelease;
			uint64_t prtDecisionReleaseNs;
			uint64_t prtProbe1SendNs;
			uint64_t prtProbe1QueueSampleNs;
			uint64_t prtProbe1AckNs;
			uint64_t prtProbe1QueueBytes;
			uint64_t prtProbe2SendNs;
			uint64_t prtProbe2QueueSampleNs;
			uint64_t prtProbe2AckNs;
			uint64_t prtProbe2QueueBytes;
			double prtQueueSlopeBytesPerNs;
			uint64_t prtQueueHatBytes;
			uint64_t prtActualQueueBytes;
			int64_t prtQueueErrorBytes;
			uint32_t prtFallbackReason;
			uint64_t prtOriginalBopCreditBytes;
			uint64_t prtCreditBytes;
			uint64_t prtPrimerEcn;
			uint64_t prtCollectiveEcn;
			uint64_t bopQbMaxBaseRateBps;
			uint64_t bopQbMaxCreditBytes;
			uint64_t bopQbMaxCreditEndSeq;
			uint64_t bopQbMaxBurstRateBps;
			bool bopQbMaxSwitchedToBase;
			uint64_t bopQbMaxActualBurstBytes;
			uint64_t bopQbMaxQueueSampleTimeNs;
			double bopQbMaxQueueSampleAgeUs;
			uint64_t bopQbMaxEcnThresholdBytes;
			uint64_t bopQbMaxPacketMarginBytes;
			uint64_t bopQbMaxQueueRoomBytes;
			uint64_t bopQbMaxGroupCreditBytes;
			uint64_t bopQbMaxTotalAllocatedCreditBytes;
			uint32_t bopQbMaxFallbackReason;
			bool bopQbMaxSafetyBoundValid;
			uint64_t groupQueueMaxBytes;
			uint64_t groupEcnMarks;
			uint64_t groupPfcEvents;

			CrfmRoundState();
	};
	struct {
		bool enabled;
		uint32_t flowId;
		uint64_t releasedBytes;
		int32_t currentRoundIndex;
		int32_t lastCompletedRound;
		int32_t latestFeedbackOriginRound;
		uint32_t latestFeedbackClass;
		uint64_t directHpccUpdates;
		uint64_t gatedLateUpdates;
		uint64_t gatedStaleUpdates;
		double rateTotalVariation;
		uint64_t minimumRate;
		uint64_t maximumRate;
		bool bopTelemetryValid;
		int32_t bopTelemetryOriginRound;
		uint64_t bopLastQueueBytes;
		uint64_t bopLastSampleTimeNs;
		uint64_t bopLastArrivalTimeNs;
		uint64_t bopLastBottleneckBps;
		bool bopQcTauValid;
		double bopQcTauEwmaNs;
		uint64_t bopQcBaseRate;
		uint64_t bopQcCreditTotal;
		uint64_t bopQcCreditRemaining;
		uint64_t bopQcCreditEndSeq;
		uint64_t bopQcPhaseOffsetNs;
		bool bopQcSwitchedToBase;
		bool bopQcSwitchPending;
		uint64_t bopQcActualBurstBytes;
		uint64_t bopQbBaseRate;
		uint64_t bopQbCreditTotal;
		uint64_t bopQbCreditRemaining;
		uint64_t bopQbCreditEndSeq;
		uint64_t bopQbPhaseOffsetNs;
		bool bopQbSwitchedToBase;
		bool bopQbSwitchPending;
		uint64_t bopQbActualBurstBytes;
		uint64_t bopQbMaxBaseRate;
		uint64_t bopQbMaxCreditTotal;
		uint64_t bopQbMaxCreditRemaining;
		uint64_t bopQbMaxCreditEndSeq;
		uint64_t bopQbMaxPhaseOffsetNs;
		bool bopQbMaxSwitchedToBase;
		bool bopQbMaxSwitchPending;
		uint64_t bopQbMaxActualBurstBytes;
		std::vector<CrfmRoundState> rounds;
	} crfm;
	struct{
		uint32_t m_lastUpdateSeq;
		uint32_t m_caState;
		uint32_t m_highSeq; // when to exit cwr
		double m_alpha;
		uint32_t m_ecnCnt;
		uint32_t m_batchSizeOfAlpha;
	} dctcp;
	struct{
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		uint32_t m_incStage;
	}hpccPint;
	enum CbapPhase {
		CBAP_DISABLED = 0,
		CBAP_PREPARE = 1,
		CBAP_ADMISSION_HOLD = 2,
		CBAP_TRACKING = 3,
		CBAP_RECOVERY = 4,
		CBAP_FINISHED = 5,
		// Appended values preserve every v1.3 phase identifier and trace.
		CBAP_HANDOFF_PENDING = 6,
		CBAP_BASE_CC = 7,
		// v1.5 appends a phase so v1.3/v1.4 trace identities stay stable.
		CBAP_DELEGATED_ENVELOPE = 8,
		// v2.0 is a separate startup-only state machine.
		CBAP_CLASSIFY = 9,
		CBAP_BYPASS = 10,
		CBAP_STARTUP_ADMISSION = 11,
		CBAP_SMOOTH_HANDOFF = 12,
		CBAP_BASE_CC_ONLY = 13
	};
	struct {
		bool enabled;
		bool fullCredit;
		bool initOnly;
		bool independentDiagnostic;
		uint32_t batchId;
		uint32_t phase;
		uint32_t stableEpochCount;
		uint32_t increaseFreezeEpochs;
		uint32_t rootId;
		uint32_t lastRateDecisionEpoch;
		uint32_t lastDecreaseEpoch;
		uint64_t applicationReadyNs;
		uint64_t networkReleaseNs;
		uint64_t currentRateBps;
		uint64_t targetRateBps;
		uint64_t requestedRateBps;
		uint64_t admitRateBps;
		uint64_t baseRateBps;
		uint64_t creditInitialBytes;
		uint64_t creditRemainingBytes;
		bool creditGateActive;
		uint64_t creditRemainingAtAdmissionExit;
		uint64_t bytesSentAtRelease;
		uint64_t bytesAckedAtRelease;
		uint64_t lastTxTimeNs;
		uint64_t lastPacketSeq;
		uint64_t lastPacketWireBytes;
		uint64_t lastFreshFeedbackNs;
		uint64_t firstFreshFeedbackNs;
		uint64_t admissionEnterNs;
		uint64_t admissionExitNs;
		uint64_t firstDataTxNs;
		uint64_t firstPostReleaseSampleNs;
		uint64_t firstCompleteFreshFeedbackNs;
		uint64_t initialAdmitRateBps;
		uint64_t bytesSentBeforeFreshFeedback;
		uint64_t rateUpdatesBeforeFirstTx;
		uint64_t ordinaryRateUpdatesDuringAdmission;
		uint64_t emergencyRateUpdatesDuringAdmission;
		uint64_t creditGateEnterNs;
		uint64_t creditGateExitNs;
		uint64_t estimatedFirstFeedbackNs;
		uint64_t protectionFloorBps;
		uint64_t rebalanceStartNs;
		uint64_t rebalanceEndNs;
		uint64_t lastEpochSndNxt;
		uint64_t recentActualRateBps[2];
		uint64_t baseEligibilityLastNs;
		long double baseEligibleBytes;
		uint64_t excessBytes;
		uint64_t capacityViolationCount;
		uint64_t creditViolationCount;
		uint64_t staleFeedbackCount;
		uint64_t rateIncreaseCount;
		uint64_t rateDecreaseCount;
		uint64_t rateHoldCount;
		uint64_t rescheduleCount;
		uint64_t firstFair80Ns;
		uint64_t firstFair90Ns;
		uint64_t firstFair95Ns;
		uint64_t trackingStartNs;
		uint64_t trackingBytesSent;
		uint64_t trackingRateLastNs;
		long double trackingRateIntegral;
		uint64_t pacingViolationCount;
		uint64_t txTraceTrackingPackets;
		bool exactGrantPacing;
		bool zeroGrantPaused;
		uint64_t zeroGrantPauseCount;
		uint64_t zeroGrantResumeCount;
		uint64_t zeroGrantPauseStartNs;
		uint64_t zeroGrantPausedNs;
		bool handoffEnabled;
		bool handedOff;
		bool cbapCnpObserved;
		uint64_t lastCbapCnpNs;
		uint64_t handoffExecuteNs;
		uint64_t handoffRateBps;
		uint64_t handoffNextTxBeforeNs;
		uint64_t handoffNextTxAfterNs;
		uint64_t firstTxAfterHandoffNs;
		uint64_t firstDcqcnRateUpdateNs;
		uint64_t firstDcqcnCnpNs;
		uint32_t handoffFlowRecordIndex;
		bool delegationEnabled;
		bool delegatedEnvelope;
		uint32_t delegationCount;
		uint64_t delegationExecuteNs;
		uint64_t dcqcnDesiredRateBps;
		uint64_t envelopeAppliedRateBps;
		double envelopeScale;
		bool envelopeBound;
		uint64_t desiredRateLastUpdateNs;
		uint64_t appliedRateLastUpdateNs;
		uint64_t positiveAiSuppressed;
		uint64_t decreaseApplied;
		uint64_t simulatorInternalRateWrites;
		uint64_t postDelegationFullGrantCount;
		uint64_t timeBelow90TargetNs;
		uint64_t timeBelow80TargetNs;
		uint64_t timeBelow50TargetNs;
		uint64_t incumbentAuditLastNs;
		CbapPhase phaseAtLastPacket;
		bool v20Enabled;
		uint32_t v20Classification;
		uint32_t v20BaseCc;
		uint64_t v20BlindWindowNs;
		uint64_t v20LeaseExpiryNs;
		uint64_t v20FirstFreshFeedbackNs;
		uint64_t v20HandoffInitialRateBps;
		uint64_t v20PostHandoffCbapWriteCount;
		bool v20CatchUpBurst;
		// Scheme-1 CBAP-SBA is separate from every legacy/v2.0 controller.
		bool sbaEnabled;
		uint64_t sbaLastAppliedRateBps;
		uint64_t sbaFirstFeedbackNs;
		uint32_t sbaHandoffCount;
		// UNCALIBRATED: fixed conservative deadline, not derived from a
		// measured blind-window distribution.  See CBAP_SBA_LEASE_NS.
		uint64_t sbaLeaseExpiryNs;
		uint32_t sbaLeaseExpiryCount;
		// Throttle for the app-cap trace so it prints once per millisecond
		// per flow rather than once per packet.
		uint64_t appCapTraceNextNs;
		// Capacity migration (docs/cbap_sba_capacity_migration_design.md):
		// SBA layers a rate envelope over DCQCN during a batch handover.
		// Effective send rate becomes min(DCQCN rate, envelope).
		bool migrationActive;
		bool migrationIsOldFlow;
		uint64_t migrationTargetBps;
		uint64_t migrationEnvelopeBps;
		uint64_t migrationStartNs;
		uint64_t migrationRetargetCount;
		// Bounded-error instrumentation: DCQCN can exceed the envelope
		// between two epoch corrections (design doc section 9).
		uint64_t migrationBreachCount;
		uint64_t migrationMaxBreachBps;
		uint64_t migrationBreachBytes;
	} cbap;

	/***********
	 * methods
	 **********/
	static TypeId GetTypeId (void);
	RdmaQueuePair(uint16_t pg, Ipv4Address _sip, Ipv4Address _dip, uint16_t _sport, uint16_t _dport);
	void SetSize(uint64_t size);
	void SetWin(uint32_t win);
	void SetBaseRtt(uint64_t baseRtt);
	void SetVarWin(bool v);
	void SetAppNotifyCallback(Callback<void> notifyAppFinish);

	uint64_t GetBytesLeft();
	void UpdateCbapEligibility(uint64_t nowNs);
	int32_t GetRoundIndexForSequence(uint64_t sequence) const;
	uint32_t GetHash(void);
	void Acknowledge(uint64_t ack);
	uint64_t GetOnTheFly();
	bool IsWinBound();
	uint64_t GetWin(); // window size calculated from m_rate
	bool IsFinished();
	uint64_t HpGetCurWin(); // window size calculated from hp.m_curRate, used by HPCC
};

class RdmaRxQueuePair : public Object { // Rx side queue pair
public:
	struct ECNAccount{
		uint16_t qIndex;
		uint8_t ecnbits;
		uint16_t qfb;
		uint16_t total;

		ECNAccount() { memset(this, 0, sizeof(ECNAccount));}
	};
	ECNAccount m_ecn_source;
	uint32_t sip, dip;
	uint16_t sport, dport;
	uint16_t m_ipid;
	uint32_t ReceiverNextExpectedSeq;
	Time m_nackTimer;
	int32_t m_milestone_rx;
	uint32_t m_lastNACK;
	EventId QcnTimerEvent; // if destroy this rxQp, remember to cancel this timer

	static TypeId GetTypeId (void);
	RdmaRxQueuePair();
	uint32_t GetHash(void);
};

class RdmaQueuePairGroup : public Object {
public:
	std::vector<Ptr<RdmaQueuePair> > m_qps;
	//std::vector<Ptr<RdmaRxQueuePair> > m_rxQps;

	static TypeId GetTypeId (void);
	RdmaQueuePairGroup(void);
	uint32_t GetN(void);
	Ptr<RdmaQueuePair> Get(uint32_t idx);
	Ptr<RdmaQueuePair> operator[](uint32_t idx);
	void AddQp(Ptr<RdmaQueuePair> qp);
	//void AddRxQp(Ptr<RdmaRxQueuePair> rxQp);
	void Clear(void);
};

}

#endif /* RDMA_QUEUE_PAIR_H */
