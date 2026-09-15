# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — OPTIMIZER ADVISER READY FOR VALIDATION

Raid Engine persists canonical `RaidPlan` snapshots, exposes plan-owned Primary/Secondary assignments, hands the exact current Raid Plan into Coverage, exposes a selected-chair handoff into Rotation, and now has a read-only Optimizer Adviser handoff for the whole current plan.

### Verified checkpoints

- Persistence/bridge gate: **32 passed in 5.49s**
- Assignment/persistence/bridge gate: **30 passed in 3.22s**
- Coverage/persistence/bridge gate: **34 passed in 4.22s**
- Coverage support-set + Rotation handoff gate: **35 passed in 3.23s**

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

Coverage:
- `services/raid_plan_coverage_scope_service.py`
- `services/tests/test_raid_plan_coverage_scope_service.py`
- `services/tests/test_raid_plan_coverage_catalog_registration.py`
- `ui/coverage_raid_plan_scope_support.py`
- `ui/raid_plan_coverage_page.py`
- `ui/tests/test_raid_plan_coverage_support.py`

Coverage support-set evidence:
- `services/raid_unique_support_set_capability_service.py`
- reviewed proc/activation sets such as Powerful Assault remain `Conditional`; equipment presence never claims uptime
- full raid-facing group/unique-set catalog is visible in Raid Plan Coverage

Rotation handoff:
- `ui/raid_plan_rotation_handoff_support.py`
- `ui/raid_plan_rotation_page.py`
- selected chairs resolve exact saved builds and enter Rotation through the existing canonical context seam
- encounter selection remains owned by Rotation
- no Rotation engine/service ownership moved into RaidPlan

### Optimizer Adviser slice — READY FOR VALIDATION

New/changed contracts:
- `services/raid_plan_optimizer_adviser_service.py`
- `services/tests/test_raid_plan_optimizer_adviser_service.py`
- `services/tests/test_raid_plan_optimizer_adviser_catalog_registration.py`
- `ui/raid_plan_optimizer_adviser_support.py`
- `ui/raid_plan_adviser_page.py`
- `ui/tests/test_raid_plan_optimizer_adviser_support.py`
- `ui/raid_engine_dashboard_support.py` now instantiates `RaidPlanAdviserPage`
- prior assignment/Coverage/Rotation route-contract tests advance through the Adviser-aware subclass

Adviser contract:
- Raid Plan's former **Open Optimizer** action is presented as **Open Adviser**.
- The exact current RaidPlan is passed to the existing Optimization workspace.
- The existing team editor is populated from exact resolved Raid Plan saved builds with `autofill=False`; the Adviser does not choose replacement players/builds.
- Advice is rendered in a dedicated **Optimizer Adviser** card and is read-only.
- Finding categories are explicit: `blocker`, `coverage_gap`, `conditional`, `redundancy`, `data_gap`.
- Open/unresolved chairs are plan blockers.
- Missing proven required static coverage is a coverage-gap review item, not an automatic team edit.
- Conditional capabilities require trigger/rotation review; they do not claim uptime.
- Multiple proven static providers are flagged only for intentional-redundancy review.
- Canonical capability-resolution debt is labeled `data_gap` and explicitly says not to change a player's build solely to clear Foundry's missing evidence.
- Reviewed unique support-set presence such as Powerful Assault feeds Adviser conditional findings through the same equipment-count semantics as Coverage.
- No recommendation is automatically applied or persisted.
- No structural change was made to `models/raid_plan.py`.
- No database migration/reset occurred.
- No Rotation engine/service file changed for the Adviser slice.

### Roadmap

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence, Assignments, Coverage, and Rotation are stable. Optimizer Adviser is implemented and **awaiting its focused validation gate** before the roadmap is marked complete.

### Rotation workstream coordination

Roto/Rotation remains an independent downstream consumer. The Adviser consumes RaidPlan/Coverage/build evidence and does not alter Rotation runtime or canonical generation contracts.

Do **not** add a second Raid Plan persistence, assignment, Coverage, effective-build, Rotation context, or optimization-advice authority.

Ownership remains:

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Coverage = consumer of exact selected Raid Plan builds + explicit planning labels
Rotation = consumer of exact resolved Raid Plan chair/effective build + live encounter/policy
Optimizer Adviser = read-only consumer of RaidPlan + canonical build/Coverage evidence
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE / INDEPENDENT

Roto may continue its mechanics/runtime work independently. No Rotation-owned engine file or persisted `RaidPlan` shape changed in the Adviser slice.
