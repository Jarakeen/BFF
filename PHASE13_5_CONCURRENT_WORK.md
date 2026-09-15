# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ROTATION HANDOFF COMPLETE / STABLE

Raid Engine persists canonical `RaidPlan` snapshots, exposes plan-owned Primary/Secondary assignments, hands the exact current Raid Plan into Coverage, and exposes a selected-chair handoff into the existing Rotation workspace.

### Verified checkpoints

- Persistence/bridge gate: **32 passed in 5.49s**
- Assignment/persistence/bridge gate: **30 passed in 3.22s**
- Coverage/persistence/bridge gate: **34 passed in 4.22s**
- Coverage support-set + Rotation handoff gate: **35 passed in 3.23s**

### Stable Raid Plan slices

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

### Coverage support-set evidence correction — STABLE

Coverage now treats exact equipped support-set thresholds as static capability evidence without claiming runtime uptime.

Stable contract:
- `services/raid_unique_support_set_capability_service.py` projects exact equipped-piece thresholds into static Coverage evidence.
- The service reuses `SavedBuildCapabilityService._active_set_counts`, including active-bar/two-handed weapon semantics, instead of inventing another gear-counting rule.
- Reviewed proc/activation sets such as Powerful Assault remain `Conditional`; equipment presence never claims uptime.
- `services/raid_unique_support_set_catalog.py` records reviewed piece thresholds (5-piece sets, 2-piece monster sets, 1-piece mythics).
- `ui/coverage_group_effect_catalog_support.py` overlays that evidence after canonical saved-build capability analysis.
- `ui/coverage_raid_plan_scope_support.py` renders the full raid-facing group/unique-set catalog rather than only `DEFAULT_RAID_COVERAGE_PROFILE`.
- Raid Plan assignment labels remain planning intent only.
- No `RaidPlan` model, Rotation engine, database, or persistence contract changed.

### Rotation handoff — STABLE

Stable files/contracts:
- `ui/raid_plan_rotation_handoff_support.py`
- `ui/raid_plan_rotation_page.py`
- `ui/tests/test_raid_plan_rotation_handoff_support.py`
- `ui/tests/test_raid_plan_rotation_page.py`
- `ui/raid_engine_dashboard_support.py` instantiates `RaidPlanRotationPage`
- existing assignment/coverage route-contract tests advance through the Rotation-aware subclass

Contract:
- Raid Plan exposes a **Rotation / Execution** card with one selected chair and **Open Rotation**.
- The selected chair must already have an exact saved build; unresolved/missing/ambiguous build ownership fails closed.
- Rotation's visible Character/Build selectors are aligned to the exact resolved Raid Plan build.
- The existing Rotation canonical context provider remains the owner of encounter/evidence/generation policy.
- The Raid Plan wrapper pins build reads to the exact selected build, then delegates to the existing `RaidPlanRotationContextBridge`.
- Encounter selection remains inside Rotation. Trial identity is never fabricated into a boss/encounter id.
- The bridge freezes the exact build as a `raid_plan` `EffectiveBuildSnapshot` and carries matching encounter-scoped triggered responsibilities.
- Primary/Secondary assignment labels are retained as provenance only. They are not converted into build adjustment labels or runtime timings.
- No Rotation engine/service file was modified for this handoff.
- No structural change was made to `models/raid_plan.py`.
- No database migration/reset is involved.

### Roadmap remains unchanged

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence, Assignments, Coverage, and the Raid Plan -> Rotation handoff are complete/stable. **Optimizer Adviser is next for the Raid Plan workstream.**

### Rotation workstream coordination

Roto/Rotation remains the downstream consumer. The stable handoff intentionally wraps Roto's existing canonical context-provider seam rather than editing its generation/runtime engine.

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

## Rotation workstream — ACTIVE / INDEPENDENT

Roto may continue its mechanics/runtime work independently. The Raid Plan handoff is now stable upstream behavior and does not change Rotation-owned engine files or the persisted `RaidPlan` shape.
