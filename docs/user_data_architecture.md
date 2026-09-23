# FoundryDock User Data Architecture

FoundryDock separates replaceable ESO/reference data from user-owned state.

## Canonical reference database

`data/eso.db` is the replaceable reference database. It owns ESO catalog/reference facts such as achievements, collectibles, gear, skills, encounters, and other game data.

The release process may rebuild or replace this database from a sanitized seed. User-owned state must not depend on preserving this file.

## User database

`foundrydock.db` is the writable user-owned SQLite database.

Development/source runs use:

`user_data/foundrydock.db`

Frozen Windows builds use:

`%LOCALAPPDATA%\FoundryDock\foundrydock.db`

The environment variable `FOUNDRYDOCK_USER_DATA_DIR` can override the user-data directory for portable/test builds.

Current user-owned database responsibilities include:

- Personnel / roster members
- Teams and team membership
- Roster assignments and roster workflow state
- Generated roster drafts/plans stored in SQLite
- Collectible ownership and collectible profiles
- Achievement completion and achievement profiles
- Saved Raid Plans
- Canonical players, characters, builds, character progression, and build-to-team assignments

## Legacy migration

On startup, `migrate_legacy_user_data()` copies legacy user-owned rows out of `data/eso.db` plus legacy `achievement_progress.json`, `raid_plans.json`, `characters.json`, and `builds.json` into `foundrydock.db`.

Migration is additive and idempotent:

- the legacy source is never deleted or replaced;
- an existing populated user table wins;
- repeated startup migration does not overwrite later user edits.

Legacy files remain valid migration inputs while older installations are still supported.

## First-install EXE seeds

Normal public/fresh builds start with a blank user database.

A deliberately customized EXE may provide a prepared `foundrydock.db` as a first-run seed. Both friend and release packaging support an explicit user database seed. PyInstaller embeds it under `_seed_user_data`, and runtime copies it only if the recipient has no existing `foundrydock.db`.

That means a customized EXE can ship prepared teams/progress without making later application updates overwrite the recipient's user database.

## Ownership rule

The boundary is intentionally simple:

- ESO/reference fact -> `data/eso.db`
- Human-created or human-owned state -> `foundrydock.db`

Do not add new user-owned tables to `data/eso.db`.


## Privacy-limited custom raid EXE

`packaging/build_friend.ps1 -UseCurrentRaidSetup` creates a first-run user database seed containing only the current raid setup. When more than one Raid Plan exists, `-RaidPlanId` is required so an unrelated plan cannot leak into the custom EXE:

- Personnel
- Teams
- Team memberships
- Personnel assignments
- Saved Raid Plans

It intentionally excludes achievement progress, collectible progress, and other collection/checklist state. The build script first migrates any legacy Raid Plan JSON into `foundrydock.db`, then creates the limited seed. This profile is for deliberate one-off builds and does not change normal public-release behavior.


For the current-raid custom profile, the seeded `foundrydock.db` carries only the canonical player/character/build records referenced by the selected Raid Plan. Neither `characters.json` nor `builds.json` is created in the package.
