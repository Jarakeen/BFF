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

## Audit queue

The remaining Phase 13.5 audit will review, in order:

1. duplicate/competing duration and periodic-runtime authority;
2. action-cost/resource authority and legacy helpers;
3. taunt/target/recipient semantics across tank services;
4. effect/proc/runtime-condition authority and hard-coded dictionaries;
5. Character -> Build -> Team identity reconstruction or fallback paths;
6. stale rotation tests, aliases, wrappers, temporary shims, and feature flags;
7. unused/dead Phase 13 services and catalog entries;
8. documentation/configuration drift;
9. focused regression after each material cleanup;
10. full regression checkpoint before Phase 13.5 closeout.
