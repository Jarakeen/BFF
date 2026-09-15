# BFF Code Retirement and Quarantine Policy

BFF keeps old code deliberately when it may still matter for compatibility, migration, forensic comparison, or historical reference. A file is not considered safe to delete merely because a quick search shows no obvious caller.

The retirement path is:

`live runtime -> deprecated -> legacy or migration -> delete only after proof`

`old_pages` is archival UI/reference material and is never a runtime dependency.

## Directory meanings

### `deprecated/`

Code that still works and may still have callers, but must not gain new production consumers. Existing callers should be migrated to the canonical replacement. A deprecated module must identify its replacement or retirement condition in its module documentation or nearby migration note.

### `legacy/`

Compatibility or historical implementations preserved after normal production callers have been migrated away. Normal runtime code must not import from `legacy/`. Code placed here remains available for forensic comparison, explicit compatibility tooling, or controlled migration work until deletion is proven safe.

### `migration/`

Explicit one-purpose transition code for old schemas, persisted data, identity repair, or compatibility conversion. Normal application runtime must not depend on `migration/` as a mechanics, UI, persistence, or domain authority. Migration/bootstrap tooling may invoke it deliberately.

### `old_pages/`

Historical UI/page implementations and archived utilities. These files are reference material only. Normal runtime imports from `old_pages/` are architecture violations. Existing historical tests may exercise old code for comparison, but production code must not use it as an authority.

## Proof required before moving code

Before moving a live file into a quarantine directory, establish all of the following where applicable:

1. Repo-wide search identifies its imports, direct calls, dynamic installers, registrations, string references, and tests.
2. Canonical replacement ownership is documented and already used by production consumers.
3. Focused tests around the affected feature are green.
4. Architecture/service-catalog audits do not identify the old implementation as a current authority.
5. A full regression suite is run for broad or cross-domain moves when practical.
6. Persisted-data or migration dependencies are explicitly accounted for rather than assumed away.

A file may remain in `deprecated/` for a long time. That is preferable to deleting a helper later discovered to be required by an old install, repair tool, or compatibility path.

## Import boundary

Normal runtime roots are `engine/`, `minmax/`, `models/`, `services/`, and `ui/`.

Those runtime roots may not import from:

- `legacy/`
- `deprecated/`
- `old_pages/`
- `migration/`

The first three are quarantine/archive boundaries. `migration/` is restricted because migration code must be invoked explicitly by migration/bootstrap tooling rather than become a hidden runtime dependency.

`tools/` and tests may access quarantine material when the tool/test is explicitly about migration, compatibility, audit, or forensic comparison.

## Deletion rule

Deletion is the final step, not the first cleanup step. Remove quarantined code only when its replacement is canonical, no supported migration still needs it, repo-wide searches show no required consumers, and the relevant focused/full tests prove removal safe.
