#include "cbap-sba.h"

#include <cstdlib>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

using ns3::CbapSbaController;

static const uint64_t GBPS = UINT64_C(1000000000);

static void Require(bool condition, const std::string &message)
{
	if (!condition)
		throw std::runtime_error(message);
}

static CbapSbaController::FlowInput Flow(uint32_t id,
		const std::vector<uint32_t> &path, uint64_t maximum = 40 * GBPS)
{
	CbapSbaController::FlowInput flow;
	flow.flowId = id;
	flow.path = path;
	flow.maximumRateBps = maximum;
	return flow;
}

static void TestSharedLinkAtomicGrant()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows;
	for (uint32_t id = 0; id < 4; ++id)
		flows.push_back(Flow(id, std::vector<uint32_t>(1, 10)));
	std::map<uint32_t, uint64_t> available;
	available[10] = 10 * GBPS; // 40 Gbps - 30 Gbps background.
	std::map<uint32_t, uint64_t> grant =
		controller.AdmitBatch(1, 1000, flows, available);
	uint64_t sum = 0;
	for (uint32_t id = 0; id < 4; ++id) {
		Require(grant[id] == 2500000000ULL, "symmetric grant is not 2.5 Gbps");
		sum += grant[id];
	}
	Require(sum <= available[10], "atomic shared-link grant exceeds 10 Gbps");
	Require(controller.CheckConservation(1, available),
		"shared-link conservation check failed");
}

static void TestTwoBottlenecksPathMin()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows;
	flows.push_back(Flow(0, std::vector<uint32_t>(1, 1)));
	std::vector<uint32_t> both;
	both.push_back(1); both.push_back(2);
	flows.push_back(Flow(1, both));
	flows.push_back(Flow(2, std::vector<uint32_t>(1, 2)));
	std::map<uint32_t, uint64_t> available;
	available[1] = 10 * GBPS;
	available[2] = 20 * GBPS;
	std::map<uint32_t, uint64_t> grant =
		controller.AdmitBatch(2, 2000, flows, available);
	Require(grant[0] == 5 * GBPS && grant[1] == 5 * GBPS &&
		grant[2] == 15 * GBPS, "two-bottleneck max-min grants are wrong");
	Require(grant[1] <= available[1] && grant[1] <= available[2],
		"path-min constraint failed");
	Require(grant[0] + grant[1] <= available[1] &&
		grant[1] + grant[2] <= available[2],
		"two-bottleneck conservation failed");
}

static void TestZeroGrantHoldAndReadmission()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows(1, Flow(7,
		std::vector<uint32_t>(1, 3)));
	std::map<uint32_t, uint64_t> unavailable;
	unavailable[3] = 0;
	controller.AdmitBatch(3, 3000, flows, unavailable);
	const CbapSbaController::FlowState *flow = controller.GetFlow(7);
	Require(flow && flow->state == CbapSbaController::ADMISSION_HOLD,
		"zero grant did not enter HOLD");
	Require(flow->grantRateBps == 0 && flow->appliedRateBps == 0,
		"zero grant created a sending rate");
	std::map<uint32_t, uint64_t> recovered;
	recovered[3] = 8 * GBPS;
	std::vector<uint32_t> admitted = controller.ReadmitHeld(3, 4000,
		recovered, "telemetry_update");
	flow = controller.GetFlow(7);
	Require(admitted.size() == 1 && admitted[0] == 7 &&
		flow->state == CbapSbaController::STARTUP_SENDING,
		"held flow was not readmitted");
	Require(flow->appliedRateBps == 8 * GBPS && flow->appliedRateBps != 1,
		"readmission used fake pacing");
}

static void TestSingleHandoffUsesAppliedRate()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows(1, Flow(9,
		std::vector<uint32_t>(1, 4), 12 * GBPS));
	std::map<uint32_t, uint64_t> available;
	available[4] = 7 * GBPS;
	controller.AdmitBatch(4, 5000, flows, available);
	uint64_t handoff = 0;
	Require(!controller.OnActionableFeedback(9, 4999, &handoff),
		"pre-release feedback was accepted");
	Require(controller.OnActionableFeedback(9, 6000, &handoff),
		"first valid feedback did not hand off");
	const CbapSbaController::FlowState *flow = controller.GetFlow(9);
	Require(handoff == 7 * GBPS && handoff == flow->appliedRateBps,
		"DCQCN initial rate differs from real applied rate");
	Require(!controller.OnActionableFeedback(9, 7000, &handoff) &&
		flow->handoffCount == 1, "flow handed off more than once");
}

static void TestHeldFlowNeverEntersDcqcn()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows(1, Flow(11,
		std::vector<uint32_t>(1, 5)));
	std::map<uint32_t, uint64_t> available;
	available[5] = 0;
	controller.AdmitBatch(5, 8000, flows, available);
	uint64_t handoff = 123;
	Require(!controller.OnActionableFeedback(11, 9000, &handoff),
		"held flow entered DCQCN");
	const CbapSbaController::FlowState *flow = controller.GetFlow(11);
	Require(flow->state == CbapSbaController::ADMISSION_HOLD &&
		flow->handoffCount == 0 && flow->handoffRateBps == 0 &&
		flow->appliedRateBps == 0 && flow->appliedRateBps != 1,
		"held flow acquired zero/fake rate-control state");
}

static void TestNoCbapWriteAfterHandoff()
{
	CbapSbaController controller;
	std::vector<CbapSbaController::FlowInput> flows(1, Flow(13,
		std::vector<uint32_t>(1, 6)));
	std::map<uint32_t, uint64_t> available;
	available[6] = 6 * GBPS;
	controller.AdmitBatch(6, 10000, flows, available);
	uint64_t handoff = 0;
	Require(controller.OnActionableFeedback(13, 11000, &handoff),
		"handoff setup failed");
	Require(!controller.TrySetStartupAppliedRate(13, 2 * GBPS),
		"CBAP modified a handed-off flow");
	const CbapSbaController::FlowState *flow = controller.GetFlow(13);
	Require(flow->state == CbapSbaController::DCQCN_OWNED &&
		flow->appliedRateBps == handoff,
		"post-handoff ownership or rate changed");
}

int main()
{
	struct Test { const char *name; void (*run)(); } tests[] = {
		{"shared_link_atomic_grant", &TestSharedLinkAtomicGrant},
		{"two_bottlenecks_path_min", &TestTwoBottlenecksPathMin},
		{"zero_grant_hold_readmission", &TestZeroGrantHoldAndReadmission},
		{"single_handoff_applied_rate", &TestSingleHandoffUsesAppliedRate},
		{"held_flow_never_dcqcn", &TestHeldFlowNeverEntersDcqcn},
		{"no_cbap_write_after_handoff", &TestNoCbapWriteAfterHandoff}
	};
	try {
		for (uint32_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) {
			tests[i].run();
			std::cout << "PASS " << tests[i].name << '\n';
		}
	} catch (const std::exception &error) {
		std::cerr << "FAIL " << error.what() << '\n';
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
