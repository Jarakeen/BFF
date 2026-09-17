# FoundryDock Release Status

This file is the release-facing inventory for packaged FoundryDock builds. It is deliberately stricter than `FEATURES.md`: a feature may exist in source and still be excluded from a release.

**Current release candidate:** `0.1.2`  
**Status date:** 2026-09-17

## Release rules

- The source repository may retain research, tests, historical evidence, migration helpers, and old implementation notes.
- The executable ships only explicitly approved runtime code/data/assets.
- Disabled, legacy, deprecated, superseded, experimental, or unfinished user-facing features do not ship as visible release features.
- Updates may replace application files but must never overwrite the live `eso.db`, user settings, saved builds, roster state, progress, or session data.
- `app_version.py` is the single source of truth for the application version.
- Final release approval requires a clean packaged-build smoke pass.

---

## Release candidate: working / intended to ship

These are current release candidates, subject to the final packaged smoke gate.

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
- Rotation Builder / rotation runtime and Phase 14 command-center UI
- Combat / Reference Data workspace
- Gear Lookup / reference tools that remain visible in current navigation
- Achievements and currently wired progress surfaces
- Collectibles / Stickerbook core workflows and category deep links; badge/layout polish remains a non-blocking visual follow-up
- Application update check / staged in-place portable update support
- Database migration/provisioning needed by supported runtime paths

**Final release gate still required:** the packaged executable must launch and every visible release route must open without depending on developer-only files.

---

## In progress: source retained, hidden from packaged release navigation

These remain active development work. Source builds keep them visible for development; frozen release builds hide their routes until they are explicitly promoted here.

- Extreme Build Engine / ceiling-proof engine
- Optimizer Adviser transition
- Remaining Raid Engine visual/interaction cleanup
- Clean packaged-build validation

---

## Disabled: do not expose in the release

- Screenshot/OCR Build Import user-facing control
- Community News
- Any feature explicitly disabled by an optional-module/runtime gate
- Broadcast module in the default FoundryDock build; it remains an explicitly optional payload only

Disabled implementation may remain in source when intentionally retained for future work, but its UI entry points and startup work must remain off.

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
- `assets/avatar` — bundled default character avatars for Roster character profiles
- `assets/timers/vas2` — optional local vAS+2 timer artwork bundled when present on the release workstation
- `assets/icons` — canonical semantic UI icon library
- `assets/logos/BFF_logo.png` — active application branding
- `assets/themes/bff/foundry.qss` — active base stylesheet
- `assets/themes/bff/urban_wilderness` — active visual skin assets
- `assets/themes/bff/field_journal/roster` — pencil/sketch Roster/Readiness assets still intentionally used by Urban Wilderness
- `bff.ico` — Windows application icon
- `data/eso.db` as a **read-only recovery seed only** inside the frozen app

The live writable database remains external.

---

## Data payload classification: complete

The top-level `data/` release boundary is fully classified.

Every external data file is assigned to one of these classes:

1. **runtime-required** — copied with the first install and safe update payload;
2. **first-install state** — created cleanly, never copied from the developer workstation;
3. **user-owned** — preserved across updates and never replaced;
4. **development/evidence/legacy** — excluded.

The release audit currently reports `unclassified_top_level_data=0`.

---

## Final release gate

A release is ready only when all of the following are true:

- full intended release test suite passes;
- release audit passes;
- packaged app launches without the developer virtual environment;
- every visible release sidebar route opens;
- in-progress and disabled routes are absent from packaged navigation;
- no missing/corrupt image warnings appear;
- no required runtime asset/data file is missing;
- no forbidden legacy asset tree is bundled;
- existing live database migrates without reset;
- update archive contains no `eso.db`, settings, builds, roster/progress/session state;
- upgrade from the previous release preserves user-owned data;
- release artifacts report version `0.1.2`.
