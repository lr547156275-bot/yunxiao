#ifndef CBAP_SBA_H
#define CBAP_SBA_H

#include <stdint.h>

#include <map>
#include <string>
#include <vector>

namespace ns3 {

// Startup Batch Admission is deliberately a short-lived owner.  It assigns
// one atomic batch grant, holds zero-grant flows without inventing a rate,
// and permanently relinquishes a positive-grant flow on its first valid
// actionable feedback.
class CbapSbaController {
public:
	enum State {
		COLLECTING = 0,
		ADMISSION_HOLD = 1,
		STARTUP_SENDING = 2,
		DCQCN_OWNED = 3,
		FINISHED = 4
	};

	struct FlowInput {
		uint32_t flowId;
		std::vector<uint32_t> path;
		uint64_t maximumRateBps;
	};

	struct FlowState {
		uint32_t batchId;
		uint32_t flowId;
		uint64_t releaseTimeNs;
		std::vector<uint32_t> path;
		uint64_t maximumRateBps;
		uint64_t grantRateBps;
		uint64_t appliedRateBps;
		uint64_t firstFeedbackTimeNs;
		uint64_t handoffRateBps;
		uint32_t handoffCount;
		State state;
		FlowState();
	};

	struct EventRecord {
		uint32_t batchId;
		uint32_t flowId;
		uint64_t releaseTimeNs;
		std::string path;
		std::string availableCapacity;
		uint64_t grantRateBps;
		uint64_t appliedRateBps;
		std::string stateTransition;
		std::string holdReason;
		std::string readmissionReason;
		uint64_t firstFeedbackTimeNs;
		uint64_t handoffRateBps;
	};

	void Reset();
	std::map<uint32_t, uint64_t> AdmitBatch(uint32_t batchId,
		uint64_t releaseTimeNs, const std::vector<FlowInput> &flows,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		double oldBatchWeight = 1.0, double newBatchWeight = 1.0);
	std::vector<uint32_t> ReadmitHeld(uint32_t batchId, uint64_t nowNs,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		const std::string &reason);
	bool OnActionableFeedback(uint32_t flowId, uint64_t feedbackTimeNs,
		uint64_t *handoffRateBps);
	bool Finish(uint32_t flowId, uint64_t nowNs);
	bool TrySetStartupAppliedRate(uint32_t flowId, uint64_t rateBps);
	bool HoldForInvalidAppliedRate(uint32_t flowId);
	bool ObserveDcqcnAppliedRate(uint32_t flowId, uint64_t rateBps);

	const FlowState *GetFlow(uint32_t flowId) const;
	const std::vector<EventRecord> &GetEvents() const;
	bool CheckConservation(uint32_t batchId,
		const std::map<uint32_t, uint64_t> &availableCapacity) const;
	static const char *StateName(State state);

private:
	std::map<uint32_t, FlowState> m_flows;
	std::vector<EventRecord> m_events;

	std::map<uint32_t, uint64_t> ProgressiveFill(
		const std::vector<uint32_t> &flowIds,
		const std::map<uint32_t, uint64_t> &capacity) const;
	void Record(const FlowState &flow, const std::string &transition,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		const std::string &holdReason,
		const std::string &readmissionReason);
	static std::string FormatPath(const std::vector<uint32_t> &path);
	static std::string FormatCapacity(
		const std::map<uint32_t, uint64_t> &capacity);
};

} // namespace ns3

#endif
