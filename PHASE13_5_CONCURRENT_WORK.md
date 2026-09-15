# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — COVERAGE SLICE COMPLETE / STABLE

Raid Engine persists canonical `RaidPlan` snapshots, exposes plan-owned Primary/Secondary assignments, and hands the exact current Raid Plan into Coverage for static build auditing.

### Verified checkpoints

- Persistence/bridge gate: **32 passed in 5.49s**
- Assignment/persistence/bridge gate: **30 passed in 3.22s**
- Coverage/persistence/bridge gate: **34 passed in 4.22s**

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
- `ui/raid_engine_dashboard_support.py` instantiates `RaidPlanCoveragePage`

### Coverage contract

- **Check Plan Coverage** sends the current `RaidPlan` directly to Coverage.
- Team Optimization is not an intermediate authority.
- Selected builds resolve through fail-closed `RaidPlanSavedBuildResolutionService`.
- Coverage audits only successfully resolved plan-selected builds.
- Missing/ambiguous chairs remain explicitly unresolved.
- Zero resolved builds never falls back to all saved builds.
- Primary/Secondary assignment labels populate Planned Provider/Backup only on exact coverage-effect display-name matches.
- Assignment labels remain planning intent, not proof of static availability or uptime.
- Static capability evidence remains owned by Coverage/SavedBuildCapability services.
- No `models/raid_plan.py` shape change, database migration, or reset occurred.

### Roadmap remains unchanged

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence, Assignments, and Coverage are complete/stable. Rotation is next.

### Rotation workstream handoff

Roto/Rotation may treat Raid Plan persistence, assignments, and Coverage scope as stable upstream context. Rotation remains a consumer and should not add a second Raid Plan persistence, assignment, or Coverage authority.

If Rotation needs a structural change to `models/raid_plan.py`, coordinate it first because that model shape round-trips through durable storage and repository tests. Prefer additive consumer-side adapters.

Ownership remains:

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Coverage = consumer of exact selected Raid Plan builds + explicit planning labels
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Rotation may now proceed against the stable upstream Raid Plan contract. The next Raid Plan integration target is making the visible Raid Plan hand one selected chair's exact resolved effective build and assignment context into Rotation, without moving Rotation ownership into RaidPlan persistence.
