# Migration

Explicit one-purpose transition code for old schemas, persisted data, identity repair, and compatibility conversion.

Normal application runtime must not depend on this directory as a mechanics, UI, persistence, or domain authority. Migration/bootstrap tools may invoke it deliberately.

Current quarantined migrations:

- `phase12_5_legacy_plan_repair.py` — repairs provable pre-Phase-12.5 generated-plan identity/assignment inconsistencies while preserving ambiguous legacy evidence.
- `phase12_5_team_workflow_audit.py` — audits persisted Phase 12.5 team-workflow results without acting as runtime team/planning authority.

See `docs/CODE_RETIREMENT_AND_QUARANTINE.md`.
