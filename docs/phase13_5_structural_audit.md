# Phase 13.5 Structural Audit

This ledger records the Phase 13 / 13.5 closeout structural audit required by `MASTER_ROADMAP.md` before Phase 14. Every material finding receives one explicit disposition: fixed, intentionally retained, or deferred with an owner/boundary. The purpose is coherence of authority, not line-count reduction.

## Status

Audit in progress.

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

## Audit queue

The remaining Phase 13.5 audit will review, in order:

1. effect/proc/runtime-condition authority and hard-coded dictionaries;
2. Character -> Build -> Team identity reconstruction or fallback paths;
3. stale rotation tests, aliases, wrappers, temporary shims, and feature flags;
4. unused/dead Phase 13 services and catalog entries;
5. documentation/configuration drift;
6. focused regression after each material cleanup;
7. full regression checkpoint before Phase 13.5 closeout.
