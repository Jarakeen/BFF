# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ASSIGNMENT SLICE READY FOR VALIDATION

Raid Engine persists canonical `RaidPlan` snapshots and now has a plan-owned Primary/Secondary assignment editing surface. The prior persistence/bridge gate is green; the new assignment slice is awaiting its focused pytest gate.

### Verified persistence checkpoint

User-reported focused gate: **32 passed in 5.49s**.

Stable persistence files:

- `services/raid_plan_repository.py`
- `services/tests/test_raid_plan_repository.py`
- `services/raid_plan_catalog_descriptors.py`
- `services/tests/test_raid_plan_catalog_registration.py`
- `ui/raid_plan_persistence_page.py`
- `ui/tests/test_raid_plan_persistence_page.py`

### Assignment slice implemented

The original roadmap remains unchanged:

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

New/changed files:

- `ui/raid_plan_assignment_page.py`
- `ui/tests/test_raid_plan_assignment_page.py`
- `ui/raid_engine_dashboard_support.py` now instantiates `RaidPlanAssignmentPage`

Behavior:

- The Raid Plan page exposes a separate **Assignments** card for all 12 chairs.
- Each chair has editable Primary and Secondary assignment controls.
- Controls use case-insensitive contains autocomplete and the same user-facing assignment vocabulary as the existing Roster Assignments surface.
- Assignment values write only to `RaidPlanMember.primary_assignment` and `RaidPlanMember.secondary_assignment`.
- Existing member identity, build selection, notes, triggered responsibilities, plan status, and team metadata are preserved.
- Clearing a visible assignment clears that plan-owned field intentionally.
- Unknown/nonexistent seat keys cannot create new Raid Plan members.
- This slice does **not** write to `RosterAssignmentContextService` or `roster_assignment_context`.
- No database migration or reset is involved.
- No structural change was made to `models/raid_plan.py`.
- Boss/encounter overrides remain a later contextual layer; Raid Plans were not reorganized around encounters.

### Rotation workstream handoff

Roto/Rotation may continue consuming the existing `RaidPlanMember.primary_assignment` and `secondary_assignment` fields. The assignment slice does not alter Rotation contracts or persisted model shape.

Do **not** add a second Raid Plan persistence path inside Rotation.

If Rotation needs a structural change to `models/raid_plan.py`, coordinate it first because that model shape round-trips through durable storage and repository tests. Additive consumer-side adapters are preferred.

### Ownership boundary

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Rotation is continuing on separate runtime/mechanics files. The Raid Plan assignment slice intentionally avoided Rotation-owned files.

### Assignment validation gate

Do not treat this assignment slice as stable until the focused assignment/persistence/bridge tests are green. Once the user reports that gate, update this note to mark the assignment slice complete and hand it off as stable upstream context.
