# v1.3 to v1.4 semantic difference

CBAP-v1.3 (mode 25) keeps full CBAP ownership until completion. Its scope,
Admission Hold, progressive filling, startup credit, incumbent floor and decay,
freshness, increase/decrease, Recovery, exact grant pacing, and zero-rate pause
semantics are frozen.

CBAP-v1.4 (mode 26) runs those same mechanisms during startup. Its only control
difference is a one-time batch handoff after the preregistered stable predicate.
Afterward original DCQCN owns the live rate. There is no handback.

Mode 25 receives read-only shadow logging to identify when the v1.4 predicate
would first have become true. This logging does not write QP rate, credit, phase,
schedule, or DCQCN state.
