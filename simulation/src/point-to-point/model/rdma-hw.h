#ifndef RDMA_HW_H
#define RDMA_HW_H

#include <ns3/rdma.h>
#include <ns3/rdma-queue-pair.h>
#include <ns3/node.h>
#include <ns3/custom-header.h>
#include "qbb-net-device.h"
#include "cbap-sba.h"
#include <unordered_map>
#include <map>
#include <set>
#include <string>
#include "pint.h"

namespace ns3 {

struct RdmaInterfaceMgr{
	Ptr<QbbNetDevice> dev;
	Ptr<RdmaQueuePairGroup> qpGrp;

	RdmaInterfaceMgr() : dev(NULL), qpGrp(NULL) {}
	RdmaInterfaceMgr(Ptr<QbbNetDevice> _dev){
		dev = _dev;
	}
};

class RdmaHw : public Object {
public:
	enum {
		CC_MODE_HPCC_ROUND_RESET = 11,
		CC_MODE_CRFM_GATE = 12,
		CC_MODE_BOP = 13,
		CC_MODE_BOP_QC = 14,
		CC_MODE_BOP_QB = 15,
		CC_MODE_BOP_QB_MAX = 16,
		CC_MODE_DCQCN_WIRE_EQUALIZED = 17,
		CC_MODE_BOP_QB_ORACLE_Q0 = 18,
		CC_MODE_BOP_QB_PRT = 19,
		CC_MODE_CBAP_INDEPENDENT = 20,
		CC_MODE_CBAP_INIT_ONLY = 21,
		CC_MODE_CBAP_RATE_ONLY = 22,
		CC_MODE_CBAP_FULL = 23,
		CC_MODE_CBAP_FULL_SCOPED = 24,
		CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX = 25,
		CC_MODE_CBAP_FULL_STABLE_HANDOFF = 26,
		CC_MODE_CBAP_FULL_GUARDED_DELEGATION = 27,
		CC_MODE_CBAP_V20_STARTUP_HANDOFF_DCQCN = 28,
		CC_MODE_CBAP_V20_STARTUP_HANDOFF_HPCC = 29,
		CC_MODE_CBAP_SBA_DCQCN = 30,
		// Same SBA startup admission and capacity migration as mode 30, but
		// control is handed to HPCC rather than DCQCN once the first
		// actionable feedback arrives.  Added to separate the contribution of
		// batch admission from the strength of the post-handoff controller.
		CC_MODE_CBAP_SBA_HPCC = 31
	};
	enum {
		BOP_Q0_ORIGIN_NONE = 0,
		BOP_Q0_ORIGIN_INT = 1,
		BOP_Q0_ORIGIN_ORACLE_RELEASE = 2
	};
	enum {
		BOP_FALLBACK_NONE = 0,
		BOP_FALLBACK_INITIAL_QUEUE_ZERO = 1,
		BOP_FALLBACK_NO_VALID_TELEMETRY = 2,
		BOP_FALLBACK_NOT_BOP = 3
	};
	enum {
		BOP_QC_FALLBACK_NONE = 0,
		BOP_QC_FALLBACK_NO_QUEUE = 1,
		BOP_QC_FALLBACK_DEFAULT_TAU = 2,
		BOP_QC_FALLBACK_FIRST_ROUND = 4,
		BOP_QC_FALLBACK_NOT_QC = 8
	};
	enum {
		BOP_QC_TAU_NOT_QC = 0,
		BOP_QC_TAU_DEFAULT = 1,
		BOP_QC_TAU_EWMA = 2
	};
	enum {
		BOP_QB_FALLBACK_NONE = 0,
		BOP_QB_FALLBACK_NO_QUEUE = 1,
		BOP_QB_FALLBACK_FIRST_ROUND = 2,
		BOP_QB_FALLBACK_NOT_QB = 4
	};
	enum {
		BOP_QB_MAX_FALLBACK_NONE = 0,
		BOP_QB_MAX_FALLBACK_NO_PRE_RELEASE_QUEUE = 1,
		BOP_QB_MAX_FALLBACK_NOT_QB_MAX = 2
	};

	static TypeId GetTypeId (void);
	RdmaHw();
	static bool IsDcqcnMode(uint32_t mode);
	static bool IsBopQbMode(uint32_t mode);
	static bool UsesBopQbCredit(uint32_t mode);
	static bool UsesHpccTelemetryMode(uint32_t mode);
	// True for both SBA variants (DCQCN- and HPCC-based post-handoff).
	static bool IsCbapSbaMode(uint32_t mode);
	static bool IsCbapMode(uint32_t mode);
	struct BopMultilinkLink {
		uint32_t linkId;
		uint32_t nodeId;
		uint32_t ifIndex;
		uint64_t capacityBps;
		uint64_t ecnThresholdBytes;
		uint64_t backgroundBps;
		bool telemetryEligible;
	};
	struct BopMultilinkGroupDecision {
		uint32_t groupId;
		uint32_t roundIndex;
		uint32_t participantCount;
		uint64_t totalRoundBytes;
		double alpha;
		double tStarSeconds;
		uint32_t limitingLinkCount;
		bool formulaValid;
		bool capacityValid;
		bool creditConstraintValid;
	};
	struct BopMultilinkLinkDecision {
		uint32_t groupId;
		uint32_t roundIndex;
		uint32_t linkId;
		uint64_t capacityBps;
		uint64_t queueBytes;
		uint64_t ecnThresholdBytes;
		uint32_t flowCount;
		uint64_t workloadBytes;
		uint64_t queueRoomBytes;
		uint64_t creditSumBytes;
		double tLinkSeconds;
		bool limitingLink;
		double tStarSeconds;
		bool formulaValid;
		bool capacityValid;
		bool creditConstraintValid;
	};
	static void ConfigureBopMultilink(
			bool enabled,
			const std::vector<BopMultilinkLink> &links,
			const std::map<uint32_t, std::vector<uint32_t> > &flowPaths,
			const std::map<uint32_t, int64_t> &groupPredecessors);
	static const std::vector<BopMultilinkGroupDecision> &
			GetBopMultilinkGroupDecisions();
	static const std::vector<BopMultilinkLinkDecision> &
			GetBopMultilinkLinkDecisions();
	static bool HasActiveBopMultilinkGroup();
	enum CbapPortState {
		CBAP_PORT_CLEAR = 0,
		CBAP_PORT_STABLE = 1,
		CBAP_PORT_ROOT_CONGESTED = 2,
		CBAP_PORT_PROPAGATED = 3,
		CBAP_PORT_MIXED_OR_UNCERTAIN = 4
	};
	enum CbapIncreasePolicy {
		CBAP_INCREASE_LEGACY_V1 = 0,
		CBAP_INCREASE_ADAPTIVE_V11 = 1
	};
	enum CbapScopePolicy {
		CBAP_SCOPE_ALWAYS = 0,
		CBAP_SCOPE_SHARED_BATCH_OVERSUBSCRIPTION = 1
	};
	enum CbapScopeReason {
		CBAP_SCOPE_REASON_ALWAYS = 0,
		CBAP_SCOPE_REASON_SHARED_BATCH_OVERSUBSCRIBED = 1,
		CBAP_SCOPE_REASON_NO_SHARED_LINK = 2,
		CBAP_SCOPE_REASON_WITHIN_ADMISSION_CAPACITY = 3
	};
	enum CbapRateFloorPolicy {
		CBAP_RATE_FLOOR_ONE_PACKET_PER_EPOCH_LEGACY = 0,
		CBAP_RATE_FLOOR_EXACT_GRANT_PACING = 1
	};
	enum CbapV20Classification {
		CBAP_V20_C0_NO_RISK = 0,
		CBAP_V20_C1_SINGLE_HOTSPOT = 1,
		CBAP_V20_C2_COMPLEX = 2
	};
	struct CbapConfig {
		bool enabled;
		uint64_t controlEpochNs;
		uint64_t planningDelayNs;
		uint64_t controlDelayNs;
		double rho;
		double epsilonRate;
		uint32_t priority;
		uint32_t maxWirePacketBytes;
		uint32_t summaryBytes;
		uint32_t grantBytes;
		uint32_t txTraceTrackingPackets;
		uint32_t increasePolicy;
		double increaseFraction;
		uint64_t increaseAbsoluteBps;
		uint32_t scopePolicy;
		uint32_t scopeBaseCc;
		uint32_t rateFloorPolicy;
		bool rateFloorSemanticZeroTest;
		uint32_t rateFloorSemanticZeroFlow;
		uint32_t rateFloorSemanticZeroStartEpoch;
		uint32_t rateFloorSemanticZeroEndEpoch;
		bool handoffEnabled;
		uint32_t handoffStableEpochsRequired;
		uint32_t handoffBaseCc;
		bool handoffDiagnosticForceRoot;
		uint32_t handoffDiagnosticRecoveryUntilEpoch;
		uint32_t delegationDiagnosticForceStaleEpochs;
		double queueTargetFraction;
		// UNCALIBRATED: SBA startup-admission deadline.  Doc section 3.3
		// requires measuring the DCQCN/HPCC feedback blind window
		// (median/p95/p99) before fixing H; this fixed value has not been
		// calibrated against any measured distribution and must be
		// revisited once S1-S6 first-feedback timestamps are available.
		uint64_t sbaLeaseNs;
		// Scheme-1 batch-to-batch reclaim redesign: dynamic per-link
		// budget based on queue occupancy (independent of the
		// portState qLow/qTarget/qHigh classification thresholds).
		double budgetQLowFraction;
		double budgetQHighFraction;
		double maxDrainRatio;
		// Batch-level target weights (old vs new) for the 50:50 split.
		double oldBatchWeight;
		double newBatchWeight;
		// Capacity migration (docs/cbap_sba_capacity_migration_design.md).
		// Disabled by default so existing baselines are untouched.
		bool migrationEnabled;
		double migrationReleaseRatio;
		double migrationDecayBase;
		double migrationRiseBase;
		double migrationRiseSkew;
		uint32_t migrationMaxRtt;
		bool migrationTrace;
		// Per-replan audit of the capacity-feasibility rule.  Off by default
		// so no existing run changes behaviour or output.
		bool etaFeasibilityTrace;
		// ---- Queueing-delay credit (transient oversubscription) ----------
		// All off/zero by default: with delayCreditEnable false the planner
		// keeps the strict sum(target) <= C behaviour bit-for-bit, so the
		// legacy control arm needs no separate code path.
		//
		// The invariant enforced is a queueing-DELAY bound, not a rate bound:
		//   queue_delay_s = queue_bytes * 8 / capacityBps
		// and the planner may hand out short-lived credit while the measured
		// queue sits below its target, bounded so the predicted queue after
		// one horizon cannot cross the hard limit.
		bool delayCreditEnable;
		double queueDelayTargetS;     // q_target  = C * this / 8
		double queueDelayHardLimitS;  // hard delay budget above q_sync_floor
		double creditHorizonS;        // H, the control loop period
		double maxOversubRatio;       // credit_bps <= this * C
		double creditMaxDrainRatio;   // drain_bps  <= this * C
		uint64_t queueSafetyMarginBytes;
		std::string scenario;
		std::string algorithm;
		std::string cbapVersion;
		CbapConfig()
			: enabled(false), controlEpochNs(5000),
			  planningDelayNs(5000), controlDelayNs(5000),
			  rho(0.95), epsilonRate(0.02), priority(3),
			  maxWirePacketBytes(1064), summaryBytes(64),
			  grantBytes(48), txTraceTrackingPackets(4096),
			  increasePolicy(CBAP_INCREASE_LEGACY_V1),
			  increaseFraction(0.10),
			  increaseAbsoluteBps(UINT64_C(2000000000)),
			  scopePolicy(CBAP_SCOPE_ALWAYS), scopeBaseCc(1),
			  rateFloorPolicy(CBAP_RATE_FLOOR_ONE_PACKET_PER_EPOCH_LEGACY),
			  rateFloorSemanticZeroTest(false),
			  rateFloorSemanticZeroFlow(0),
			  rateFloorSemanticZeroStartEpoch(0),
			  rateFloorSemanticZeroEndEpoch(0),
			  handoffEnabled(false), handoffStableEpochsRequired(2),
			  handoffBaseCc(1), handoffDiagnosticForceRoot(false),
			  handoffDiagnosticRecoveryUntilEpoch(0),
			  delegationDiagnosticForceStaleEpochs(0),
			  queueTargetFraction(0.25),
			  sbaLeaseNs(UINT64_C(1000000)),
			  budgetQLowFraction(0.5), budgetQHighFraction(1.0),
			  maxDrainRatio(0.20), oldBatchWeight(1.0),
			  newBatchWeight(1.0),
			  migrationEnabled(false), migrationReleaseRatio(0.5),
			  migrationDecayBase(0.30), migrationRiseBase(0.30),
			  migrationRiseSkew(0.35), migrationMaxRtt(5),
			  migrationTrace(false), etaFeasibilityTrace(false),
			  delayCreditEnable(false), queueDelayTargetS(0.0),
			  queueDelayHardLimitS(0.0), creditHorizonS(0.0),
			  maxOversubRatio(0.0), creditMaxDrainRatio(0.0),
			  queueSafetyMarginBytes(0),
			  scenario("unknown"), algorithm("unknown"),
			  cbapVersion("v1") {}
	};
	struct CbapV20BatchRecord {
		uint32_t batchId;
		uint32_t linkId;
		uint32_t classification;
		std::string classificationReason;
		uint32_t riskyLinkCount;
		uint64_t blindWindowNs;
		uint64_t queue0Bytes;
		uint64_t queueTargetBytes;
		uint64_t effectiveCapacityBps;
		uint64_t blindWorkBytes;
		uint64_t serviceAndBufferBytes;
		uint64_t excessBytes;
		uint64_t startupBudgetBps;
		uint64_t admissionAggregateBps;
		uint64_t actualAppliedAggregateBps;
		uint64_t firstFreshFeedbackNs;
		uint64_t leaseExpiryNs;
		uint64_t handoffNs;
		std::string handoffReason;
		std::string baseCc;
		uint64_t postHandoffCbapWriteCount;
		bool catchUpBurst;
		bool capacityViolation;
		bool pacingViolation;
		bool preReleaseCausal;
		CbapV20BatchRecord();
	};
	struct CbapV20FlowRecord {
		uint32_t batchId;
		uint32_t flowId;
		uint32_t classification;
		uint64_t startupGrantBps;
		uint64_t pathMinGrantBps;
		uint64_t appliedRateBps;
		uint64_t packetGapNs;
		uint64_t firstFreshFeedbackNs;
		uint64_t handoffInitialRateBps;
		std::string postHandoffOwner;
		uint64_t postHandoffCbapWriteCount;
		bool catchUpBurst;
		CbapV20FlowRecord();
	};
	struct CbapHandoffBatchRecord {
		uint32_t batchId;
		uint64_t applicationReadyNs;
		uint64_t networkReleaseNs;
		uint64_t trackingEnterNs;
		uint64_t firstStableEpochNs;
		uint64_t handoffCandidateNs;
		uint64_t handoffExecuteNs;
		bool handoffOccurred;
		std::string noHandoffReason;
		uint32_t stableEpochCount;
		uint64_t measuredRttNs;
		uint64_t minimumTrackingTimeNs;
		uint32_t activeFlowCount;
		uint64_t remainingBytesTotal;
		double remainingFraction;
		uint64_t queueBytesAtHandoff;
		double queueGradientAtHandoff;
		uint64_t appliedRateSumBefore;
		uint64_t dcqcnRateSumAfterInit;
		uint64_t maxPerFlowRateJumpBps;
		uint64_t firstDcqcnRateUpdateNs;
		uint64_t firstDcqcnCnpNs;
		uint64_t grantsBeforeHandoff;
		uint64_t grantsAfterHandoff;
		uint64_t controlBytesBeforeHandoff;
		uint64_t controlBytesAfterHandoff;
		uint64_t shadowHandoffCandidateNs;
		uint64_t shadowRemainingBytes;
		double shadowRemainingFraction;
		uint64_t shadowQueueBytes;
		uint64_t shadowRateSumBps;
		uint64_t shadowControlledAfterCandidateNs;
		CbapHandoffBatchRecord();
	};
	struct CbapHandoffFlowRecord {
		uint32_t flowId;
		uint32_t batchId;
		uint32_t phaseBefore;
		uint32_t phaseAfter;
		uint64_t remainingBytes;
		uint64_t cbapAppliedRateBefore;
		uint64_t dcqcnCurrentRateAfter;
		uint64_t dcqcnTargetRateAfter;
		double alphaAfter;
		uint64_t nextTxBeforeNs;
		uint64_t nextTxAfterNs;
		uint64_t firstTxAfterHandoffNs;
		uint64_t packetGapRequiredNs;
		uint64_t packetGapActualNs;
		bool catchupBurstDetected;
		CbapHandoffFlowRecord();
	};
	struct CbapControllerOwnershipRecord {
		uint64_t timeNs;
		uint32_t epoch;
		uint32_t batchId;
		uint32_t flowId;
		uint32_t phase;
		std::string owner;
		bool cbapRateUpdate;
		bool dcqcnRateUpdate;
	};
	struct CbapEnvelopeLinkRecord {
		uint64_t epochNs;
		uint32_t epoch;
		uint32_t batchId;
		uint32_t linkId;
		uint64_t effectiveCapacityBps;
		uint64_t incumbentReserveBps;
		uint64_t batchBudgetBps;
		uint32_t delegatedFlowCount;
		uint64_t desiredRateSumBps;
		uint64_t appliedRateSumBps;
		double scale;
		bool staleFeedback;
		bool capIncreaseAllowed;
		uint64_t reserveReleaseBps;
		uint64_t capacityExcessBps;
		bool capacityViolation;
	};
	struct CbapEnvelopeFlowRecord {
		uint64_t epochNs;
		uint32_t epoch;
		uint32_t batchId;
		uint32_t flowId;
		uint64_t desiredRateBps;
		uint64_t appliedRateBps;
		double pathScale;
		bool envelopeBound;
		uint64_t positiveAiSuppressed;
		uint64_t decreaseApplied;
		uint64_t packetGapNs;
		uint64_t simulatorInternalRateWriteCount;
		uint64_t postDelegationFullCbapGrantCount;
		std::string desiredWriter;
		std::string appliedWriter;
	};
	struct CbapIncumbentRecord {
		uint64_t timeNs;
		uint32_t flowId;
		uint32_t batchId;
		uint64_t sizeBytes;
		uint64_t sentBytes;
		uint64_t ackedBytes;
		uint64_t remainingBytes;
		uint64_t currentRateBps;
		uint64_t targetRateBps;
		uint64_t protectionFloorBps;
		uint64_t timeBelow90TargetNs;
		uint64_t timeBelow80TargetNs;
		uint64_t timeBelow50TargetNs;
		bool finished;
	};
	struct CbapControlMessageRecord {
		uint64_t timeNs;
		uint32_t epoch;
		uint32_t batchId;
		uint64_t activeControlSummaries;
		uint64_t monitoringOnlySummaries;
		uint64_t grants;
	};
	struct CbapScopeBatchRecord {
		uint32_t batchId;
		uint64_t applicationReadyNs;
		uint64_t decisionCompleteNs;
		uint64_t decisionDelayNs;
		uint32_t flowCount;
		uint32_t usedLinkCount;
		bool enabled;
		uint32_t reason;
		uint32_t triggeringLinkCount;
		uint32_t maximumPendingCount;
		double maximumOversubscriptionRatio;
	};
	struct CbapScopeLinkRecord {
		uint32_t batchId;
		uint64_t applicationReadyNs;
		uint64_t newestSummarySampleNs;
		uint64_t newestSummaryDeliveryNs;
		uint32_t linkId;
		uint32_t switchId;
		uint32_t egressPort;
		uint32_t pendingCount;
		uint64_t admissionCapacityBps;
		uint64_t independentAggregateBps;
		uint64_t oversubscriptionBps;
		double oversubscriptionRatio;
		bool enabledOnLink;
		bool preReleaseCausal;
	};
	struct CbapPortSnapshot {
		bool valid;
		uint64_t timestampNs;
		uint32_t linkId;
		uint32_t switchId;
		uint32_t egressPort;
		uint64_t capacityBps;
		uint64_t queueBytes;
		uint64_t ingressBytes;
		uint64_t txBytes;
		uint64_t ecnMarks;
		uint64_t pfcPauseEvents;
		uint64_t pfcResumeEvents;
		uint64_t pfcPauseDurationNs;
		bool localPaused;
		bool downstreamPaused;
		CbapPortSnapshot()
			: valid(false), timestampNs(0), linkId(0), switchId(0),
			  egressPort(0), capacityBps(0), queueBytes(0),
			  ingressBytes(0), txBytes(0), ecnMarks(0),
			  pfcPauseEvents(0), pfcResumeEvents(0),
			  pfcPauseDurationNs(0), localPaused(false),
			  downstreamPaused(false) {}
	};
	struct CbapPortRecord {
		uint64_t sampleTimeNs;
		uint64_t deliveryTimeNs;
		uint32_t linkId;
		uint32_t switchId;
		uint32_t egressPort;
		uint64_t capacityBps;
		uint64_t queueBytes;
		uint64_t previousQueueBytes;
		uint64_t inputBytesDelta;
		uint64_t outputBytesDelta;
		uint64_t ecnMarksDelta;
		uint64_t pfcEventsDelta;
		uint64_t pauseDurationDeltaNs;
		double arrivalRateBps;
		double serviceRateBps;
		double queueGradientBytesPerSecond;
		uint32_t portState;
		uint32_t rootId;
		uint32_t rootReason;
		uint64_t effectiveCapacityBps;
		uint32_t activeControlledFlows;
		uint32_t pendingControlledFlows;
		bool localPaused;
		bool downstreamPaused;
		bool stale;
	};
	struct CbapAdmissionRecord {
		uint64_t planStartNs;
		uint64_t planCompleteNs;
		uint64_t applicationReadyNs;
		uint64_t networkReleaseNs;
		uint32_t batchId;
		uint32_t flowId;
		uint64_t baseRateBps;
		uint64_t admitRateBps;
		uint64_t initialRateBps;
		uint64_t creditBytes;
		uint64_t feedbackHorizonNs;
		uint64_t observedQueueBytes;
		uint64_t packetMarginBytes;
		uint64_t effectiveCapacityBps;
		double floorScale;
		bool independentDiagnostic;
		bool capacityValid;
	};
	struct CbapRateRecord {
		uint64_t timeNs;
		uint32_t epoch;
		uint32_t batchId;
		uint32_t flowId;
		uint32_t phaseBefore;
		uint32_t phaseAfter;
		uint64_t oldRateBps;
		uint64_t targetRateBps;
		uint64_t newRateBps;
		uint32_t reason;
		uint32_t rootId;
		uint64_t feedbackAgeNs;
		uint64_t creditRemainingBytes;
		uint64_t protectionFloorBps;
		uint64_t rebalanceStartNs;
		uint64_t rebalanceEndNs;
		bool staleFeedback;
		bool capacityValid;
	};
	struct CbapAppliedRateAuditRecord {
		uint32_t linkId;
		uint32_t epoch;
		uint64_t capacityBps;
		uint64_t rhoCapacityBps;
		uint64_t effectiveCapacityBps;
		uint64_t plannerGrantSumBps;
		uint64_t targetRateSumBps;
		uint64_t appliedRateSumBps;
		uint64_t actualTxRateSumBps;
		uint64_t backgroundRateBps;
		uint64_t legacyFloorRateBps;
		uint32_t flowsBelowLegacyFloor;
		uint32_t floorClampCount;
		uint64_t rateClampDeltaSumBps;
		uint32_t zeroGrantFlowCount;
		uint32_t pausedZeroGrantCount;
		uint64_t appliedCapacityExcessBps;
		bool appliedCapacityViolation;
		uint64_t actualArrivalExcessBps;
	};
	// One row per replan per link while the delay credit is enabled.  Carries
	// the full control trajectory so the mechanism can be audited from data:
	// which phase the link was in, the measured and derived queue thresholds,
	// the credit or drain that resulted, and the predicted queue one horizon
	// ahead that the credit was truncated against.
	struct CbapDelayCreditRecord {
		uint64_t timestampNs;
		uint32_t linkId;
		uint32_t epoch;
		uint32_t phase;                  // CbapQueuePhase
		uint64_t queueBytes;
		uint64_t qTargetBytes;
		uint64_t qHardBytes;             // the bound in force for this phase
		uint64_t qSyncFloorBytes;
		uint64_t qPredictedBytes;
		uint64_t capacityBps;
		uint64_t creditBps;
		uint64_t drainBps;
		uint64_t totalBudgetBps;
		uint64_t oldShareBps;
		uint64_t newShareBps;
		uint64_t sumTargetBps;
		uint32_t newFlowCount;
		bool creditTruncated;            // prediction check clamped the credit
		bool oversubscribed;             // sumTarget > capacity this epoch
	};
	// One row per handover replan on one link, emitted only when the
	// allocation is (re)computed -- not per packet.  Exists to make the
	// capacity-feasibility rule auditable directly from data:
	//   eta_effective == max(eta_base, eta_feasible)
	//   finalSumTargetBps <= linkCapacityBps
	struct CbapEtaFeasibilityRecord {
		uint64_t timestampNs;
		uint32_t linkId;
		uint32_t epoch;
		double etaBase;
		double etaFeasible;
		double etaEffective;
		uint64_t rOldBps;            // runtime aggregate of the old side
		uint32_t newFlowCount;       // N on THIS link
		uint64_t minRateBps;
		uint64_t residualCapacityBps; // C - R_old (may be 0)
		uint64_t oldTargetSumBps;
		uint64_t newTargetSumBps;
		uint64_t finalSumTargetBps;
		uint64_t linkCapacityBps;
		bool floorBinding;           // did MIN_RATE clamp the new side?
	};
	struct CbapIncreaseRecord {
		uint64_t timestampNs;
		std::string scenario;
		std::string algorithm;
		std::string cbapVersion;
		uint32_t increasePolicy;
		uint32_t flowId;
		uint32_t batchId;
		uint32_t phase;
		uint64_t currentRateBeforeBps;
		uint64_t targetRateBps;
		uint64_t maxRateBps;
		uint64_t fractionalCandidateBps;
		uint64_t absoluteCandidateBps;
		uint64_t selectedDeltaBps;
		uint64_t newRateBps;
		uint32_t stableEpochCount;
		uint64_t feedbackAgeNs;
		bool staleFeedback;
		uint32_t limitingLink;
		uint32_t reason;
	};
	struct CbapFlowRecord {
		uint32_t flowId;
		uint32_t batchId;
		uint64_t applicationReadyNs;
		uint64_t networkReleaseNs;
		uint64_t firstFreshFeedbackNs;
		uint64_t admissionEnterNs;
		uint64_t admissionExitNs;
		uint64_t firstDataTxNs;
		uint64_t firstPostReleaseSampleNs;
		uint64_t firstCompleteFreshFeedbackNs;
		uint64_t initialAdmitRateBps;
		double actualAdmissionMeanRateBps;
		uint64_t bytesSentBeforeFreshFeedback;
		uint64_t rateUpdatesBeforeFirstTx;
		uint64_t ordinaryRateUpdatesDuringAdmission;
		uint64_t emergencyRateUpdatesDuringAdmission;
		uint64_t creditGateEnterNs;
		uint64_t creditGateExitNs;
		bool creditGateActiveAtFinish;
		uint64_t creditRemainingAtAdmissionExit;
		double trackingActualRateBps;
		double trackingCurrentRateBps;
		uint64_t trackingBaseRateBps;
		uint64_t pacingViolations;
		uint64_t estimatedFirstFeedbackNs;
		uint64_t finishNs;
		uint64_t bytesSent;
		uint64_t bytesAcked;
		uint64_t baseRateBps;
		uint64_t admitRateBps;
		uint64_t finalRateBps;
		uint64_t initialCreditBytes;
		uint64_t remainingCreditBytes;
		uint64_t excessBytes;
		uint64_t capacityViolations;
		uint64_t creditViolations;
		uint64_t staleFeedback;
		uint64_t rateIncreases;
		uint64_t rateDecreases;
		uint64_t rateHolds;
		uint64_t reschedules;
		uint64_t fair80Ns;
		uint64_t fair90Ns;
		uint64_t fair95Ns;
	};
	enum CbapTxEventType {
		CBAP_TX_SCHEDULE = 1,
		CBAP_TX_SEND = 2,
		CBAP_TX_RESCHEDULE = 3,
		CBAP_TX_CANCEL_OR_INVALIDATE = 4
	};
	struct CbapTxRecord {
		uint64_t timeNs;
		uint32_t eventType;
		uint32_t flowId;
		uint32_t batchId;
		uint64_t packetSeq;
		uint64_t wireBytes;
		uint32_t phase;
		uint64_t currentRateBps;
		uint64_t targetRateBps;
		uint64_t admitRateBps;
		uint64_t baseRateBps;
		bool creditGateActive;
		uint64_t creditRemainingBytes;
		uint64_t scheduledTimeNs;
		uint64_t actualSendTimeNs;
		uint64_t previousTxTimeNs;
		uint64_t expectedGapNs;
		uint64_t actualGapNs;
		uint32_t rescheduleReason;
	};
	typedef Callback<CbapPortSnapshot, uint32_t>
		CbapPortReadCallback;
	static void ConfigureCbap(const CbapConfig &config,
			const std::vector<BopMultilinkLink> &links,
			const std::map<uint32_t, std::vector<uint32_t> > &flowPaths);
	static void SetCbapPortReadCallback(CbapPortReadCallback callback);
	static void StartCbapCoordinator();
	static const std::vector<CbapPortRecord> &GetCbapPortRecords();
	static const std::vector<CbapAdmissionRecord> &
		GetCbapAdmissionRecords();
	static const std::vector<CbapRateRecord> &GetCbapRateRecords();
	static const std::vector<CbapAppliedRateAuditRecord> &
		GetCbapAppliedRateAuditRecords();
	static const std::vector<CbapEtaFeasibilityRecord> &
		GetCbapEtaFeasibilityRecords();
	static const std::vector<CbapDelayCreditRecord> &
		GetCbapDelayCreditRecords();
	static const std::vector<CbapIncreaseRecord> &
		GetCbapIncreaseRecords();
	static const std::vector<CbapFlowRecord> &GetCbapFlowRecords();
	static const std::vector<CbapTxRecord> &GetCbapTxRecords();
	static uint64_t GetCbapSummaryMessageCount();
	static uint64_t GetCbapGrantMessageCount();
	static const std::vector<CbapScopeBatchRecord> &
		GetCbapScopeBatchRecords();
	static const std::vector<CbapScopeLinkRecord> &
		GetCbapScopeLinkRecords();
	static const std::vector<CbapHandoffBatchRecord> &
		GetCbapHandoffBatchRecords();
	static const std::vector<CbapHandoffFlowRecord> &
		GetCbapHandoffFlowRecords();
	static const std::vector<CbapControllerOwnershipRecord> &
		GetCbapControllerOwnershipRecords();
	static const std::vector<CbapControlMessageRecord> &
		GetCbapControlMessageRecords();
	static const std::vector<CbapEnvelopeLinkRecord> &
		GetCbapEnvelopeLinkRecords();
	static const std::vector<CbapEnvelopeFlowRecord> &
		GetCbapEnvelopeFlowRecords();
	static const std::vector<CbapV20BatchRecord> &
		GetCbapV20BatchRecords();
	static const std::vector<CbapV20FlowRecord> &
		GetCbapV20FlowRecords();
	static const std::vector<CbapSbaController::EventRecord> &
		GetCbapSbaEventRecords();
	static std::vector<CbapIncumbentRecord> GetCbapIncumbentRecords();
	static bool GetCbapScopeApplicationReadyNs(uint32_t batchId,
		uint64_t &applicationReadyNs);

	Ptr<Node> m_node;
	DataRate m_minRate;		//< Min sending rate
	uint32_t m_mtu;
	uint32_t m_cc_mode;
	double m_nack_interval;
	uint32_t m_chunk;
	uint32_t m_ack_interval;
	bool m_backto0;
	bool m_var_win, m_fast_react;
	bool m_rateBound;
	std::vector<RdmaInterfaceMgr> m_nic; // list of running nic controlled by this RdmaHw
	std::unordered_map<uint64_t, Ptr<RdmaQueuePair> > m_qpMap; // mapping from uint64_t to qp
	std::unordered_map<uint64_t, Ptr<RdmaRxQueuePair> > m_rxQpMap; // mapping from uint64_t to rx qp
	std::unordered_map<uint32_t, std::vector<int> > m_rtTable; // map from ip address (u32) to possible ECMP port (index of dev)

	// qp complete callback
	typedef Callback<void, Ptr<RdmaQueuePair> > QpCompleteCallback;
	QpCompleteCallback m_qpCompleteCallback;

	void SetNode(Ptr<Node> node);
	void Setup(QpCompleteCallback cb); // setup shared data and callbacks with the QbbNetDevice
	static uint64_t GetQpKey(uint32_t dip, uint16_t sport, uint16_t pg); // get the lookup key for m_qpMap
	Ptr<RdmaQueuePair> GetQp(uint32_t dip, uint16_t sport, uint16_t pg); // get the qp
	uint32_t GetNicIdxOfQp(Ptr<RdmaQueuePair> qp); // get the NIC index of the qp
	void AddQueuePair(uint64_t size, uint16_t pg, Ipv4Address _sip, Ipv4Address _dip, uint16_t _sport, uint16_t _dport, uint32_t win, uint64_t baseRtt, Callback<void> notifyAppFinish); // add a new qp (new send)
	void DeleteQueuePair(Ptr<RdmaQueuePair> qp);

	Ptr<RdmaRxQueuePair> GetRxQp(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport, uint16_t pg, bool create); // get a rxQp
	uint32_t GetNicIdxOfRxQp(Ptr<RdmaRxQueuePair> q); // get the NIC index of the rxQp
	void DeleteRxQp(uint32_t dip, uint16_t pg, uint16_t dport);

	int ReceiveUdp(Ptr<Packet> p, CustomHeader &ch);
	int ReceiveCnp(Ptr<Packet> p, CustomHeader &ch);
	int ReceiveAck(Ptr<Packet> p, CustomHeader &ch); // handle both ACK and NACK
	int Receive(Ptr<Packet> p, CustomHeader &ch); // callback function that the QbbNetDevice should use when receive packets. Only NIC can call this function. And do not call this upon PFC

	void CheckandSendQCN(Ptr<RdmaRxQueuePair> q);
	int ReceiverCheckSeq(uint32_t seq, Ptr<RdmaRxQueuePair> q, uint32_t size);
	void AddHeader (Ptr<Packet> p, uint16_t protocolNumber);
	static uint16_t EtherToPpp (uint16_t protocol);

	void RecoverQueue(Ptr<RdmaQueuePair> qp);
	void QpComplete(Ptr<RdmaQueuePair> qp);
	void SetLinkDown(Ptr<QbbNetDevice> dev);

	// call this function after the NIC is setup
	void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
	void ClearTable();
	void RedistributeQp();
	void RegisterRoundSchedule(uint32_t dip, uint16_t sport, uint16_t pg,
			uint32_t flowId,
			const std::vector<RdmaQueuePair::CrfmRoundState> &rounds);
	void ReleaseRound(Ptr<RdmaQueuePair> qp, uint32_t roundIndex);

	Ptr<Packet> GetNxtPacket(Ptr<RdmaQueuePair> qp); // get next packet to send, inc snd_nxt
	void PktSent(Ptr<RdmaQueuePair> qp, Ptr<Packet> pkt, Time interframeGap);
	void UpdateNextAvail(Ptr<RdmaQueuePair> qp, Time interframeGap, uint32_t pkt_size);
	// The single authority for what actually paces the wire:
	// min(controller rate, application cap).  Shared by every CC algorithm.
	uint64_t EffectivePacingRateBps(Ptr<RdmaQueuePair> qp) const;
	void ChangeRate(Ptr<RdmaQueuePair> qp, DataRate new_rate);
	// Periodic trace of controller rate vs cap vs effective rate, for flows
	// that have an application cap.  Off by default.
	bool m_appCapTrace;
	/******************************
	 * Mellanox's version of DCQCN
	 *****************************/
	double m_g; //feedback weight
	double m_rateOnFirstCNP; // the fraction of line rate to set on first CNP
	bool m_EcnClampTgtRate;
	double m_rpgTimeReset;
	double m_rateDecreaseInterval;
	uint32_t m_rpgThreshold;
	double m_alpha_resume_interval;
	DataRate m_rai;		//< Rate of additive increase
	DataRate m_rhai;		//< Rate of hyper-additive increase

	// the Mellanox's version of alpha update:
	// every fixed time slot, update alpha.
	void UpdateAlphaMlx(Ptr<RdmaQueuePair> q);
	void ScheduleUpdateAlphaMlx(Ptr<RdmaQueuePair> q);

	// Mellanox's version of CNP receive
	void cnp_received_mlx(Ptr<RdmaQueuePair> q);

	// Mellanox's version of rate decrease
	// It checks every m_rateDecreaseInterval if CNP arrived (m_decrease_cnp_arrived).
	// If so, decrease rate, and reset all rate increase related things
	void CheckRateDecreaseMlx(Ptr<RdmaQueuePair> q);
	void ScheduleDecreaseRateMlx(Ptr<RdmaQueuePair> q, uint32_t delta);

	// Mellanox's version of rate increase
	void RateIncEventTimerMlx(Ptr<RdmaQueuePair> q);
	void RateIncEventMlx(Ptr<RdmaQueuePair> q);
	void FastRecoveryMlx(Ptr<RdmaQueuePair> q);
	void ActiveIncreaseMlx(Ptr<RdmaQueuePair> q);
	void HyperIncreaseMlx(Ptr<RdmaQueuePair> q);

	/***********************
	 * High Precision CC
	 ***********************/
	double m_targetUtil;
	double m_utilHigh;
	uint32_t m_miThresh;
	bool m_multipleRate;
	bool m_sampleFeedback; // only react to feedback every RTT, or qlen > 0
	void HandleAckHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);
	void UpdateRateHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react);
	void UpdateRateHpTest(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react);
	void FastReactHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);

	/************************
	 * Cross-round feedback
	 ************************/
	struct CrfmPendingSchedule {
		uint32_t flowId;
		std::vector<RdmaQueuePair::CrfmRoundState> rounds;
	};
	struct HpFeedbackEstimate {
		bool valid;
		double normalizedLoad;
		uint64_t maximumQueueBytes;
		uint64_t bottleneckCapacityBps;
		uint64_t bottleneckSampleTimeNs;
		HpFeedbackEstimate()
			: valid(false), normalizedLoad(0), maximumQueueBytes(0),
			  bottleneckCapacityBps(0), bottleneckSampleTimeNs(0) {}
	};
	bool m_roundMode;
	double m_bopRho;
	uint64_t m_bopBackgroundBps;
	bool m_bopPhaseStagger;
	uint32_t m_bopPacketBytes;
	uint64_t m_bopBottleneckBps;
	bool m_bopMultilinkEnable;
	double m_bopQcBdpFactor;
	double m_bopQcDefaultTauUs;
	double m_bopQcTauEwmaAlpha;
	uint32_t m_bopQcQueueLimitMode;
	uint32_t m_bopQcPacketMargin;
	bool m_bopQcEnablePhaseStagger;
	uint64_t m_bopQcEcnThresholdBytes;
	double m_bopQbQueueFraction;
	uint32_t m_bopQbPacketMargin;
	bool m_bopQbEnablePhaseStagger;
	uint64_t m_bopQbEcnThresholdBytes;
	uint32_t m_bopQbMaxPacketMargin;
	bool m_bopQbMaxEnablePhaseStagger;
	uint64_t m_bopQbMaxEcnThresholdBytes;
	uint32_t m_finalPrimerFirstFlow;
	std::unordered_map<uint64_t, CrfmPendingSchedule> m_pendingRoundSchedules;
	HpFeedbackEstimate EvaluateHpFeedback(
			Ptr<RdmaQueuePair> qp, CustomHeader &ch, bool fastReact,
			RdmaQueuePair::CrfmRoundState &round) const;
	void HandleAckCrfm(Ptr<RdmaQueuePair> qp, Ptr<Packet> p,
			CustomHeader &ch);
	void RecordRoundAckCompletion(Ptr<RdmaQueuePair> qp);
	void ResetHpccForRound(Ptr<RdmaQueuePair> qp);
	void SetCrfmRate(Ptr<RdmaQueuePair> qp, uint64_t rate);
	void SetRoundStartRate(Ptr<RdmaQueuePair> qp, uint64_t rate);
	void UpdateBopTelemetry(Ptr<RdmaQueuePair> qp, int32_t originRound,
			const HpFeedbackEstimate &estimate, uint64_t feedbackTimeNs);
	void UpdateBopMultilinkTelemetry(Ptr<RdmaQueuePair> qp,
			IntHeader &ih, uint64_t feedbackTimeNs);
	struct RoundGroupMember {
		RdmaHw *hw;
		Ptr<RdmaQueuePair> qp;
		uint32_t roundIndex;
	};
	struct RoundGroupRuntime {
		struct PrtProbeSample {
			bool returned;
			uint64_t sendNs;
			uint64_t queueSampleNs;
			uint64_t ackNs;
			uint64_t queueBytes;
			uint64_t capacityBps;
			PrtProbeSample()
				: returned(false), sendNs(0), queueSampleNs(0),
				  ackNs(0), queueBytes(0), capacityBps(0) {}
		};
		uint32_t participantCount;
		uint32_t roundIndex;
		std::vector<RoundGroupMember> members;
		uint32_t ackCompleted;
		uint64_t barrierNs;
		uint64_t commonReleaseNs;
		uint64_t applicationReadyNs;
		uint64_t earliestReleaseNs;
		bool planScheduled;
		bool planned;
		bool barrierComplete;
		uint64_t queueMaxBytes;
		uint64_t ecnMarks;
		uint64_t pfcEvents;
		uint32_t prtProbeCountSent;
		PrtProbeSample prtProbe[2];
		uint64_t prtRttHatNs;
		uint64_t prtPrimerEcn;
		uint64_t prtCollectiveEcn;
		RoundGroupRuntime();
	};
	static std::map<uint32_t, RoundGroupRuntime> s_roundGroups;
	struct BopMultilinkObservation {
		bool valid;
		uint64_t queueBytes;
		uint64_t sampleTimeNs;
		uint64_t arrivalTimeNs;
		BopMultilinkObservation()
			: valid(false), queueBytes(0), sampleTimeNs(0),
			  arrivalTimeNs(0) {}
	};
	static bool s_bopMultilinkConfigured;
	static std::map<uint32_t, BopMultilinkLink> s_bopMultilinkLinks;
	static std::map<uint32_t, std::vector<uint32_t> >
			s_bopMultilinkFlowPaths;
	static std::map<uint32_t, BopMultilinkObservation>
			s_bopMultilinkObservations;
	static std::map<uint32_t, int64_t> s_bopMultilinkGroupPredecessors;
	static std::map<uint32_t, uint32_t> s_bopMultilinkGroupSuccessors;
	static std::vector<BopMultilinkGroupDecision>
			s_bopMultilinkGroupDecisions;
	static std::vector<BopMultilinkLinkDecision>
			s_bopMultilinkLinkDecisions;
	typedef Callback<uint64_t> RoundQueueReadCallback;
	static RoundQueueReadCallback s_roundQueueRead;
	static void SetRoundQueueReadCallback(RoundQueueReadCallback callback);
	void RegisterRoundGroups(Ptr<RdmaQueuePair> qp);
	static void ScheduleRoundGroup(uint32_t groupId,
			uint64_t commonReleaseNs);
	static void PlanRoundGroup(uint32_t groupId);
	static void SendPrtProbe(uint32_t groupId, uint8_t probeId);
	static void RecordPrtProbeAck(uint32_t groupId, uint8_t probeId,
			IntHeader &ih);
	static bool ReadPrtQueueSample(IntHeader &ih,
			uint64_t &queueBytes, uint64_t &sampleTimeNs,
			uint64_t &capacityBps);
	static void NotifyRoundGroupAck(Ptr<RdmaQueuePair> qp,
			uint32_t roundIndex, uint64_t completionNs);
	static void ObserveRoundBottleneck(uint64_t queueBytes,
			uint64_t ecnDelta, uint64_t pfcDelta);
	struct CbapFlowRuntime {
		RdmaHw *hw;
		Ptr<RdmaQueuePair> qp;
		uint32_t flowId;
		uint32_t batchId;
		uint32_t roundIndex;
		bool planned;
		bool active;
		bool finished;
		CbapFlowRuntime()
			: hw(NULL), qp(NULL), flowId(0), batchId(0),
			  roundIndex(0), planned(false), active(false),
			  finished(false) {}
	};
	// Two-phase hard bound for the queueing-delay credit.  A synchronous
	// N-way batch puts one MTU per sender into the bottleneck port before any
	// controller can act: at N=64 and 1048 B on the wire that is 67 072 B,
	// which already exceeds one BDP.  That burst is structural -- it is present
	// under strict sum(target) <= C too -- so charging it as a credit violation
	// would make even the legacy arm fail.  It must also not become a standing
	// queue target, so the allowance is one-shot: the link starts in
	// SYNC_BURST, and the first time the queue falls to the normal bound it
	// latches into NORMAL for good.
	enum CbapQueuePhase {
		CBAP_QPHASE_SYNC_BURST = 0,
		CBAP_QPHASE_NORMAL = 1
	};
	struct CbapLinkRuntime {
		BopMultilinkLink config;
		bool initialized;
		CbapPortSnapshot previousRaw;
		CbapPortRecord latest;
		uint32_t overloadEpochs;
		uint32_t growthEpochs;
		uint32_t clearStableEpochs;
		uint64_t previousEffectiveCapacityBps;
		uint64_t plannerCapacityBps;
		uint64_t rootDetectTimeNs;
		// --- queueing-delay credit state (diagnostic + phase latch) --------
		CbapQueuePhase queuePhase;
		// True once the queue has actually risen above the normal bound, i.e.
		// the synchronous startup burst has been observed.  Without this the
		// latch fires at the first replan while the queue is still 0.
		bool syncBurstObserved;
		uint64_t qSyncFloorBytes;        // N_active * packet_on_wire_bytes
		uint64_t qHardStartupBytes;      // q_sync_floor + C*hard_budget/8
		uint64_t qHardNormalBytes;       // C * 1 RTT / 8
		uint64_t structuralStartupPeak;  // peak seen while in SYNC_BURST
		uint64_t normalPhasePeak;        // peak seen after latching NORMAL
		uint64_t normalPhaseViolations;  // samples above q_hard_normal in NORMAL
		uint64_t fellBelowNormalNs;      // when the latch happened (0 = never)
		CbapLinkRuntime()
			: initialized(false), overloadEpochs(0), growthEpochs(0),
			  clearStableEpochs(0), previousEffectiveCapacityBps(0),
			  plannerCapacityBps(0), rootDetectTimeNs(0),
			  queuePhase(CBAP_QPHASE_SYNC_BURST), syncBurstObserved(false),
			  qSyncFloorBytes(0),
			  qHardStartupBytes(0), qHardNormalBytes(0),
			  structuralStartupPeak(0), normalPhasePeak(0),
			  normalPhaseViolations(0), fellBelowNormalNs(0) {}
	};
	// Computes the queueing-delay credit for one link.  Declared after
	// CbapLinkRuntime because it takes one by reference.  A pure function of
	// its arguments plus s_cbapConfig, so it is directly testable.
	static uint64_t ComputeDelayCreditBudget(CbapLinkRuntime &runtime,
		uint64_t queueBytes, uint32_t newFlowCount, uint64_t nowNs,
		uint32_t epoch, CbapDelayCreditRecord *out);
	struct CbapScopeBaseFlowRuntime {
		Ptr<RdmaQueuePair> qp;
		uint32_t flowId;
		uint64_t protectionFloorBps;
		uint64_t rebalanceStartNs;
		uint64_t rebalanceEndNs;
		CbapScopeBaseFlowRuntime() : qp(NULL), flowId(0),
			protectionFloorBps(0), rebalanceStartNs(0),
			rebalanceEndNs(0) {}
	};
	struct CbapV20BatchRuntime {
		uint32_t classification;
		uint32_t riskyLinkCount;
		uint64_t releaseNs;
		uint64_t blindWindowNs;
		uint64_t leaseExpiryNs;
		uint64_t firstFreshFeedbackNs;
		uint64_t handoffNs;
		std::string handoffReason;
		bool bypass;
		bool handedOff;
		CbapV20BatchRuntime()
			: classification(CBAP_V20_C2_COMPLEX), riskyLinkCount(0),
			  releaseNs(0), blindWindowNs(0), leaseExpiryNs(0),
			  firstFreshFeedbackNs(0), handoffNs(0),
			  handoffReason("not_evaluated"), bypass(false),
			  handedOff(false) {}
	};
	static CbapConfig s_cbapConfig;
	// Effective release ratio of the most recent handover, after the capacity
	// feasibility floor.  Diagnostic only.
	static double s_cbapLastEtaEffective;
	static bool s_cbapStarted;
	static uint32_t s_cbapEpoch;
	static CbapPortReadCallback s_cbapPortRead;
	static std::map<uint32_t, CbapLinkRuntime> s_cbapLinks;
	static std::map<uint32_t, std::vector<uint32_t> > s_cbapFlowPaths;
	// Batches whose capacity migration has already been planned, so the
	// epoch tick plans each batch exactly once after it releases.
	static std::set<uint32_t> s_cbapSbaMigrationPlanned;
	// Active-set fingerprint at the last migration replan.  Any change --
	// a new batch arriving, a migrating flow finishing, any active-flow
	// churn -- makes the next epoch recompute targets, so released
	// capacity is never left stranded.
	static std::set<uint32_t> s_cbapSbaMigrationActiveSet;
	// Set when a migration deadline lapses; the next epoch replans before
	// stepping any envelope, so an unreachable target is recomputed from
	// the live link state instead of being chased forever.
	static bool s_cbapSbaMigrationReplanPending;
	static void ReplanCbapSbaMigrationTargets(uint64_t nowNs,
			const char *reason);
	static std::map<uint32_t, CbapFlowRuntime> s_cbapFlows;
	static std::map<uint32_t, CbapScopeBaseFlowRuntime>
		s_cbapScopeBaseFlows;
	static std::map<uint32_t, CbapV20BatchRuntime> s_cbapV20Batches;
	static CbapSbaController s_cbapSbaController;
	static std::vector<CbapV20BatchRecord> s_cbapV20BatchRecords;
	static std::vector<CbapV20FlowRecord> s_cbapV20FlowRecords;
	static std::vector<CbapPortRecord> s_cbapPortRecords;
	static std::vector<CbapAdmissionRecord> s_cbapAdmissionRecords;
	static std::vector<CbapRateRecord> s_cbapRateRecords;
	static std::vector<CbapAppliedRateAuditRecord>
		s_cbapAppliedRateAuditRecords;
	static std::vector<CbapEtaFeasibilityRecord>
		s_cbapEtaFeasibilityRecords;
	static std::vector<CbapDelayCreditRecord>
		s_cbapDelayCreditRecords;
	static std::vector<CbapIncreaseRecord> s_cbapIncreaseRecords;
	static std::vector<CbapFlowRecord> s_cbapFlowRecords;
	static std::vector<CbapTxRecord> s_cbapTxRecords;
	static uint64_t s_cbapSummaryMessages;
	static uint64_t s_cbapGrantMessages;
	static std::vector<CbapScopeBatchRecord> s_cbapScopeBatchRecords;
	static std::vector<CbapScopeLinkRecord> s_cbapScopeLinkRecords;
	static std::map<uint32_t, CbapHandoffBatchRecord>
		s_cbapHandoffBatches;
	static std::vector<CbapHandoffFlowRecord> s_cbapHandoffFlowRecords;
	static std::vector<CbapControllerOwnershipRecord>
		s_cbapControllerOwnershipRecords;
	static std::vector<CbapControlMessageRecord>
		s_cbapControlMessageRecords;
	static std::vector<CbapEnvelopeLinkRecord>
		s_cbapEnvelopeLinkRecords;
	static std::vector<CbapEnvelopeFlowRecord>
		s_cbapEnvelopeFlowRecords;
	static std::map<uint64_t, uint64_t> s_cbapEnvelopeLastBudget;
	static uint64_t s_cbapLogicalEnvelopeUpdates;
	static uint64_t s_cbapLogicalEnvelopeBytes;
	static std::map<uint32_t, uint64_t> s_cbapBatchGrantMessages;
	static std::map<uint32_t, uint64_t> s_cbapBatchActiveSummaries;
	static std::map<uint32_t, uint64_t> s_cbapBatchMonitoringSummaries;
	static void PlanCbapBatch(uint32_t groupId);
	static void PlanScopedCbapBatch(uint32_t groupId);
	static void PlanCbapV20Batch(uint32_t groupId);
	static void PlanCbapSbaBatch(uint32_t groupId);
	static std::map<uint32_t, uint64_t> GetCbapSbaAvailableCapacity();
	static void EvaluateCbapSbaReadmission(uint64_t nowNs,
			const std::string &reason);
	static void EvaluateCbapSbaLease(uint64_t nowNs);
	// Capacity migration: plan targets at batch arrival, then advance
	// the per-flow envelope once per control epoch.  See
	// docs/cbap_sba_capacity_migration_design.md.
	static void EvaluateCbapSbaMigration(uint64_t nowNs);
	static void EvaluateCbapV20Batches(uint64_t nowNs);
	static void EvaluateCbapV20Lease(uint32_t groupId);
	static void FinalizeCbapV20Lease(uint32_t groupId);
	static void ExecuteCbapV20Handoff(uint32_t groupId,
			uint64_t nowNs, const std::string &reason);
	static bool IsCbapV20Mode(uint32_t mode);
	static void CbapEpochTick();
	static void DeliverCbapPortSummary(uint32_t linkId,
			CbapPortSnapshot snapshot);
	static void RecomputeCbapTracking();
	static void EvaluateCbapHandoffBatches(uint64_t nowNs);
	static void ExecuteCbapBatchHandoff(uint32_t batchId,
			uint64_t nowNs);
	static void ExecuteCbapBatchDelegation(uint32_t batchId,
			uint64_t nowNs);
	static void ProjectCbapDelegatedEnvelope(uint64_t nowNs);
	static void SetCbapEnvelopeAppliedRate(CbapFlowRuntime &flow,
			uint64_t rateBps);
	bool IsGuardedDelegated(Ptr<RdmaQueuePair> qp) const;
	uint64_t GetDcqcnDesiredOrAppliedRate(Ptr<RdmaQueuePair> qp) const;
	void SetDcqcnDesiredOrAppliedRate(Ptr<RdmaQueuePair> qp,
			uint64_t rateBps, bool decrease, bool positiveIncrease);
	void RecordCbapObservedCnp(Ptr<RdmaQueuePair> qp);
	bool HandoffCbapSbaFlow(Ptr<RdmaQueuePair> qp,
			uint64_t feedbackTimeNs);
	void RecordFirstDcqcnUpdate(Ptr<RdmaQueuePair> qp, bool cnp);
	static void RecordCbapAppliedRateAudit();
	static uint64_t CbapPacketGapNs(uint32_t wireBytes,
			uint64_t rateBps);
	static bool HasCompletePostReleaseFeedback(
			const CbapFlowRuntime &flow, uint64_t &firstSampleNs,
			uint64_t &completeDeliveryNs);
	static bool HasPostReleaseEmergencyEvidence(
			const CbapFlowRuntime &flow, uint32_t &rootId);
	static void ExitCbapAdmission(Ptr<RdmaQueuePair> qp,
			uint64_t completeDeliveryNs);
	static void UpdateCbapTrackingRateIntegral(Ptr<RdmaQueuePair> qp,
			uint64_t nowNs);
	static void RecordCbapTxEvent(Ptr<RdmaQueuePair> qp,
			uint32_t eventType, uint64_t scheduledTimeNs,
			uint64_t actualSendTimeNs, uint64_t previousTxTimeNs,
			uint64_t expectedGapNs, uint64_t actualGapNs,
			uint32_t reason);
	static void FinishCbapFlow(Ptr<RdmaQueuePair> qp);
	static void SetCbapRate(CbapFlowRuntime &flow, uint64_t target,
			uint32_t reason, uint32_t rootId, bool stale);
	static std::map<uint32_t, uint64_t> ComputeCbapProgressiveFill(
			const std::vector<uint32_t> &flowIds,
			const std::map<uint32_t, uint64_t> &linkCapacity,
			const std::map<uint32_t, uint64_t> &initialRates);

	/**********************
	 * TIMELY
	 *********************/
	double m_tmly_alpha, m_tmly_beta;
	uint64_t m_tmly_TLow, m_tmly_THigh, m_tmly_minRtt;
	void HandleAckTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);
	void UpdateRateTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool us);
	void FastReactTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);

	/**********************
	 * DCTCP
	 *********************/
	DataRate m_dctcp_rai;
	void HandleAckDctcp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);

	/*********************
	 * HPCC-PINT
	 ********************/
	uint32_t pint_smpl_thresh;
	void SetPintSmplThresh(double p);
	void HandleAckHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch);
	void UpdateRateHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react);
};

} /* namespace ns3 */

#endif /* RDMA_HW_H */
