# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ASSIGNMENT SLICE COMPLETE / STABLE

Raid Engine persists canonical `RaidPlan` snapshots and now has a plan-owned Primary/Secondary assignment editing surface. The persistence, assignment, and existing bridge tests are green.

### Verified checkpoints

User-reported persistence/bridge gate: **32 passed in 5.49s**.

User-reported assignment/persistence/bridge gate: **30 passed in 3.22s**.

Stable persistence files:

- `services/raid_plan_repository.py`
- `services/tests/test_raid_plan_repository.py`
- `services/raid_plan_catalog_descriptors.py`
- `services/tests/test_raid_plan_catalog_registration.py`
- `ui/raid_plan_persistence_page.py`
- `ui/tests/test_raid_plan_persistence_page.py`

Stable assignment files:

- `ui/raid_plan_assignment_page.py`
- `ui/tests/test_raid_plan_assignment_page.py`
- `ui/raid_engine_dashboard_support.py` instantiates `RaidPlanAssignmentPage`

### Roadmap remains unchanged

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

Persistence and Assignments are now complete/stable for this roadmap slice. Coverage is the next Raid Plan integration target.

### Assignment behavior

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

Roto/Rotation may now treat the Raid Plan assignment slice as stable upstream context and continue consuming `RaidPlanMember.primary_assignment` and `secondary_assignment` through additive consumer-side adapters.

Do **not** add a second Raid Plan assignment or persistence authority inside Rotation.

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

Rotation is continuing on separate runtime/mechanics files. The completed Raid Plan assignment slice intentionally avoided Rotation-owned files.
