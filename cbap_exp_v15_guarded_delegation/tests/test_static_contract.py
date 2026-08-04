#!/usr/bin/env python3
import csv,os,re
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
hw=open(os.path.join(ROOT,"simulation/src/point-to-point/model/rdma-hw.h")).read()
cc=open(os.path.join(ROOT,"simulation/src/point-to-point/model/rdma-hw.cc")).read()
assert "CC_MODE_CBAP_FULL_SCOPED_RATEFLOOR_FIX = 25" in hw
assert "CC_MODE_CBAP_FULL_STABLE_HANDOFF = 26" in hw
assert "CC_MODE_CBAP_FULL_GUARDED_DELEGATION = 27" in hw
assert "CBAP_DELEGATED_ENVELOPE = 8" in open(os.path.join(ROOT,"simulation/src/point-to-point/model/rdma-queue-pair.h")).read()
assert "q->mlx.m_targetRate = q->m_rate = m_rateOnFirstCNP * q->m_rate" in cc
assert "q->m_rate = std::max(m_minRate" in cc
assert "ProjectCbapDelegatedEnvelope" in cc and "ENVELOPE_PROJECTOR" in cc
assert "pathScale = std::min(pathScale, scales[path[hop]])" in cc
assert "if (isStale && budget > previous) budget = previous" in cc
base=os.path.join(ROOT,"cbap_exp_v15_guarded_delegation/configs")
assert len(list(csv.DictReader(open(os.path.join(base,"semantic_manifest.csv")))))==8
assert len(list(csv.DictReader(open(os.path.join(base,"validation_manifest.csv")))))==42
print("PASS frozen modes, ownership, stale guard, and manifests")
