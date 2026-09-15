# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ROTATION HANDOFF READY FOR VALIDATION

Raid Engine persists canonical `RaidPlan` snapshots, exposes plan-owned Primary/Secondary assignments, hands the exact current Raid Plan into Coverage, and now exposes a selected-chair handoff into the existing Rotation workspace.

### Verified checkpoints

- Persistence/bridge gate: **32 passed in 5.49s**
- Assignment/persistence/bridge gate: **30 passed in 3.22s**
- Coverage/persistence/bridge gate: **34 passed in 4.22s**

### Stable prior Raid Plan slices

Persistence:
- `services/raid_plan_repository.py`
- `services/tests/test_raid_plan_repository.py`
- `services/raid_plan_catalog_descriptors.py`
- `services/tests/test_raid_plan_catalog_registration.py`
- `ui/raid_plan_persistence_page.py`
- `ui/tests/test_raid_plan_persistence_page.py`

Assignments:
- `ui/raid_plan_assignment_page.py`
- `ui/tests/test_raid_plan_assignment_page.py`

Coverage:
- `services/raid_plan_coverage_scope_service.py`
- `services/tests/test_raid_plan_coverage_scope_service.py`
- `services/tests/test_raid_plan_coverage_catalog_registration.py`
- `ui/coverage_raid_plan_scope_support.py`
- `ui/raid_plan_coverage_page.py`
- `ui/tests/test_raid_plan_coverage_support.py`

### Rotation handoff slice implemented

New/changed files:
- `ui/raid_plan_rotation_handoff_support.py`
- `ui/raid_plan_rotation_page.py`
- `ui/tests/test_raid_plan_rotation_handoff_support.py`
- `ui/tests/test_raid_plan_rotation_page.py`
- `ui/raid_engine_dashboard_support.py` now instantiates `RaidPlanRotationPage`
- existing assignment/coverage route-contract tests advanced through the new subclass

Contract:
- Raid Plan exposes a **Rotation / Execution** card with one selected chair and **Open Rotation**.
- The selected chair must already have an exact saved build; unresolved/missing/ambiguous build ownership fails closed.
- Rotation's visible Character/Build selectors are aligned to the exact resolved Raid Plan build.
- The existing Rotation canonical context provider remains the owner of encounter/evidence/generation policy.
- The Raid Plan wrapper pins build reads to the exact selected build, then delegates to the existing `RaidPlanRotationContextBridge`.
- Encounter selection remains inside Rotation. Trial identity is never fabricated into a boss/encounter id.
- The bridge freezes the exact build as a `raid_plan` `EffectiveBuildSnapshot` and carries matching encounter-scoped triggered responsibilities.
- Primary/Secondary assignment labels are retained as provenance only. They are not converted into build adjustment labels or runtime timings.
- No Rotation engine/service file was modified for this slice.
- No structural change was made to `models/raid_plan.py`.
- No database migration/reset is involved.

### Roadmap remains unchanged

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence, Assignments, and Coverage are stable. The visible Raid Plan -> Rotation handoff is implemented and awaiting its focused validation gate before the Rotation slice is marked stable.

### Rotation workstream coordination

Roto/Rotation remains the downstream consumer. This handoff intentionally wraps Roto's existing canonical context-provider seam rather than editing its generation/runtime engine.

Do **not** add a second Raid Plan persistence, assignment, Coverage, effective-build, or Rotation context authority.

If Roto needs a structural change to `models/raid_plan.py`, coordinate it first because that model shape round-trips through durable storage and repository tests. Prefer additive consumer-side adapters.

Ownership remains:

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Coverage = consumer of exact selected Raid Plan builds + explicit planning labels
Rotation = consumer of exact resolved Raid Plan chair/effective build + live encounter/policy
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Roto may continue its mechanics/runtime work independently. The Raid Plan handoff has not changed Rotation-owned engine files or the persisted RaidPlan shape. Treat this handoff as **ready for validation**, not stable, until the focused test gate is reported green.
