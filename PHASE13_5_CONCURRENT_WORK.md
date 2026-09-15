# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — PERSISTENCE COMPLETE / HANDOFF READY

Raid Engine now persists canonical `RaidPlan` snapshots and the focused persistence/bridge gate is green.

### Verified persistence checkpoint

User-reported focused gate: **32 passed in 5.49s**.

Stable files:

- `services/raid_plan_repository.py`
- `services/tests/test_raid_plan_repository.py`
- `services/raid_plan_catalog_descriptors.py`
- `services/tests/test_raid_plan_catalog_registration.py`
- `ui/raid_plan_persistence_page.py`
- `ui/tests/test_raid_plan_persistence_page.py`
- `ui/raid_engine_dashboard_support.py` now instantiates `RaidPlanPersistencePage`

Persistence behavior:

- Storage target is versioned `raid_plans.json` under the normal app data directory.
- Multiple named Raid Plans are supported.
- Save / Load / Delete are visible on the Raid Plan page.
- Persistence owns **trial-specific planning decisions only**.
- It does not create or mutate Personnel, Character, Saved Build, Team, ESO Logs, or canonical encounter identity.
- No database reset or database migration is used.
- Hidden plan-owned state that is not yet editable in the UI, including assignments, notes, stable references, and triggered responsibilities, is preserved across Load -> edit visible fields -> Save.

### Rotation workstream handoff

Roto/Rotation may now treat Raid Plan persistence as a stable upstream contract and continue consuming `RaidPlan` / `RaidPlanMember` through the existing effective-build/runtime bridges.

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

Recent Rotation commits observed during the persistence slice include:

- `a75ddec7` Fix runtime application RaidPlanMember test fixture
- `cd435e44` Test runtime application installer contract
- `818ee869` Install runtime application support on Rotation page
- `0afdf190` Install runtime application on Rotation pages
- `fba01456` Install runtime observation support at app startup

Those changes remain intact. Raid Plan persistence intentionally avoided Rotation-owned files.

## Next Raid Plan slice

The persistence slice is done. The next Raid Plan work is assignment editing/ownership on the Raid Plan surface, reusing existing assignment behavior rather than duplicating it. Rotation is free to continue against the stable persistence boundary while that separate UI/assignment slice proceeds.
