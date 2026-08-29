#include <cstdio>
#include "cbap-sba.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>

namespace ns3 {

CbapSbaController::FlowState::FlowState()
	: batchId(0), flowId(0), releaseTimeNs(0), maximumRateBps(0),
	  grantRateBps(0), appliedRateBps(0), firstFeedbackTimeNs(0),
	  handoffRateBps(0), handoffCount(0), state(COLLECTING)
{
}

void CbapSbaController::Reset()
{
	m_flows.clear();
	m_events.clear();
}

const char *CbapSbaController::StateName(State state)
{
	switch (state) {
	case COLLECTING: return "COLLECTING";
	case ADMISSION_HOLD: return "ADMISSION_HOLD";
	case STARTUP_SENDING: return "STARTUP_SENDING";
	case DCQCN_OWNED: return "DCQCN_OWNED";
	case FINISHED: return "FINISHED";
	}
	return "INVALID";
}

std::string CbapSbaController::FormatPath(
		const std::vector<uint32_t> &path)
{
	std::ostringstream out;
	for (uint32_t i = 0; i < path.size(); ++i) {
		if (i)
			out << ';';
		out << path[i];
	}
	return out.str();
}

std::string CbapSbaController::FormatCapacity(
		const std::map<uint32_t, uint64_t> &capacity)
{
	std::ostringstream out;
	bool first = true;
	for (std::map<uint32_t, uint64_t>::const_iterator it = capacity.begin();
			it != capacity.end(); ++it) {
		if (!first)
			out << ';';
		first = false;
		out << it->first << ':' << it->second;
	}
	return out.str();
}

void CbapSbaController::Record(const FlowState &flow,
		const std::string &transition,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		const std::string &holdReason,
		const std::string &readmissionReason)
{
	EventRecord event;
	event.batchId = flow.batchId;
	event.flowId = flow.flowId;
	event.releaseTimeNs = flow.releaseTimeNs;
	event.path = FormatPath(flow.path);
	event.availableCapacity = FormatCapacity(availableCapacity);
	event.grantRateBps = flow.grantRateBps;
	event.appliedRateBps = flow.appliedRateBps;
	event.stateTransition = transition;
	event.holdReason = holdReason;
	event.readmissionReason = readmissionReason;
	event.firstFeedbackTimeNs = flow.firstFeedbackTimeNs;
	event.handoffRateBps = flow.handoffRateBps;
	m_events.push_back(event);
}

std::map<uint32_t, uint64_t> CbapSbaController::ProgressiveFill(
		const std::vector<uint32_t> &flowIds,
		const std::map<uint32_t, uint64_t> &capacity) const
{
	std::map<uint32_t, long double> rates;
	std::set<uint32_t> active;
	for (uint32_t i = 0; i < flowIds.size(); ++i) {
		std::map<uint32_t, FlowState>::const_iterator flow =
			m_flows.find(flowIds[i]);
		if (flow == m_flows.end() || flow->second.path.empty())
			throw std::logic_error("SBA progressive fill references unknown flow");
		rates[flowIds[i]] = 0;
		if (flow->second.maximumRateBps > 0)
			active.insert(flowIds[i]);
	}

	for (uint32_t iteration = 0;
			!active.empty() && iteration <= flowIds.size(); ++iteration) {
		long double step = std::numeric_limits<long double>::max();
		std::map<uint32_t, long double> linkStep;
		for (std::map<uint32_t, uint64_t>::const_iterator link =
				capacity.begin(); link != capacity.end(); ++link) {
			uint32_t count = 0;
			long double used = 0;
			for (uint32_t i = 0; i < flowIds.size(); ++i) {
				const FlowState &flow = m_flows.find(flowIds[i])->second;
				if (std::find(flow.path.begin(), flow.path.end(), link->first) ==
						flow.path.end())
					continue;
				used += rates[flow.flowId];
				if (active.count(flow.flowId))
					count++;
			}
			if (count == 0)
				continue;
			long double remaining = std::max((long double)0,
				(long double)link->second - used);
			linkStep[link->first] = remaining / count;
			step = std::min(step, linkStep[link->first]);
		}
		std::map<uint32_t, long double> maximumStep;
		for (std::set<uint32_t>::const_iterator id = active.begin();
				id != active.end(); ++id) {
			maximumStep[*id] = std::max((long double)0,
				(long double)m_flows.find(*id)->second.maximumRateBps - rates[*id]);
			step = std::min(step, maximumStep[*id]);
		}
		if (!std::isfinite((double)step) || step < 0)
			throw std::logic_error("SBA progressive fill produced invalid step");
		if (step > 0) {
			for (std::set<uint32_t>::const_iterator id = active.begin();
					id != active.end(); ++id)
				rates[*id] += step;
		}
		std::set<uint32_t> frozen;
		for (std::set<uint32_t>::const_iterator id = active.begin();
				id != active.end(); ++id) {
			if (maximumStep[*id] <= step + 0.5L)
				frozen.insert(*id);
			const std::vector<uint32_t> &path = m_flows.find(*id)->second.path;
			for (uint32_t hop = 0; hop < path.size(); ++hop)
				if (linkStep.count(path[hop]) &&
						linkStep[path[hop]] <= step + 0.5L)
					frozen.insert(*id);
		}
		if (frozen.empty())
			break;
		for (std::set<uint32_t>::const_iterator id = frozen.begin();
				id != frozen.end(); ++id)
			active.erase(*id);
	}

	std::map<uint32_t, uint64_t> result;
	for (uint32_t i = 0; i < flowIds.size(); ++i) {
		const FlowState &flow = m_flows.find(flowIds[i])->second;
		long double bounded = std::min((long double)flow.maximumRateBps,
			std::max((long double)0, rates[flow.flowId]));
		result[flow.flowId] = (uint64_t)std::floor(bounded);
	}
	return result;
}

void CbapSbaController::SetCoreInitialRelease(bool enable, double rhoInit)
{
	m_coreInitialRelease = enable;
	// Clamp rather than trust the caller: a ratio outside [0,1] would either
	// take capacity away from the batch or release more than the old side has.
	m_initialReleaseRatio = rhoInit < 0.0 ? 0.0 : (rhoInit > 1.0 ? 1.0 : rhoInit);
}

const std::map<uint32_t, uint64_t> &
CbapSbaController::GetLastAdmitOldApplied() const
{
	return m_lastAdmitOldApplied;
}

std::map<uint32_t, uint64_t> CbapSbaController::AdmitBatch(
		uint32_t batchId, uint64_t releaseTimeNs,
		const std::vector<FlowInput> &flows,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		double oldBatchWeight, double newBatchWeight)
{
	if (flows.empty())
		throw std::invalid_argument("SBA batch is empty");
	std::map<uint32_t, uint64_t> residual = availableCapacity;
	// Aggregate applied rate of the old side, per link, recorded before it is
	// subtracted.  The initial-release allocator needs R_old_observed itself,
	// not just the headroom that survives it.
	std::map<uint32_t, uint64_t> oldAppliedByLink;
	for (std::map<uint32_t, FlowState>::const_iterator existing =
			m_flows.begin(); existing != m_flows.end(); ++existing) {
		// Lifecycle guard: an installed-but-unreleased flow (COLLECTING)
		// holds no network rate and must never enter the old-side census.
		// (Its appliedRateBps is 0 today; the guard makes the invariant
		// explicit instead of incidental.)
		if (existing->second.state == FINISHED ||
				existing->second.state == ADMISSION_HOLD ||
				existing->second.state == COLLECTING)
			continue;
		for (uint32_t hop = 0; hop < existing->second.path.size(); ++hop) {
			uint64_t &capacity = residual[existing->second.path[hop]];
			oldAppliedByLink[existing->second.path[hop]] +=
				existing->second.appliedRateBps;
			capacity = capacity > existing->second.appliedRateBps ?
				capacity - existing->second.appliedRateBps : 0;
		}
	}
	m_lastAdmitOldApplied = oldAppliedByLink;
	// SBA_LIFECYCLE: admission-time lifecycle census (observability only).
	{
		uint32_t nCol = 0, nHold = 0, nStart = 0, nOwn = 0, nFin = 0;
		for (std::map<uint32_t, FlowState>::const_iterator it =
				m_flows.begin(); it != m_flows.end(); ++it) {
			switch (it->second.state) {
			case COLLECTING: nCol++; break;
			case ADMISSION_HOLD: nHold++; break;
			case STARTUP_SENDING: nStart++; break;
			case DCQCN_OWNED: nOwn++; break;
			case FINISHED: nFin++; break;
			}
		}
		std::printf("SBA_LIFECYCLE batch=%u release_ns=%llu installed=%u "
			"collecting=%u hold=%u startup=%u dcqcn_owned=%u finished=%u "
			"new_batch=%u rho_init=%.4f\n",
			batchId, (unsigned long long)releaseTimeNs,
			(unsigned)m_flows.size(), nCol, nHold, nStart, nOwn, nFin,
			(unsigned)flows.size(), (double)m_initialReleaseRatio);
		for (std::map<uint32_t, uint64_t>::const_iterator l =
				oldAppliedByLink.begin(); l != oldAppliedByLink.end(); ++l)
			std::printf("SBA_LIFECYCLE_LINK batch=%u link=%u old_applied=%llu "
				"available=%llu\n", batchId, l->first,
				(unsigned long long)l->second,
				(unsigned long long)(availableCapacity.count(l->first) ?
					availableCapacity.find(l->first)->second : 0));
		std::fflush(stdout);
	}
	std::vector<uint32_t> ids;
	for (uint32_t i = 0; i < flows.size(); ++i) {
		if (flows[i].path.empty() || m_flows.count(flows[i].flowId))
			throw std::invalid_argument("invalid or duplicate SBA flow");
		std::set<uint32_t> uniquePath;
		for (uint32_t hop = 0; hop < flows[i].path.size(); ++hop) {
			if (!availableCapacity.count(flows[i].path[hop]) ||
					!uniquePath.insert(flows[i].path[hop]).second)
				throw std::invalid_argument("invalid SBA path");
		}
		FlowState state;
		state.batchId = batchId;
		state.flowId = flows[i].flowId;
		state.releaseTimeNs = releaseTimeNs;
		state.path = flows[i].path;
		state.maximumRateBps = flows[i].maximumRateBps;
		m_flows[state.flowId] = state;
		ids.push_back(state.flowId);
	}

	// Scheme-1 batch-to-batch reclaim redesign: aggregate 50:50 (by
	// default) target weighting between this new batch and every
	// pre-existing ("old") flow sharing a link, per-link.  All
	// pre-existing batches are pooled into a single old weight rather
	// than each holding its own share (see design notes).
	bool hasOldFlows = false;
	for (std::map<uint32_t, FlowState>::const_iterator existing =
			m_flows.begin();
			existing != m_flows.end() && !hasOldFlows; ++existing) {
		if (existing->second.batchId != batchId &&
				existing->second.state != FINISHED &&
				existing->second.state != ADMISSION_HOLD)
			hasOldFlows = true;
	}
	std::map<uint32_t, uint64_t> newBatchResidual = residual;
	if (m_coreInitialRelease) {
		// Core mode: work-conserving initial release.  The old side gives up
		// rho_init of the rate it is actually using, and the batch receives the
		// untouched headroom plus exactly that release, so
		//     R_old_init + R_new_init = C
		// leaving no capacity hole while a batch has demand.  No 0.5 weight is
		// applied here or anywhere else on this path.
		//
		//     released_init = rho_init * R_old_observed
		//     R_new_init    = (C - R_old_observed) + released_init
		//
		// residual already equals C - R_old_observed at this point, which is why
		// the release is simply added to it rather than recomputed from C.
		for (std::map<uint32_t, uint64_t>::iterator link =
				newBatchResidual.begin(); link != newBatchResidual.end(); ++link) {
			uint64_t oldApplied = oldAppliedByLink.count(link->first) ?
				oldAppliedByLink[link->first] : 0;
			uint64_t released = (uint64_t)std::floor(
				(long double)m_initialReleaseRatio * (long double)oldApplied);
			link->second += released;
			// Never plan above the link itself.
			if (availableCapacity.count(link->first) &&
					link->second > availableCapacity.find(link->first)->second)
				link->second = availableCapacity.find(link->first)->second;
		}
	} else if (hasOldFlows && oldBatchWeight > 0.0 && newBatchWeight > 0.0) {
		// legacy_50_50 control arm only.  Retained for comparison; not part of
		// the core algorithm.
		double share = newBatchWeight / (oldBatchWeight + newBatchWeight);
		for (std::map<uint32_t, uint64_t>::iterator link =
				newBatchResidual.begin(); link != newBatchResidual.end(); ++link)
			link->second = (uint64_t)std::floor(
				(long double)link->second * share);
	}
	std::map<uint32_t, uint64_t> grants = ProgressiveFill(ids, newBatchResidual);
	for (uint32_t i = 0; i < ids.size(); ++i) {
		FlowState &flow = m_flows[ids[i]];
		flow.grantRateBps = grants[flow.flowId];
		flow.appliedRateBps = flow.grantRateBps;
		if (flow.grantRateBps == 0) {
			flow.state = ADMISSION_HOLD;
			Record(flow, "COLLECTING->ADMISSION_HOLD", residual,
				"zero_available_capacity", "");
		} else {
			flow.state = STARTUP_SENDING;
			Record(flow, "COLLECTING->STARTUP_SENDING", residual,
				"", "");
		}
	}
	// The budget ProgressiveFill was actually handed is newBatchResidual, so
	// that is what the batch's grants must respect.  On the legacy path
	// newBatchResidual is derived from residual by a <=1 weight, so this is
	// identical to the previous check there.
	if (!CheckConservation(batchId, newBatchResidual))
		throw std::logic_error("SBA atomic admission violates capacity");
	// Core mode hands the batch capacity the old side is releasing, so
	// sum(grants) <= C - R_old_observed no longer holds and must not be
	// asserted.  The property that does hold is planned-state conservation:
	//     sum(grants) + (1 - rho_init) * R_old_observed <= C
	// i.e. the batch plus the rate the old side is being left with fits the
	// link.  Checked per link, and only for links the old side actually uses.
	if (m_coreInitialRelease) {
		for (std::map<uint32_t, uint64_t>::const_iterator link =
				availableCapacity.begin();
				link != availableCapacity.end(); ++link) {
			uint64_t oldApplied = oldAppliedByLink.count(link->first) ?
				oldAppliedByLink.find(link->first)->second : 0;
			uint64_t released = (uint64_t)std::floor(
				(long double)m_initialReleaseRatio * (long double)oldApplied);
			uint64_t oldRetained = oldApplied > released ?
				oldApplied - released : 0;
			uint64_t batchSum = 0;
			for (uint32_t i = 0; i < ids.size(); ++i) {
				const FlowState &flow = m_flows[ids[i]];
				if (std::find(flow.path.begin(), flow.path.end(),
						link->first) == flow.path.end())
					continue;
				batchSum += flow.grantRateBps;
			}
			// Tolerate the per-flow floor() rounding in ProgressiveFill, which
			// can only ever round the batch down, never up.
			// Occupancy bound.  availableCapacity is payload-domain while
			// oldApplied is wire-domain (census-proven: available ==
			// C*1000/1048 exactly); comparing the plan against available alone
			// therefore rejects EVERY admission on a saturated link by the
			// framing overhead, independent of batch size.  The invariant that
			// is actually safe and domain-consistent: the planned state must
			// never exceed max(available, observed occupancy) -- strict when
			// under-loaded (bit-identical to the old check there), and
			// plan-never-worsens when saturated (batchSum + oldRetained ==
			// oldApplied by construction when residual == 0).  The wire/payload
			// mixing inside grant budgets is documented debt, not hidden.
			const uint64_t occupancyBound = link->second > oldApplied ?
				link->second : oldApplied;
			std::printf("SBA_LIFECYCLE_CHECK batch=%u link=%u batch_sum=%llu "
				"old_retained=%llu available=%llu bound=%llu margin=%lld\n",
				batchId, link->first, (unsigned long long)batchSum,
				(unsigned long long)oldRetained,
				(unsigned long long)link->second,
				(unsigned long long)occupancyBound,
				(long long)((int64_t)occupancyBound + (int64_t)ids.size() -
					(int64_t)batchSum - (int64_t)oldRetained));
			std::fflush(stdout);
			if (batchSum + oldRetained > occupancyBound + ids.size())
				throw std::logic_error(
					"SBA initial release violates planned capacity");
		}
	}
	return grants;
}

std::vector<uint32_t> CbapSbaController::ReadmitHeld(uint32_t batchId,
		uint64_t nowNs,
		const std::map<uint32_t, uint64_t> &availableCapacity,
		const std::string &reason)
{
	(void)nowNs;
	std::map<uint32_t, uint64_t> residual = availableCapacity;
	std::vector<uint32_t> held;
	for (std::map<uint32_t, FlowState>::const_iterator it = m_flows.begin();
			it != m_flows.end(); ++it) {
		const FlowState &flow = it->second;
		if (flow.state == FINISHED)
			continue;
		if (flow.batchId == batchId && flow.state == ADMISSION_HOLD) {
			held.push_back(flow.flowId);
			continue;
		}
		if (flow.state == ADMISSION_HOLD)
			continue;
		// A handed-off flow is no longer rate-controlled by SBA, but its last
		// real applied rate remains an admission reservation until telemetry
		// or completion releases that capacity.
		for (uint32_t hop = 0; hop < flow.path.size(); ++hop) {
			uint64_t &capacity = residual[flow.path[hop]];
			capacity = capacity > flow.appliedRateBps ?
				capacity - flow.appliedRateBps : 0;
		}
	}
	if (held.empty())
		return held;
	std::map<uint32_t, uint64_t> grants = ProgressiveFill(held, residual);
	std::vector<uint32_t> admitted;
	for (uint32_t i = 0; i < held.size(); ++i) {
		FlowState &flow = m_flows[held[i]];
		if (grants[flow.flowId] == 0)
			continue;
		flow.grantRateBps = grants[flow.flowId];
		flow.appliedRateBps = grants[flow.flowId];
		flow.state = STARTUP_SENDING;
		Record(flow, "ADMISSION_HOLD->STARTUP_SENDING", residual, "",
			reason);
		admitted.push_back(flow.flowId);
	}
	return admitted;
}

bool CbapSbaController::OnActionableFeedback(uint32_t flowId,
		uint64_t feedbackTimeNs, uint64_t *handoffRateBps)
{
	std::map<uint32_t, FlowState>::iterator found = m_flows.find(flowId);
	if (found == m_flows.end())
		return false;
	FlowState &flow = found->second;
	if (flow.state != STARTUP_SENDING || flow.appliedRateBps == 0 ||
			feedbackTimeNs < flow.releaseTimeNs)
		return false;
	flow.firstFeedbackTimeNs = feedbackTimeNs;
	flow.handoffRateBps = flow.appliedRateBps;
	flow.handoffCount++;
	flow.state = DCQCN_OWNED;
	Record(flow, "STARTUP_SENDING->DCQCN_OWNED",
		std::map<uint32_t, uint64_t>(), "", "first_actionable_feedback");
	if (handoffRateBps)
		*handoffRateBps = flow.handoffRateBps;
	return true;
}

bool CbapSbaController::Finish(uint32_t flowId, uint64_t nowNs)
{
	(void)nowNs;
	std::map<uint32_t, FlowState>::iterator found = m_flows.find(flowId);
	if (found == m_flows.end() || found->second.state == FINISHED)
		return false;
	FlowState &flow = found->second;
	std::string transition = std::string(StateName(flow.state)) + "->FINISHED";
	flow.state = FINISHED;
	flow.appliedRateBps = 0;
	Record(flow, transition, std::map<uint32_t, uint64_t>(), "",
		"flow_completed_capacity_release");
	return true;
}

bool CbapSbaController::TrySetStartupAppliedRate(uint32_t flowId,
		uint64_t rateBps)
{
	std::map<uint32_t, FlowState>::iterator found = m_flows.find(flowId);
	if (found == m_flows.end() || found->second.state != STARTUP_SENDING ||
			rateBps == 0)
		return false;
	found->second.grantRateBps = rateBps;
	found->second.appliedRateBps = rateBps;
	return true;
}

bool CbapSbaController::HoldForInvalidAppliedRate(uint32_t flowId)
{
	std::map<uint32_t, FlowState>::iterator found = m_flows.find(flowId);
	if (found == m_flows.end() ||
			found->second.state != STARTUP_SENDING)
		return false;
	FlowState &flow = found->second;
	flow.grantRateBps = 0;
	flow.appliedRateBps = 0;
	flow.state = ADMISSION_HOLD;
	Record(flow, "STARTUP_SENDING->ADMISSION_HOLD",
		std::map<uint32_t, uint64_t>(), "invalid_nonpositive_applied_rate", "");
	return true;
}

bool CbapSbaController::ObserveDcqcnAppliedRate(uint32_t flowId,
		uint64_t rateBps)
{
	std::map<uint32_t, FlowState>::iterator found = m_flows.find(flowId);
	if (found == m_flows.end() || found->second.state != DCQCN_OWNED)
		return false;
	// Observation is used only to account capacity for held peers.  It does
	// not write the QP, change ownership, or reopen the SBA state machine.
	found->second.appliedRateBps = rateBps;
	return true;
}

const CbapSbaController::FlowState *CbapSbaController::GetFlow(
		uint32_t flowId) const
{
	std::map<uint32_t, FlowState>::const_iterator found = m_flows.find(flowId);
	return found == m_flows.end() ? NULL : &found->second;
}

const std::vector<CbapSbaController::EventRecord> &
CbapSbaController::GetEvents() const
{
	return m_events;
}

bool CbapSbaController::CheckConservation(uint32_t batchId,
		const std::map<uint32_t, uint64_t> &availableCapacity) const
{
	for (std::map<uint32_t, uint64_t>::const_iterator link =
			availableCapacity.begin(); link != availableCapacity.end(); ++link) {
		uint64_t sum = 0;
		for (std::map<uint32_t, FlowState>::const_iterator flow =
				m_flows.begin(); flow != m_flows.end(); ++flow) {
			if (flow->second.batchId != batchId ||
					flow->second.state == FINISHED ||
					std::find(flow->second.path.begin(), flow->second.path.end(),
						link->first) == flow->second.path.end())
				continue;
			if (std::numeric_limits<uint64_t>::max() - sum <
					flow->second.grantRateBps)
				return false;
			sum += flow->second.grantRateBps;
		}
		if (sum > link->second)
			return false;
	}
	return true;
}

} // namespace ns3
