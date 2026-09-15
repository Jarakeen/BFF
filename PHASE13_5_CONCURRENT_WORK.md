# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — COVERAGE SLICE READY FOR VALIDATION

Raid Engine persists canonical `RaidPlan` snapshots, exposes plan-owned Primary/Secondary assignments, and now hands the exact current Raid Plan into Coverage for static build auditing.

### Verified checkpoints

User-reported persistence/bridge gate: **32 passed in 5.49s**.

User-reported assignment/persistence/bridge gate: **30 passed in 3.22s**.

### Stable prior slices

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

### Coverage slice implemented

New/changed files:

- `services/raid_plan_coverage_scope_service.py`
- `services/tests/test_raid_plan_coverage_scope_service.py`
- `services/raid_plan_catalog_descriptors.py` now registers `raid_plan.coverage_scope`
- `services/tests/test_raid_plan_coverage_catalog_registration.py`
- `ui/coverage_raid_plan_scope_support.py`
- `ui/raid_plan_coverage_page.py`
- `ui/tests/test_raid_plan_coverage_support.py`
- `ui/raid_engine_dashboard_support.py` now instantiates `RaidPlanCoveragePage`

Behavior:

- Raid Plans expose **Check Plan Coverage**.
- The current `RaidPlan` is handed directly to Coverage; Team Optimization is not an intermediate authority.
- Each selected Raid Plan build is resolved through the existing fail-closed `RaidPlanSavedBuildResolutionService`.
- Coverage audits exactly the successfully resolved selected builds.
- Missing or ambiguous selected builds remain explicitly unresolved and are reported in the Coverage scope/summary.
- A Raid Plan with zero resolved builds does **not** fall back to all saved builds.
- Coverage gets a distinct `raid_plan` build-scope entry.
- Primary and Secondary assignment labels populate **Planned Provider** and **Backup** only when they exactly match a coverage-effect display name.
- Assignment labels are planning intent only and never prove static availability or uptime.
- Static capability evidence remains owned by the existing Coverage/SavedBuildCapability services.
- No structural change was made to `models/raid_plan.py`.
- No database migration/reset is involved.
- Boss/encounter overrides remain a later contextual layer; the original roadmap was not changed.

### Roadmap remains unchanged

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence and Assignments are stable. Coverage is implemented and awaiting its focused validation gate before being marked stable.

### Rotation workstream handoff

Roto/Rotation may continue consuming the stable Raid Plan persistence and assignment fields. The Coverage slice is a sibling consumer and does not alter Rotation contracts, runtime state, or persisted model shape.

Do **not** add a second Raid Plan persistence, assignment, or Coverage authority inside Rotation.

If Rotation needs a structural change to `models/raid_plan.py`, coordinate it first because that model shape round-trips through durable storage and repository tests. Additive consumer-side adapters are preferred.

### Ownership boundary

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Coverage = consumer of exact selected Raid Plan builds + explicit planning labels
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Rotation is continuing on separate runtime/mechanics files. The Raid Plan Coverage slice intentionally avoided Rotation-owned files.

### Coverage validation gate

Do not treat this Coverage slice as stable until the focused Raid Plan scope/catalog/UI/persistence/bridge tests are green. Once the user reports that gate, update this note to mark Coverage complete/stable and hand it off as upstream context.
