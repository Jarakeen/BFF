# Phase 13.5 Concurrent Work Coordination

This file is a short-lived coordination note for parallel Phase 13.5 workstreams. It is not architecture authority and should be removed when the concurrent work settles.

## Raid Plan workstream — ACTIVE

Current owner is remodeling Raid Engine around persistent `RaidPlan` snapshots.

### Current checkpoint

- Latest Raid Plan persistence commit at time of note: `e2fbb6fb176483fdd7a69d3e23e996d295fd5e23`
- New file: `services/raid_plan_repository.py`
- Storage target: versioned `raid_plans.json` under the normal app data directory.
- Persistence owns **trial-specific planning decisions only**.
- It must not create/mutate Personnel, Character, Saved Build, Team, or canonical encounter identity.
- No database reset or migration is planned for this slice.

### Files this workstream expects to touch next

- `services/tests/test_raid_plan_repository.py`
- service-catalog descriptor/bootstrap for Raid Plan persistence
- Raid Plan UI save/load controls, likely through a dedicated persistence-aware page/subclass rather than changing Rotation pages
- `FEATURES.md`
- possibly `models/raid_plan.py` documentation/serialization helpers only if required; avoid structural model changes unless coordinated

### Rotation workstream guidance

Rotation may **consume** `RaidPlan` / `RaidPlanMember` and the existing effective-build/runtime bridges, but should not add its own Raid Plan persistence or duplicate plan ownership.

Please avoid concurrent writes to:

- `services/raid_plan_repository.py`
- its repository tests
- Raid Plan save/load UI files while this note is active

If Rotation needs a model field or contract change in `models/raid_plan.py`, coordinate first rather than independently changing persisted shape. Current fields, including `triggered_responsibilities`, are intended to round-trip through persistence unchanged.

### Ownership boundary

```text
Personnel / Characters / Saved Builds = global reusable identity
RaidPlan = trial-specific selections, assignments, adjustments, triggered responsibilities
Rotation = consumer of an exact resolved Raid Plan seat/effective build
RaidPlanRepository = persistence of RaidPlan snapshots only
```

Do not make ESO Logs, Rotation runtime state, or Team Optimization state a persistence dependency of `RaidPlanRepository`.

## Rotation workstream — ACTIVE

Recent Rotation commits observed immediately before this note include:

- `a75ddec7` Fix runtime application RaidPlanMember test fixture
- `cd435e44` Test runtime application installer contract
- `818ee869` Install runtime application support on Rotation page
- `dcb0953b` Test canonical runtime application UI boundary

Those changes should remain intact. The Raid Plan persistence workstream will re-fetch branch head before each write and avoid Rotation-owned files.
