# Phase 13.5 Structural Audit

This ledger records the Phase 13 / 13.5 closeout structural audit required by `MASTER_ROADMAP.md` before Phase 14. Every material finding receives one explicit disposition: fixed, intentionally retained, or deferred with an owner/boundary. The purpose is coherence of authority, not line-count reduction.

## Status

**COMPLETE.** Every material finding has a disposition and the repository-wide
regression gate is green: **3026 passed in 46.93s** on 2026-09-17.

## Findings

### F001 — Rotation sustain reconstructed character-owned armor progression from equipped gear

**Category:** architecture drift / competing identity truth

**Files:**
- `services/rotation_sustain_service.py`
- `services/tests/test_rotation_sustain_canonical_progression.py`
- `services/tests/test_rotation_sustain_service.py`
- `services/tests/test_rotation_required_action_reserve_service.py`

**Finding:** when canonical Character progression was unresolved or contained no owned skill lines, `RotationSustainService` inferred owned Light/Medium/Heavy Armor skill lines from currently equipped armor. That made a Build-local equipment fact impersonate Character-owned progression and violated the canonical Character -> Build ownership boundary.

**Disposition:** FIXED.

**Resolution:** rotation sustain now returns only canonical progression from `MinmaxCharacterProgressionAdapter`. Missing owned skill-line evidence remains explicit unresolved state. It no longer derives character-owned skill-line ownership from equipped gear. Stale tests that required the fallback were rewritten to protect the canonical-only contract.

**Validation:** user-reported focused gate after cleanup: `15 passed in 3.65s`.

---

### F002 — Recovery-heavy pressure accepts a caller maximum while produced timelines carry canonical maximum state

**Category:** compatibility shim / potential duplicate authority

**Files reviewed:**
- `minmax/resource_timeline.py`
- `services/rotation_recovery_heavy_replay_service.py`
- `services/rotation_recovery_heavy_stabilization_service.py`
- recovery-heavy generation/candidate/UI callers

**Finding:** `RotationRecoveryHeavyReplayService.pressure_resolver()` accepts `maximum_amount`, and that value is threaded through the stabilization/generation path. At first glance this appears to compete with bar-aware `ResourceTimelineResult.starting_maximum` and maximum events.

**Authority review:** produced Phase 4 resource timelines always record `starting_maximum` and apply verified maximum transitions. `ResourceTimelineResult.maximum_at()` consults timeline maximum evidence first; the passed fallback is used only when a manually constructed historical/test timeline omits maximum metadata. Therefore the caller maximum does not override canonical production timeline state.

**Disposition:** INTENTIONALLY RETAINED as non-authoritative compatibility.

**Reason retained:** removing the argument would require broad churn across recovery-heavy adapters/tests without changing production semantics. The lower-level timeline compatibility supports historical manually constructed timelines, while production decisions continue to use timeline-owned maximum evidence first.

**Closeout boundary:** do not introduce new production callers that rely on fallback-only maximum state. New canonical timelines must carry maximum evidence directly.

---

### F003 — DD and healer periodic runtime maintain separate clocks/duration authorities

**Category:** duplicate/competing duration and periodic-runtime authority

**Files reviewed:**
- `services/rotation_duration_analysis_service.py`
- `services/rotation_candidate_periodic_damage_timing_evidence_service.py`
- `services/rotation_candidate_periodic_damage_runtime_projection_service.py`
- `services/rotation_healer_canonical_periodic_timing_service.py`
- `services/rotation_healer_periodic_runtime_evidence_service.py`
- `services/rotation_healer_periodic_runtime_service.py`
- shared `minmax.runtime_event` periodic scheduler

**Finding:** review was required because DD and healer periodic paths expose role-specific services and runtime evidence objects that each carry duration/cadence fields.

**Authority review:** no competing runtime clock was found. DD periodic timing delegates canonical duration resolution to the shared rotation-duration evidence path and delegates concrete recurring event expansion to the shared Phase 7 periodic scheduler. Healer runtime evidence is assembled from canonical healer cadence/duration plus a narrow reviewed observation overlay for first-tick offset, expiry-boundary behavior, repeated-application refresh semantics, and magnitude timing; its concrete recurring event expansion also delegates to the shared scheduler. `RotationDurationAnalysisService` remains the recast/effective-duration analyzer rather than a second periodic tick scheduler.

**Disposition:** REVIEWED / NO CONFLICT FOUND.

**Closeout boundary:** role-specific services may own role-specific evidence binding and legality, but concrete periodic clock arithmetic must continue to delegate to the shared runtime scheduler. Reviewed overlays may not replace canonical component identity/cadence/duration.

---

### F004 — Rotation sustain and provider workload calculate action costs independently

**Category:** duplicate/competing action-cost and resource authority

**Files reviewed:**
- `services/rotation_sustain_service.py`
- Phase 4 `evaluate_named_build_sustain` path
- `services/team_provider_canonical_workload_service.py`
- `minmax/ability_cost_repository.py`
- `minmax/build_action_cost_modifiers.py`
- `minmax/build_final_action_cost.py`

**Finding:** rotation sustain and provider workload expose separate consumer services and both resolve scheduled action costs, so the audit checked whether they maintain independent cost arithmetic.

**Authority review:** no competing cost formula was found. Both paths resolve canonical base costs through `AbilityCostRepository` and reuse build cost-modifier/final-action-cost mechanics rather than maintaining role-local numeric rules. Provider workload directly composes `BuildFinalActionCostResolver`; rotation sustain delegates through the Phase 4 sustain engine using the same base-cost and modifier authorities. Provider-specific handling of secondary paid Ultimate activations remains an explicit semantic branch, not an alternative ordinary skill-cost formula.

**Identity review:** `TeamProviderCanonicalWorkloadService` validates `PlayerBuild.Name` + `BuildName`; this matches the canonical `PlayerBuild` model, which does not own a separate `CharacterName` field. The broader defensive identity fallback used by rotation sustain is compatibility around injected/legacy-shaped objects, not a competing canonical field.

**Disposition:** REVIEWED / NO CONFLICT FOUND.

**Closeout boundary:** new rotation/provider consumers must reuse the canonical base-cost and final build-modifier services. Role-local hard-coded costs or duplicate cost modifier tables are not permitted.

---

### F005 — Tank assignment, taunt obligation, maintenance, and priority layers duplicate target semantics

**Category:** target/recipient authority and layered Tank responsibility

**Files reviewed:**
- `minmax/rotation_plan.py`
- `services/rotation_assignment_taunt_obligation_service.py`
- `services/rotation_tank_taunt_obligation_service.py`
- `services/rotation_assignment_taunt_maintenance_service.py`
- `services/rotation_tank_taunt_maintenance_service.py`
- `services/rotation_tank_encounter_priority_context_service.py`
- `services/rotation_tank_priority_candidate_assessment_service.py`

**Finding:** several Tank services carry `target_key`, and the new priority assessor additionally accepts reviewed actor-name identity as a soft match. The audit checked whether those layers compete over target truth or allow soft aliases to satisfy hard obligations.

**Authority review:** no hard-semantic conflict was found. Assignment services translate provider/lane ownership into explicit caller-owned planning targets. Taunt application and maintenance services require exact target-key matching when a hard target is supplied; canonical TAUNT skill semantics remain source-backed through utility-component evidence. The Tank priority assessor is a soft ranking layer only: it may recognize either the reviewed responsibility target key or reviewed actor name when assessing explicit scheduled targets, but that alias cannot satisfy a hard taunt application/maintenance requirement or rescue an ineligible candidate.

**Disposition:** REVIEWED / NO CONFLICT FOUND.

**Closeout boundary:** hard taunt legality and maintenance must continue to use exact caller-owned target identity. Actor-name aliases are permitted only in reviewed soft-priority comparison and may not flow backward into mechanic truth, taunt duration, immunity/overtaunt behavior, or hard target legality.

---

### F006 — Conditional runtime-output truth was embedded in a Python reviewed-rule tuple

**Category:** hard-coded runtime-condition authority

**Files:**
- `services/rotation_runtime_output_eligibility_service.py`
- `data/rotation_runtime_output_conditions.json`
- `services/tests/test_rotation_runtime_output_eligibility_service.py`

**Finding:** Detonating Siphon's reviewed geometry condition was stored in a module-level `_REVIEWED_RULES` tuple. Although narrow, provenance-bearing, and delegated to the shared runtime eligibility evaluator, the source file itself was acting as the persistence layer for reviewed runtime-condition evidence.

**Disposition:** FIXED.

**Resolution:** reviewed runtime-output conditions now live in versioned repository data (`data/rotation_runtime_output_conditions.json`). `RotationRuntimeOutputConditionRegistryService` validates schema, canonicalizes skill identity, rejects duplicate component rules, and constructs the existing shared runtime eligibility rules. `RotationRuntimeOutputEligibilityService` loads the registry by default while retaining explicit rule injection for focused tests. Runtime state/geometry remains caller-owned through exact-time `ConditionContext`; the registry does not calculate geometry or output.

**Closeout boundary:** new reviewed conditional-output rules must be added to the versioned registry with provenance rather than embedded in role-local Python dictionaries. Runtime truth still requires exact event-time context.

---

### F007 — Reviewed scribed rotation semantics were embedded as a Python constant

**Category:** hard-coded reviewed effect/runtime semantics

**Files:**
- `services/rotation_scribed_skill_damage_semantics_service.py`
- `data/rotation_scribed_skill_damage_semantics.json`
- `services/tests/test_rotation_scribed_skill_damage_semantics_service.py`
- `services/scribing_catalog.py`

**Finding:** Magical Banner's reviewed rotation-facing semantics (non-damaging activation, persistent toggle, and 6% Magic Damage Done while active) were stored as `_MAGICAL_BANNER` in Python. Canonical result identity already belonged to `services.scribing_catalog`, but reviewed runtime/effect semantics used source code as persistence.

**Disposition:** FIXED.

**Resolution:** reviewed scribed rotation semantics now live in versioned repository data. The loader validates schema, validates damage-modifier fields through `DamageDoneModifiers`, and requires each reviewed result name to resolve to the exact Grimoire + Focus identity owned by the canonical scribing catalog. Unknown/unreviewed results remain fail-closed.

**Closeout boundary:** `services.scribing_catalog` remains authoritative for result identity and legal naming. Reviewed rotation semantics may supplement that identity from versioned evidence data but may not infer unreviewed Signature/Affix behavior or become a second scribing-identity catalog.

---

### F008 — Raid Plan Rotation binding reconstructed canonical build identity from legacy/adjacent fields

**Category:** Character -> Build identity reconstruction / fail-open guard

**Files:**
- `ui/rotation_generate_canonical_context.py`
- `ui/tests/test_rotation_generate_raid_plan_context.py`
- canonical `models/build_model.py` `PlayerBuild`

**Finding:** `RotationGenerateCanonicalContext.with_raid_plan_member()` validates the exact Raid Plan member against the supplied `PlayerBuild`, but its local helpers accepted `CharacterName or Name` for character identity and `BuildName or Name` for build identity. Canonical `PlayerBuild` owns `Name` as character identity and `BuildName` as build identity; it has no canonical `CharacterName` field. The build-name fallback was especially unsafe because a blank `BuildName` could be replaced by the character name and potentially satisfy a selected-build guard using the wrong field.

**Disposition:** FIXED.

**Resolution:** the Raid Plan -> Rotation canonical context now reads only `PlayerBuild.Name` for character identity and only `PlayerBuild.BuildName` for build identity. Missing canonical values fail closed. Regression coverage explicitly supplies a fake legacy `CharacterName` while canonical `Name` is blank and separately leaves canonical `Name` intact while `BuildName` is blank; both bindings are rejected at the appropriate identity boundary.

**Closeout boundary:** exact Raid Plan/Rotation build binding must validate canonical model fields directly. Compatibility aliases or UI/display labels may be normalized at ingestion boundaries, but they may not substitute for missing canonical identity after a `PlayerBuild` has entered the Rotation/Raid Plan execution path.

---

### F009 — Comp saved-build candidates conflate character identity and account display fallback

**Category:** Character -> Build -> Team identity contract debt

**Files reviewed:**
- `services/comp_builder_build_candidates.py`
- `services/comp_builder_team_candidate_optimizer.py`
- `services/comp_builder_provider_evidence.py`
- `ui/team_provider_workload_support.py`
- `ui/comp_builder_build_candidate_support.py`

**Finding:** saved `CompBuildCandidate` rows use `source_name` as a blended display-owner field: canonical `PlayerBuild.Name` when present, otherwise `PlayerBuild.Gamertag`. Downstream Comp Maker grouping, provider-evidence, and selected-build recovery reuse `source_name` as a saved-player key. This means the field is not a stable canonical character identity even though several consumers treat it as if it were one.

**Disposition:** DEFERRED — broader Comp Maker identity-contract cleanup required.

**Reason deferred:** the ambiguity originates in the upstream candidate contract rather than one Rotation consumer. Tightening only `ui/team_provider_workload_support.py` would make that consumer disagree with candidate generation, optimizer grouping, and provider evidence. A correct repair needs a dedicated canonical saved-build identity on `CompBuildCandidate` (for example canonical build id and/or explicit character identity) while retaining `source_name` as display/source metadata.

**Closeout boundary:** no new consumer may treat `CompBuildCandidate.source_name` as canonical character or build identity. Existing consumers may retain current fail-closed/unique-match behavior until the candidate contract is migrated. Exact Raid Plan and Rotation execution paths must continue using canonical `PlayerBuild` fields / build ids and must not inherit this display fallback.

---

### F010 — Stabilized healer runtime output service existed but Generate did not bind it

**Category:** unwired canonical capability / stale pre-stabilization role evidence

**Files:**
- `services/rotation_candidate_healer_multi_demand_role_output_service.py`
- `services/rotation_healer_canonical_role_output_factory_service.py`
- `services/rotation_recovery_healer_role_output_service.py`
- `services/rotation_healer_demand_criteria_service.py`
- `ui/rotation_generate_healer_role_evidence_support.py`
- focused healer runtime/factory/criteria tests

**Finding:** `RotationRecoveryHealerRoleOutputService` already existed to evaluate healer output against the final recovery-stabilized plan using exact runtime build context, but the production healer Generate path supplied a plain canonical plan-evidence provider with no stabilized-snapshot binder. Recovery could therefore move casts/bar swaps while healer role-output evidence remained on the static/pre-stabilization path. Verified healer hard criteria were vulnerable to the same split authority.

**Disposition:** FIXED.

**Resolution:** the existing multi-demand healer output path now accepts an optional exact runtime build-context resolver and forwards it to every canonical healing demand. `RotationHealerCanonicalRoleOutputFactoryResult` exposes the same runtime seam. The recovery-healer adapter supports the canonical multi-demand provider and exposes its exact stabilized runtime resolver. Production healer Generate wraps canonical plan evidence with a stabilized-snapshot binder so role output and verified healer hard criteria evaluate the same final plan/runtime context. Static behavior remains unchanged when no runtime history is supplied.

**Fail-closed clarification:** relevant factory-level static-context blockers invalidate aggregate healer comparison and verified hard obligations without erasing already-modeled per-window evidence. A window may therefore remain inspectably modeled while `weakest_window_value` and authoritative criteria stay unresolved.

**Validation:** user-reported focused healer gate after final repair: `31 passed in 5.28s`.

**Closeout boundary:** healer role ranking and verified healer hard obligations must consume the same final stabilized runtime context whenever such evidence exists. Do not reintroduce a seed/static-only healer ranking path after recovery stabilization.

---

### F011 — Stabilized healer catalog metadata lags the production multi-demand runtime path

**Category:** documentation / service-catalog drift

**Files reviewed:**
- `services/rotation_catalog_descriptors.py`
- `services/rotation_recovery_healer_role_output_service.py`
- `ui/rotation_generate_healer_role_evidence_support.py`

**Finding:** the service descriptor for `rotation.healer.stabilized_runtime_role_output` still names `RotationCandidateHealerRoleOutputService` as the healer-output input. Production Generate now binds `RotationHealerCanonicalRoleOutputFactoryResult` / `RotationCandidateHealerMultiDemandRoleOutputService` and may also recompute verified healer hard criteria from the same stabilized runtime context. The descriptor therefore understates the current production contract.

**Disposition:** FIXED.

**Resolution:** the stabilized-runtime descriptor now advertises
`RotationHealerCanonicalRoleOutputFactoryResult`,
`RotationCandidateHealerMultiDemandRoleOutputService`, and the shared runtime
resolver consumed by verified healer hard criteria. Its dependencies now point to
the registered multi-demand and healer-criteria authorities.

**Closeout boundary:** discovery metadata must continue to describe the production
multi-demand path. The lower-level single-demand service remains diagnostic-only as
recorded in F012.

---

### F012 — Single-demand healer role-output service remains a lower-level diagnostic compatibility primitive

**Category:** apparent dead service / compatibility review

**Files reviewed:**
- `services/rotation_candidate_healer_role_output_service.py`
- `services/rotation_recovery_healer_role_output_service.py`
- `tools/audit_phase13_saved_build_stabilized_healer_output.py`
- focused healer role-output/runtime-context tests

**Finding:** production healer Generate now uses the canonical multi-demand role-output path, so `RotationCandidateHealerRoleOutputService` initially appears superseded. Reference review shows it remains intentionally used by the saved-build stabilized-healer audit and lower-level canonical demand/runtime forwarding tests. The recovery-healer adapter intentionally accepts both the single-demand diagnostic primitive and the production multi-demand wrapper through the same runtime-context seam.

**Disposition:** INTENTIONALLY RETAINED as lower-level diagnostic compatibility.

**Reason retained:** the single-demand service remains useful for focused mechanic/audit isolation without becoming a competing production ranking authority. Deleting it would force audit tooling to construct multi-demand orchestration solely to inspect one demand window, adding ceremony without improving correctness.

**Closeout boundary:** production Generate must continue using the multi-demand path. New application-facing healer ranking code should not adopt the single-demand service; its scope is focused diagnostics, audit tooling, and lower-level tests.

---

### F013 — Active formula tests imported removed quarantine modules

**Category:** stale tests / quarantine drift

**Files:** twelve formula regression modules under `minmax/tests`.

**Finding:** the formula consolidation moved live implementations into
`final_calculations`, `resolved_modifiers`, `derived_stats`, `core_stats`, and
`power_mitigations`, but twelve active tests still imported nonexistent
`old_pages.old_*` modules. Repository-wide test collection therefore stopped before
running any regression gate.

**Disposition:** FIXED.

**Resolution:** the tests now import the live canonical formula owners. The
architecture audit also reports an error when any active test imports a quarantine
module that no longer exists; historical comparisons may still import real archived
modules.

**Validation:** **127 passed in 1.41s** for the migrated formula set.

---

### F014 — Healer Performance Dashboard extensions fell out of explicit bootstrap

**Category:** unwired user-visible capability / UI composition drift

**Files:**
- `ui/application_performance_dashboard_bootstrap.py`
- `services/performance_healer_analysis_support.py`
- `ui/performance_dashboard_healer_support.py`
- architecture and UI bootstrap tests

**Finding:** both the healer analysis decorator and healer dashboard presentation
still existed, but neither was installed after Performance Dashboard composition was
moved into its explicit application bootstrap. The tests still described the correct
pre-`MainWindow` contract, but production startup did not satisfy it.

**Disposition:** FIXED.

**Resolution:** the explicit Performance Dashboard bootstrap now installs healer
analysis before presentation and before `MainWindow` construction. The architecture
audit additionally fails when a runtime UI class-patch adapter has no non-test
production import owner.

**Validation:** architecture, bootstrap, healer UI, and service-catalog focused gate:
**24 passed in 12.19s**.

---

## Audit queue

Completed/reviewed in this ledger:
- Character -> Build -> Team identity reconstruction/fallback paths;
- stale rotation aliases, wrappers, compatibility seams, and suspicious services;
- effect/proc/runtime-condition authorities and hard-coded reviewed semantics;
- documentation/service-catalog drift;
- stale quarantine-dependent regression tests;
- production reachability of runtime UI class-patch adapters;
- focused regression after material cleanup;
- full repository regression checkpoint.

No Phase 13.5 structural-audit item remains without a fixed, intentionally retained,
or explicitly deferred owner/boundary disposition.
