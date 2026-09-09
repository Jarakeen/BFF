# Phase 13 Provider Workload Shared Decision Checkpoint

**Date:** 2026-09-09  
**Branch:** `phase13.2`  
**Validated head:** `fcde9b4c460e220e6f766295294d8a7594810ca3`

## Scope

This checkpoint validates the shared provider-workload decision seam used by Comp Maker and Team Optimization.

The shared UI support now materializes `TeamProviderWorkloadDecisionResult` once from candidate evidence, applies encounter/role policy to that same authoritative decision result, renders from the stored decision state, and clears candidate/decision/policy state together when team analysis is invalidated.

This preserves the intended boundary:

```text
saved team / build candidates
        ↓
canonical provider workload projections
        ↓
Pareto / frontier decision analysis
        ↓
explicit encounter / role policy selection
        ↓
shared Comp Maker / Team Optimization explanation
```

No universal weighted workload score is introduced. Provider GCD time, resources, Ultimate, bar space, applications, and primary-role displacement remain separate dimensions.

## Regression coverage

User-reported Windows / Python 3.12.4 focused checkpoint:

- `ui/tests/test_team_provider_workload_support.py`
- `services/tests/test_team_provider_workload_policy_explanation.py`
- `services/tests/test_team_provider_workload_explanation_service.py`
- `services/tests/test_team_provider_workload_policy_service.py`
- `services/tests/test_team_provider_workload_decision_service.py`
- `services/tests/test_team_provider_workload_frontier_service.py`

**Result: 37 passed in 3.04s.**

The UI support regression includes a guard proving rendering/policy changes reuse the already-materialized decision rather than silently recomputing the frontier.

## Boundary

This checkpoint does not claim Phase 13 completion. The next integration step remains feeding explicit encounter/provider assignment policy and real saved team rotation plans into this shared candidate-generation/decision seam, while preserving exact Character → Build → Team identity and explicit unresolved evidence.
