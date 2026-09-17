# FoundryDock Release Status

This file is the release-facing inventory for packaged FoundryDock builds. It is deliberately stricter than `FEATURES.md`: a feature may exist in source and still be excluded from a release.

**Current development version:** `0.1.0`  
**Next release version:** `0.1.1` when the release candidate is approved.  
**Status date:** 2026-09-17

## Release rules

- The source repository may retain research, tests, historical evidence, migration helpers, and old implementation notes.
- The executable ships only explicitly approved runtime code/data/assets.
- Disabled, legacy, deprecated, superseded, experimental, or unfinished user-facing features do not ship as visible release features.
- Updates may replace application files but must never overwrite the live `eso.db`, user settings, saved builds, roster state, progress, or session data.
- `app_version.py` is the single source of truth for the application version.
- Final release approval requires a clean build on a machine/environment that is not relying on the developer checkout.

---

## Release candidate: working / intended to ship

These are current release candidates, subject to the final smoke gate.

- Desktop application shell and Urban Wilderness visual skin
- Canonical sidebar/navigation for enabled workspaces
- BFF application branding and active semantic icon library
- Character and canonical saved-build management
- Build Editor core configuration surfaces
- Roster workspace and inline Players / Characters / Teams / Availability / Recruitment / Archive detail flow
- Raid Plans
- Assignments
- Readiness
- Live Raid workspace
- Coverage workflows that are currently registered and tested
- Comp Maker workflows that are currently registered and tested
- Combat / Reference Data workspace
- Gear Lookup / reference tools that remain visible in current navigation
- Achievements and currently wired progress surfaces
- Application update check / staged in-place portable update support
- Database migration/provisioning needed by supported runtime paths

**Final release gate still required:** every visible route must open successfully from the packaged build and must not depend on developer-only files.

---

## In progress: source retained, not considered release-ready yet

These remain active development work. They may be present in the source tree and may be packaged only if their runtime dependencies are needed by another approved feature; they are not to be advertised as finished release features until their gate is explicitly changed here.

- Rotation Builder / rotation runtime completion and UI hardening
- Extreme Build Engine / ceiling-proof engine
- Optimizer Adviser transition
- Collectibles presentation polish and final badge/layout review
- Remaining Raid Engine visual/interaction cleanup
- Final executable data-payload classification
- Clean-machine packaged-build validation

---

## Disabled: do not expose in the release

- Screenshot/OCR Build Import user-facing control
- Community News
- Any feature explicitly disabled by an optional-module/runtime gate
- Broadcast module in the default FoundryDock build; it remains an explicitly optional payload only

Disabled implementation may remain in source when it is intentionally retained for future work, but its UI entry points and startup work must remain off.

---

## Legacy / deprecated / superseded: exclude from packaged assets and release UI

- Retired visual themes and old theme-selection experience
- `assets/themes/bff/city_night`
- `assets/themes/bff/grimoire`
- retired theme decorative packs
- old Roster raven/street filler artwork
- unused field-office placeholder artwork
- deprecated or superseded UI implementations that are no longer registered
- tests, audit scripts, research HTML, evidence dumps, handoff files, screenshots, caches, virtual environments, and Git metadata
- old duplicated encounter/data corpora when a canonical replacement is the runtime authority

Historical/reference source may remain in the repository when useful for development. Repository presence is not permission to package it.

---

## Approved bundled asset families

The authoritative machine-readable list lives in `packaging/release_manifest.py`.

Currently approved:

- `assets/AbilityIcons` — runtime-selected ESO ability artwork
- `assets/icons` — canonical semantic UI icon library
- `assets/logos/BFF_logo.png` — active application branding
- `assets/themes/bff/foundry.qss` — active base stylesheet
- `assets/themes/bff/urban_wilderness` — active visual skin assets
- `assets/themes/bff/field_journal/roster` — two pencil/sketch Roster/Readiness assets still intentionally used by Urban Wilderness
- `bff.ico` — Windows application icon
- `data/eso.db` as a **read-only seed only** inside the frozen app

The live writable database remains external.

---

## Data payload classification: required before final 0.1.1 build

The current portable build historically copied many top-level `data/` reference files. Do not remove them by guesswork: several Rotation, Extreme, coverage, encounter, potion, gear, and canonical services consume JSON semantics at runtime.

Before final packaging, every external `data/` file must be assigned exactly one class:

1. **runtime-required** — ships with the app/update;
2. **first-install state** — created cleanly, never copied from the developer workstation;
3. **user-owned** — preserved across updates, never replaced;
4. **development/evidence/legacy** — excluded.

The release audit intentionally reports this as an outstanding gate until the classification is complete.

---

## Final release gate

A release is ready only when all of the following are true:

- full intended release test suite passes;
- release audit passes;
- app boots from a clean checkout;
- packaged app boots without the developer virtual environment;
- every visible sidebar route opens;
- disabled routes are absent;
- no missing/corrupt image warnings;
- no required runtime asset/data file is missing;
- no forbidden legacy asset tree is bundled;
- existing live database migrates without reset;
- update archive contains no `eso.db`, settings, builds, roster/progress/session state;
- upgrade from the previous release preserves user-owned data;
- `APP_VERSION` is bumped to the new release number only after the candidate is approved.
