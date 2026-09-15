# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ASSIGNMENT SLICE ACTIVE

Raid Engine now persists canonical `RaidPlan` snapshots and the focused persistence/bridge gate is green.

### Verified persistence checkpoint

User-reported focused gate: **32 passed in 5.49s**.

Stable persistence files:

- `services/raid_plan_repository.py`
- `services/tests/test_raid_plan_repository.py`
- `services/raid_plan_catalog_descriptors.py`
- `services/tests/test_raid_plan_catalog_registration.py`
- `ui/raid_plan_persistence_page.py`
- `ui/tests/test_raid_plan_persistence_page.py`

Persistence behavior:

- Storage target is versioned `raid_plans.json` under the normal app data directory.
- Multiple named Raid Plans are supported.
- Save / Load / Delete are visible on the Raid Plan page.
- Persistence owns **trial-specific planning decisions only**.
- It does not create or mutate Personnel, Character, Saved Build, Team, ESO Logs, or canonical encounter identity.
- No database reset or database migration is used.
- Hidden plan-owned state that is not yet editable in the UI is preserved across Load -> edit visible fields -> Save.

### Current Raid Plan assignment slice

The original roadmap remains unchanged:

```text
Persistence -> Assignments -> Coverage -> Rotation -> Optimizer Adviser
```

This slice exposes the existing `RaidPlanMember.primary_assignment` and `secondary_assignment` fields on the Raid Plan surface.

Rules for this slice:

- Assignments remain **plan-owned**, not Roster/Team-owned.
- Reuse the same assignment vocabulary/autocomplete already used by the Roster Assignments UI.
- Do not write Raid Plan assignment edits into `roster_assignment_context`.
- Do not reorganize Raid Plans around bosses or encounters.
- Boss/encounter overrides remain a later contextual layer.
- No structural change to `models/raid_plan.py` is expected.
- Rotation may continue consuming the stable `RaidPlanMember` assignment fields as upstream context.

Expected assignment-slice files:

- new Raid Plan assignment-aware UI subclass and focused tests
- `ui/raid_engine_dashboard_support.py` route update to use that page
- `FEATURES.md` wording update

### Rotation workstream handoff

Roto/Rotation may treat Raid Plan persistence as a stable upstream contract and continue consuming `RaidPlan` / `RaidPlanMember` through the existing effective-build/runtime bridges.

Do **not** add a second Raid Plan persistence path inside Rotation.

If Rotation needs a structural change to `models/raid_plan.py`, coordinate it first because that model shape now round-trips through durable storage and repository tests. Additive consumer-side adapters are preferred over changing persistence-owned shape.

### Ownership boundary

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Recent Rotation activity is continuing on separate runtime/mechanics files. Raid Plan assignment work should avoid Rotation-owned files and will re-fetch shared route files immediately before writes.
