# Build persistence destructive-write and gate audit

Date: 2026-09-25
Branch: phase14

## Required invariant

Canonical user data in `user_data/foundrydock.db` is authoritative. UI rosters and page state are projections, not replacement authority.

A read, lookup, navigation event, normalization pass, or filtered/empty UI projection must never delete or replace canonical Saved Builds.

Only an explicit user-owned mutation may alter a Saved Build. Deletion must be an explicit deletion operation.

## Gates

| Gate | Required behavior | Audit status |
|---|---|---|
| Storage | Stable BuildId persists until explicit delete | Hardened |
| Identity | Build -> Character -> Player; ambiguous/cross-player repair fails closed | Hardened / regression coverage present |
| Load | Existing canonical Saved Build remains visible even if legacy optional fields are incomplete | Hardened |
| UI | Builds/Roles may filter views but cannot replace canonical catalog | Hardened |
| Assignment | Raid Plan references Saved BuildId; planned state is not a Saved Build | Hardened |
| Override | Raid-specific overrides belong to Raid Plan, not Saved Build | Architecture enforced in Comp persistence |
| Save | Page projection cannot replace whole canonical Build collection | Hardened |
| Legacy | Legacy comp records cannot become reusable Saved Builds | Hardened |
| Template/copy | Explicit copy/template promotion creates a new Saved Build identity | Preserved |
| Corruption | Mutation paths fail closed on unreadable canonical catalog | Hardened on audited mutation paths |

## Destructive paths found and fixed

1. `CanonicalBuildBridge.save()` could route a UI `BuildRoster` through replacement-style synchronization. Live application saves now merge stable identities instead.
2. `CanonicalBuildBridge.sync_from_roster()` could replace the application catalog. It is now forbidden for the live user database.
3. Character-progression identity lookup could call `sync_from_roster(page.roster)` merely while resolving a character. The write side effect was removed.
4. Canonical Saved Builds were filtered through a legacy completeness heuristic. Canonical BuildId + CharacterId records now remain visible.
5. Mutation services used tolerant `load()`, which converts read/JSON/SQLite failures to an empty catalog. Audited mutation paths now use `load_strict()` so a bad read cannot become an empty destructive write.
6. `import_legacy_roster()` now loads canonical state strictly before constructing a write candidate.

## Audited mutation surfaces

- Builds page save
- Build copy/template application
- roster import and context-variant persistence
- player identity merge
- team merge/deletion
- character progression writes
- Comp Maker Build persistence
- team prescription compatibility save
- canonical bridge migration/synchronization
- user-data legacy migration
- direct `build_catalog` SQL writes

Packaging/custom-seed tools intentionally construct filtered databases and are not normal runtime mutation paths.

## Recovery acceptance test

Do not call the recovery complete until all of these pass:

1. Restore the 12 known-good reusable Saved Builds from the emergency snapshot.
2. Strict catalog read reports exactly those recovered BuildIds.
3. `BuildService.load()` exposes the same 12 reusable Builds.
4. Opening Builds does not change the canonical catalog.
5. Roles offers the correct same-player Saved Build for every chair.
6. Copy Build creates a new BuildId owned by the selected destination Character and leaves the source unchanged.
7. Raid Plan assignment references Saved BuildId without creating a pseudo/comp Build.
8. Save, navigate across planning pages, close, and reopen.
9. Strict catalog contents and Raid Plan assignments remain semantically unchanged except for explicit user edits.
10. Create a fresh safety snapshot after the successful round trip.

## Rule for future code

If a function has only a projection, it may merge explicit records but may not infer deletion from absence. If deletion is intended, use an explicit deletion API with a named target identity and user-visible action.


## Hardened gates added during audit

- Application Build roster saves merge by stable identity; an empty or filtered UI projection cannot imply deletion.
- Destructive `sync_from_roster` is forbidden for the live application user database.
- Full-catalog application saves refuse to omit an existing Saved BuildId.
- Explicit Build deletion is isolated behind `BuildCatalogService.delete_build(build_id)`.
- Roster re-import replacement deletes only exact prior imported BuildIds; a matching record without a canonical BuildId fails closed.
- Team deletion and team merge update `build_catalog` through the same SQLite connection/savepoint as team rows.
- Canonical mutation-adjacent reads use strict loading so malformed state cannot degrade into an empty catalog.
- Read-only regression coverage compares raw `payload_json` before and after repeated `BuildService.load()` calls.
- Malformed-catalog regression coverage requires load failure while preserving the malformed payload byte-for-byte for diagnosis/recovery.
- Copy Build regression coverage requires a new nonblank BuildId at the exact destination Character and an unchanged source Build record.

## Recovery gate

Do not perform the final 12-Build recovery until the focused persistence suite containing these gates passes. After recovery, verify the exact recovered BuildIds through a strict catalog read, then through `BuildService.load()`, then open the Builds and Roles pages without saving and confirm the raw catalog payload is unchanged. Only after the save/navigation/close/reopen round trip succeeds should a fresh safety snapshot become the new recovery baseline.
