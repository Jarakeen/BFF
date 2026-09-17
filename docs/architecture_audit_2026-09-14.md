# FoundryDock Architecture Audit — 2026-09-14

## Purpose

This audit reviews BFF / FoundryDock against `SYSTEM_ARCHITECTURE_RULES.md` after the Phase 13.5 Raid Plan roadmap was completed. It is an architecture/ownership audit, not a feature-completeness review and not a request to rewrite stable code merely for aesthetics.

Primary questions:

- Is there one authority for each durable identity and mechanic?
- Do runtime paths match the authority declared by `services/service_catalog.py`?
- Are compatibility layers actually bridges, or have they become competing truth?
- Are feature installers and UI patches hiding architectural dependencies?
- Are older planning/engine paths still live after newer canonical boundaries were introduced?
- Do unknowns continue to fail closed rather than being converted into favorable assumptions?

Achievements and Collectibles are outside the cleanup scope of this audit. They may appear in broad static searches, but no remediation work should touch those surfaces as part of this audit.

## Executive result

The system is directionally much healthier than its age and patch history suggest. The canonical service catalog, `EffectiveBuildSnapshot`, RaidPlan consumer boundaries, effect identity model, and fail-closed rules are doing useful architectural work.

The largest risk is not duplicated combat math inside the new Phase 13.5 work. It is **hidden runtime authority created by compatibility and installation side effects**.

Priority order:

1. **Critical — restore the declared canonical Build persistence path.**
2. **High — make UI composition/install order explicit and stop adding transitive monkey-patch installers.**
3. **High — converge player/character/build/team identity ownership and retire name-based joins over time.**
4. **High — migrate `GeneratedRosterPlan` from competing durable plan identity to an explicit legacy/draft bridge around RaidPlan/Team ownership.**
5. **Medium — quarantine legacy `engine/main.py` / `engine/operations.py` mechanics prototypes.**
6. **Medium — flatten the service-catalog descriptor aggregation graph.**
7. **Medium — finish RaidPlan identity/documentation migration (`selected_build_id`, persistence documentation).**
8. **Low/Medium — remove remaining runtime-local default data paths where they can bypass packaged-path configuration.**

Do not perform these as one giant refactor. Each item should get a migration contract and focused regression gate.

## Remediation checkpoint — 2026-09-15

Current focused gate:

- architecture audit: **0 errors, 342 warnings**;
- the complete `installer-fanout` category is closed and regression-guarded;
- application composition now has explicit workspace, Team Optimization, Performance Dashboard, and Extreme Optimization bootstrap boundaries;
- feature-specific schedule, Hybrid-anchor, Build Editor performance, and Extreme page installers no longer bootstrap unrelated features;
- Build persistence authority, GeneratedRosterDraft migration, RaidPlan stable identity, runtime data paths, catalog aggregation, and legacy Console quarantine are substantially resolved;
- remaining high-value cleanup is concentrated in UI class monkey-patch families and selected compatibility retirement;
- raw service-catalog warning count remains intentionally noisy and is not a completion percentage.

Protected scope remains unchanged:

- do not modify Achievements or Collectibles during this cleanup;
- keep ESO Logs integrated because Top Gear, Capabilities, Performance, and ranked-team evidence actively consume it;
- defer Broadcast / Field Notes modular extraction to its own explicit migration.

## Final closeout checkpoint — 2026-09-17

**AUDIT COMPLETE.** The audit now has zero architectural closeout blockers and the
full repository gate is green: **3026 passed in 46.93s**.

| Finding | Final disposition |
|---|---|
| A-01 Build persistence authority | Fixed; canonical catalog/bridge authority is no longer replaced at package import. |
| A-02 hidden UI composition | Stabilized; installer fan-out is closed, application bootstraps own composition order, and every retained class-patch adapter has a proven non-test runtime owner. |
| A-03 player/character/team identity overlap | Stabilized with canonical IDs and fail-closed bridges; display-name compatibility does not become execution identity. |
| A-04 GeneratedRosterPlan overlap | Fixed; live callers use the draft API and legacy names/tables are compatibility/read-migration only. |
| A-05 RaidPlan identity/docs | Fixed; persistence documentation and stable selected-build identity match the live repository. |
| A-06 legacy Console prototypes | Fixed by quarantine; normal runtime imports from quarantine are architecture errors. |
| A-07 service-catalog aggregation | Fixed through the explicit catalog aggregator. |
| A-08 package import side effects | Fixed for the audited persistence/runtime authority paths. |
| A-09 runtime-local data defaults | Fixed for the audited paths; packaged-path configuration remains authoritative. |
| A-10 healer Performance composition | Fixed; healer analysis and presentation are restored to the explicit pre-window bootstrap. |

The static report deliberately retains two warning inventories rather than hiding
them:

- **272 `service-catalog:unregistered-service-boundary` candidates.** This heuristic
  includes leaf helpers whose class names end in `Service`; it is a review inventory,
  not proof that 272 canonical authorities are missing. Catalog integrity and unknown
  dependency errors remain blocking.
- **77 `ui-class-monkey-patch` adapters.** These are countable staged migration debt.
  All 77 have a production import owner; a test-only, dead, or dropped adapter is now
  an architecture error. Collectibles remain in the protected/out-of-scope subset.

`python tools/audit_system_architecture.py --closeout` treats any error or any warning
outside those two explicit inventories as a closeout blocker. This preserves visible
debt while preventing a raw warning count from masquerading as an unresolved
correctness finding.

---

## Healthy architecture worth preserving

### Canonical architecture rules are explicit

`SYSTEM_ARCHITECTURE_RULES.md` clearly defines the intended direction:

```text
canonical ESO data
  -> shared mechanics / runtime contracts
  -> role- and feature-specific evaluation
  -> explanation / UI
```

It also correctly separates gameplay-practice policy from mechanics, requires fail-closed unknowns, and treats the service catalog as discovery metadata rather than a dynamic locator.

### `EffectiveBuildSnapshot` is a good downstream boundary

`models/effective_build_snapshot.py` freezes an exact `PlayerBuild`, fingerprints it, deep-copies it on materialization, carries provenance, and distinguishes saved/candidate/RaidPlan sources. This is the right shape for preventing Rotation, Coverage, or Optimization from reconstructing contextual build truth independently.

### RaidPlan consumer ownership is clean

The Phase 13.5 RaidPlan work generally follows the intended ownership model:

```text
Global reusable identity
  Personnel / Characters / Saved Builds / Team

Trial-specific planning
  RaidPlan

Consumers
  Coverage / Rotation / Optimizer Adviser
```

Coverage and Rotation resolve exact selected builds and fail closed on ambiguity. Triggered responsibilities remain planning intent rather than fake wall-clock actions. Adviser is read-only.

### Coverage semantics are appropriately conservative

The current Coverage path distinguishes `available`, `conditional`, `not_found`, and `unverified`; unique support-set equipment can prove capability without claiming proc uptime; self-only effects are not promoted as group coverage.

### Canonical effect identity is structured

`EffectVariant.name` is explicitly the stable lower-snake-case mechanic identity. Magnitude/source/display text are not used as identity substitutes.

### Startup protects canonical ESO data

`app.py` validates the real canonical database before encounter schema work and refuses to silently create/use an empty replacement database.

---

# Findings

## A-01 — CRITICAL — Build persistence authority is silently replaced at package import

### Declared architecture

`services/build_catalog_descriptors.py` declares:

- `build.catalog.persistence` (`BuildCatalogService`) as canonical player/character/build persistence;
- `build.compatibility.persistence_facade` (`BuildService`) as a compatibility/UI facade;
- `builds.json` as compatibility data, not source of truth.

`services/build_service.py` is written consistently with that contract. Its `load()` and `save()` delegate through `CanonicalBuildBridge`, and `CanonicalBuildBridge` reads the canonical catalog first while maintaining `builds.json` as a compatibility mirror.

### Actual runtime behavior

`services/__init__.py` executes `_install_build_persistence()` on import and mutates the class globally:

```python
BuildService.load = load
BuildService.save = save
```

The replacement functions live in `services/build_persistence.py` and read/write `service.builds_path` directly. They do not call `CanonicalBuildBridge` and do not synchronize the canonical build catalog.

Because Python executes package `__init__.py` before importing `services.build_service`, ordinary application imports silently receive this patched behavior.

### Why it matters

Runtime truth can differ from the service catalog and from the code visible on `BuildService` itself. `characters.json` / canonical build state may become stale while the UI appears to save successfully to `builds.json`.

This is precisely the kind of competing authority the architecture rules prohibit.

### Remediation

Do this first, in a dedicated migration slice:

1. Move atomic-write/corruption-hardening semantics into the canonical persistence path (`CanonicalBuildBridge` / `BuildCatalogService` / explicit BuildService implementation).
2. Remove the `BuildService.load/save` monkey patch from `services/__init__.py`.
3. Make `services/__init__.py` side-effect free.
4. Add contract tests proving:
   - BuildService save updates canonical catalog and compatibility mirror;
   - canonical catalog remains load authority;
   - corruption never silently becomes a favorable empty roster;
   - compatibility mirror failure cannot silently supersede canonical state.

Do not simply delete `build_persistence.py` until its atomic-write protections have been absorbed.

---

## A-02 — HIGH — UI runtime is composed through deep monkey-patch/install chains

### Evidence

`app.py` directly installs many support modules before `MainWindow` construction, but two installers also act as hidden bootstrap hubs:

- `ui/team_optimization_hybrid_anchor_support.py` transitively installs Comp Maker, Team Optimization, Coverage, provider, bookmark, layout, and Rotation-related support modules.
- `ui/operations_console_schedule_support.py` transitively installs roster imports, identity/merge layers, Coverage gap presentation, Rotation runtime/navigation, assignments, build variants, Comp Maker intake, and other unrelated functionality.

The latter also mutates persisted Personnel data at startup through duplicate-player merge before installing UI behavior.

Repository search confirms many live assignments such as:

```python
CompBuilderPage.__init__ = ...
BuildEditor.__init__ = ...
MechanicsPage.__init__ = ...
EncounterBoard.__init__ = ...
OptimizationPage.<method> = ...
```

### Why it matters

- behavior depends on install order that is not visible from the target class;
- one feature installer implicitly owns startup for unrelated domains;
- wrappers can capture different previous implementations depending on order;
- tests can pass in isolation but application behavior can differ after the full patch chain;
- recent Coverage bugs were affected by wrapper/patch composition, demonstrating this is an operational risk, not merely style debt.

### Remediation

Do not big-bang rewrite the UI.

1. Freeze the rule: **no new unrelated transitive `install()` calls and no new class monkey patches unless explicitly marked compatibility debt.**
2. Introduce one explicit UI composition/bootstrap manifest whose only job is ordered installation/composition.
3. Move transitive install calls out of feature-specific modules into that manifest.
4. As each heavily patched page is touched, prefer real subclasses/composed collaborators over replacing class methods globally.
5. Prioritize Builds, Comp Maker/Optimization, Coverage, and Rotation because they carry the deepest functional patch stacks.

Existing patches may remain during migration; they should become visible compatibility adapters rather than invisible dependency wiring.

---

## A-03 — HIGH — Player/character/team identity has more than one durable authority

### Canonical build catalog

`BuildCatalogService` schema v4 owns stable:

- `player_id` and player/gamertag identity;
- `character_id` and player-to-character ownership;
- reusable build records / build IDs;
- build-level team assignments.

Its documentation explicitly says `PlayerBuild` / `BuildRoster` are compatibility snapshots rather than identity authority.

### Roster / Personnel database

`RosterService` independently owns SQLite tables for:

- `roster_member(id, player_name, character_name, eso_class, ...)`;
- global `team` identity;
- team membership;
- member assignments.

A `roster_member` row blends player identity with character fields using a separate integer identity.

### RaidPlan bridge

`RaidPlanMember` currently carries both `roster_member_id` and `character_id`, but selected build identity is still `selected_build_name`. `RaidPlanSavedBuildResolutionService` correctly fails closed, but resolves via display fields (`gamertag`, `character_name`, `BuildName`) rather than a stable build ID.

### Why it matters

The system can represent the same person/character through two durable identity stores and then join them by presentation names. Rename/duplicate/alias workflows therefore require repair logic and create avoidable ambiguity.

### Remediation target

Do not delete either store yet. Establish the migration contract first.

Recommended ownership:

```text
Canonical person/player + character + build IDs -> BuildCatalog (or one successor identity service)
Global Team identity + membership/schedule       -> Roster/Team domain
Trial-specific selections/assignments            -> RaidPlan
```

Roster/Personnel should reference stable canonical player/character IDs rather than independently re-owning those identities. Review `BuildCatalogService.team_assignments` separately: keep it only if it represents build availability/association rather than duplicating team membership or RaidPlan assignment ownership.

RaidPlan schema should eventually persist a stable `selected_build_id`, retaining build name only as compatibility/display data during migration.

---

## A-04 — HIGH — `GeneratedRosterPlan` is still a competing durable planning model

`GeneratedRosterPlanService` persists `generated_roster_plan` / `generated_roster_plan_slot` in SQLite. The object contains player, character, role, build name, candidate source, gear sets, skills, and Mundus and describes itself as a persistent build/assignment layer under a durable team identity.

It is still used by live Comp Maker / Optimization / Roster adoption workflows.

This predates the current RaidPlan ownership model and now overlaps with it:

```text
Team         = durable global identity
RaidPlan     = trial-specific selected team/build/assignment state
Comp Maker   = assembler / adviser
Optimizer    = adviser / explicit improvement
```

### Remediation

Treat `GeneratedRosterPlan` as a live legacy/draft bridge, not something to delete immediately.

Desired direction:

```text
Comp Maker output
  -> typed candidate/draft plan evidence
  -> explicit adoption into Team and/or RaidPlan
```

Migration needs to preserve recruitment placeholders and source/candidate evidence. The old tables should become deprecated only after every live consumer has an equivalent typed route into Team/RaidPlan.

The service catalog should eventually mark the old persistence responsibility deprecated/superseded rather than leaving two canonical durable plan concepts indefinitely.

---

## A-05 — MEDIUM — RaidPlan model documentation and build identity lag current implementation

`models/raid_plan.py` still states that the module is “persistence-neutral” and that existing roster/team/assignment services remain authoritative until a later migration adopts RaidPlan persistence. That migration has happened: `RaidPlanRepository` and the persisted Raid Plan UI are live.

The model also persists `selected_build_name` but no stable selected build ID.

### Remediation

- Correct the stale model documentation now.
- Design repository schema v2 around `selected_build_id` only after canonical build identity migration is proven.
- Preserve name fields as compatibility/display data during migration.
- Keep current fail-closed name resolver until stable IDs are populated reliably.

---

## A-06 — MEDIUM — Legacy Console engine prototypes duplicate models and mechanics in runtime packages

`engine/operations.py` contains several strong legacy/prototype signals:

- imports `CombatEffect`, `DynamicTrigger`, `SourceGameObject`, then redefines them locally;
- defines `TheConsoleEngine` more than once in the same file;
- defines `TheConsoleOpsEngine` in multiple places;
- includes demonstration/test blocks alongside runtime code;
- contains direct hardcoded mechanic calculations and capability strings that are outside the newer shared mechanics architecture.

`engine/main.py` is a FastAPI/prototype entry point with duplicate imports, several `if __name__ == "__main__"` blocks, and comments for an old `sorce` directory layout.

### Risk

These paths appear mostly isolated from the current desktop application, so they are not the first cleanup target. But leaving them under active `engine/` makes it easy for future work to mistake them for canonical mechanic authorities.

### Remediation

After confirming production import reachability:

- classify them explicitly as legacy/experimental developer tooling;
- move them to a legacy/prototype location or remove them if unused;
- do not preserve duplicated formulas as an alternative mechanic engine.

---

## A-07 — MEDIUM — Service catalog family aggregation obscures domain ownership

The catalog data model and integrity checks are useful. The family aggregation graph is less clean.

`services/service_catalog.py` defines catalog types and a base tuple, then imports `COMP_MAKER_SERVICE_DESCRIPTORS` at the bottom and appends it.

`services/comp_maker_catalog_descriptors.py`, despite its name, imports and re-exports descriptor families for RaidPlan, Extreme, Rotation, Team Prescription, Team Provider, and Team Workflow.

`team_workflow_catalog_descriptors.py` further bundles Build and Foundation descriptor families.

### Why it matters

A file named for one domain is effectively a whole-system aggregation root. This weakens the registry’s value as an ownership map and creates a circular-style import bootstrap between the catalog definition and descriptor families.

### Remediation

- split catalog types/query behavior from descriptor aggregation;
- keep each descriptor-family file limited to that family’s own descriptors;
- add one explicit aggregator module that concatenates families;
- preserve the current public `SERVICE_CATALOG` query API.

This can be done without changing runtime mechanic services.

---

## A-08 — MEDIUM — Import-time side effects exist outside the UI patch layer

`services/__init__.py` is the critical example because it mutates BuildService globally. Importing a package should not silently reassign service methods or perform data migration.

The static architecture audit should treat package-level mutation/installation as suspicious by default.

### Remediation

- make service packages side-effect free;
- explicit application bootstrap may perform migrations/installations;
- importing a service for a test or tool must not change another service’s behavior.

---

## A-09 — LOW/MEDIUM — Runtime library defaults sometimes bypass the centralized path service

Most UI/runtime entry points correctly use `engine.config.get_data_dir()` or `services.paths`. Some runtime library modules still define defaults via repository-relative paths, e.g. `minmax/skill_effect_repository.py`, `minmax/build_backed_roster_lab.py`, and `minmax/source_provenance.py`.

This is less urgent because important production call sites often pass explicit database paths. The risk is packaged/frozen execution when a caller accidentally relies on a repo-relative default.

### Remediation

Prefer explicit paths or `engine.config` for runtime defaults. Exempt developer tools/importers/tests where repository-relative paths are intentional.

---

# Recommended cleanup sequence

## Slice 1 — Build persistence authority

Goal: runtime and service catalog agree on the canonical Build persistence path.

No UI redesign. No identity migration yet.

Acceptance criteria:

- `services/__init__.py` has no BuildService mutation;
- atomic persistence still exists;
- canonical catalog is authoritative on load;
- save updates canonical catalog and compatibility mirror;
- corruption/failure stays explicit and fail closed;
- full Build persistence focused tests green.

## Slice 2 — Explicit UI bootstrap boundary

Goal: expose install order without changing every UI feature.

- central bootstrap manifest;
- feature installers stop transitively installing unrelated features;
- no new monkey patches;
- maintain current page behavior through compatibility adapters.

## Slice 3 — Identity convergence design + migration

Goal: one stable person/character/build identity chain.

- map Roster/Personnel rows to canonical player/character IDs;
- establish build ID on RaidPlan;
- distinguish Team membership from build association from RaidPlan assignment;
- provide migration/audit before deleting old identifiers.

## Slice 4 — GeneratedRosterPlan migration

Goal: Comp Maker produces/adopts typed draft/candidate plans rather than owning a competing durable team-plan truth.

## Slice 5 — Legacy engine quarantine

Goal: eliminate accidental reuse of obsolete hardcoded mechanic engines.

## Slice 6 — Service catalog aggregation cleanup

Goal: registry family names become truthful ownership boundaries.

## Slice 7 — Remaining path/default and compatibility cleanup

Only after higher-value authority conflicts are resolved.

---

# What this audit does *not* recommend

- Do not rewrite Rotation, Extreme, Coverage, or RaidPlan because their files are numerous.
- Do not delete ContextVariants before their migration to RaidPlan/boss adjustments is proven.
- Do not delete GeneratedRosterPlan while live Comp Maker/Roster consumers remain.
- Do not merge gameplay policy into mechanics.
- Do not turn ESO Logs observations into canonical mechanic truth.
- Do not perform a broad database reset.
- Do not touch Achievements or Collectibles as part of this cleanup.

The primary cleanup theme is **authority and composition**, not file-count reduction.
