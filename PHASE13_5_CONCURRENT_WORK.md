# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — PERSISTENCE SLICE STABLE

Raid Engine is being remodeled around persistent `RaidPlan` snapshots.

### Stable persistence checkpoint

- Repository: `services/raid_plan_repository.py`
- Repository tests: `services/tests/test_raid_plan_repository.py`
- Catalog descriptor: `services/raid_plan_catalog_descriptors.py`
- Catalog registration flows through `services/comp_maker_catalog_descriptors.py` into the canonical `SERVICE_CATALOG`.
- Visible save/load page: `ui/raid_plan_persistence_page.py`
- Main Raid Engine registration now instantiates `RaidPlanPersistencePage`.
- Storage target: versioned `raid_plans.json` under the normal app data directory.
- Persistence owns **trial-specific planning decisions only**.
- It does not create/mutate Personnel, Character, Saved Build, Team, or canonical encounter identity.
- No database reset or migration is used.
- Hidden plan-owned state that is not yet editable in the UI (assignments, notes, stable references, triggered responsibilities) is preserved across Load -> edit visible fields -> Save.

### Rotation workstream guidance

Rotation may **consume** `RaidPlan` / `RaidPlanMember` and the existing effective-build/runtime bridges. It should not add its own Raid Plan persistence or duplicate plan ownership.

The persistence files above are now stable enough to consume. Avoid changing their persisted shape without coordination. In particular, if Rotation needs a field or contract change in `models/raid_plan.py`, coordinate before changing the model because that shape now round-trips through durable storage.

### Ownership boundary

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Recent Rotation commits observed during this persistence slice include:

- `a75ddec7` Fix runtime application RaidPlanMember test fixture
- `cd435e44` Test runtime application installer contract
- `818ee869` Install runtime application support on Rotation page
- `0afdf190` Install runtime application on Rotation pages
- `fba01456` Install runtime observation support at app startup

Those changes remain intact. Raid Plan persistence intentionally avoided Rotation-owned files.

## Next Raid Plan slice

After the persistence gate is green, the next planned work is assignment editing/ownership on the Raid Plan surface, reusing existing assignment behavior rather than duplicating it.
