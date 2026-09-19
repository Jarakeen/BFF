# Phase 14 Legacy Cleanup Ledger

This ledger records code that has been removed from normal Phase 14 ownership but may
remain temporarily for compatibility, migration, or historical tooling.

## Runtime ownership rules

- Raid Plan is the durable trial-specific source of truth.
- Comp Maker uses canonical `CompPlanState` and persists directly to Raid Plan.
- Team Optimization route `console:6` is the lightweight Phase 14 Recommendation Workbench.
- Compatibility code may read historical formats but must not become a parallel writer.
- Existing database files and user-owned data are never reset or replaced as part of cleanup.

## Comp Maker

### Retired from normal runtime ownership

- [x] `comp_builder_authoritative_prescription_support` is not bootstrapped.
- [x] generated-roster draft persistence is not the supported Phase 14 Save/Send path.
- [x] `comp_builder_build_candidate_support` no longer installs its generated-roster
      `_send_to_roster` wrapper.
- [x] `comp_builder_build_constraint_support` no longer installs its legacy send-time
      `_send_to_roster` validator wrapper.
- [x] `comp_builder_send_feedback_support` no longer wraps `_send_to_roster`.
- [x] Phase 14 shell is the final runtime owner of Comp Save/Send to Raid Plan.

### Compatibility still present

- [ ] `_comp_applied_candidates` remains a presentation/cache bridge in several older
      Comp helpers. Continue replacing reads with canonical `CompPlanState` recovery.
- [ ] generated-roster draft construction helpers remain for historical/migration tooling.
      Delete only after no supported imports/tests require them.
- [ ] move or rename compatibility-only modules into an explicit legacy namespace once
      import-site proof makes that safe.

## Team Optimization

### Retired from application startup

- [x] `team_optimization_role_cleanup` is no longer bootstrapped.
- [x] `team_optimization_canonical_analysis_support` is no longer bootstrapped.
- [x] `team_optimization_gap_guidance_support` is no longer transitively installed by
      Team Progress.
- [x] `raid_plan_optimizer_adviser_support` is no longer installed by the Raid Engine
      dashboard; the Phase 14 Workbench owns the exact Raid Plan handoff directly.
- [x] Optimization-specific provider-workload constructor/update hooks are not installed.
- [x] Main Window no longer constructs the legacy editable Optimizer send-to-Raid-Plan
      control.
- [x] Phase 14 Workbench initialization calls `FoundryPage.__init__` directly and never
      calls the original `OptimizationPage.__init__` chain.
- [x] saved-build loading, capability resolution, and Adviser construction are deferred
      until `set_raid_plan_adviser_scope` receives an exact saved Raid Plan.
- [x] route identity remains `console:6`.
- [x] Workbench remains read-only and does not silently overwrite Builds or Raid Plans.

### Compatibility still present

- [ ] `ui/optimization_page.py` retains the old editable implementation for historical
     /manual tooling, but normal startup replaces its constructor before MainWindow.
- [ ] `ui/team_optimization_role_cleanup.py` retains generated-roster draft load/send
      helpers as compatibility-only code.
- [ ] `ui/team_optimization_canonical_analysis_support.py` retains the old hidden-card
      presentation around reusable canonical analysis services.
- [ ] `ui/raid_plan_optimizer_adviser_support.py` retains the old adapter for historical
      callers. New runtime code uses the Phase 14 shell directly.
- [ ] old MainWindow helper methods that project an editable Optimization table can be
      deleted after search/tests prove no external/manual workflow invokes them.

## Profiling / proof

- [x] `tools/profile_team_optimization_startup.py` records lightweight page-construction
      time independently from first plan-scope analysis time.
- [x] `tools/profile_team_optimization_legacy_baseline.py` profiles the retired
      Optimization-specific constructor chain from a detached source tree without invoking
      unrelated Comp/Roster application bootstrap code.
- [x] focused structural tests guard that legacy Optimization constructors and provider
      hooks do not return to application startup.
- [ ] record local Windows before/after timing output in this file after profiling.
- [ ] run focused Phase 14 Comp + Optimization regression gates.
- [ ] after green proof, delete dead compatibility ownership paths rather than leaving
      duplicate implementations indefinitely.
