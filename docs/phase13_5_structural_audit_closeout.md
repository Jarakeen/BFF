# Phase 13.5 Rotation Structural Audit Closeout

## Scope

This note closes the repository-structure pass required by the Phase 13 / 13.5 Rotation Engine closeout gate. The detailed finding ledger remains `docs/phase13_5_structural_audit.md`; this note records the final disposition of the remaining audit queue rather than replacing that evidence.

## Result

**STRUCTURAL AUDIT COMPLETE — focused and full repository regression checkpoints verified green.**

The audit found no proven orphaned Rotation production service whose removal would improve correctness without removing a supported caller, diagnostic boundary, evidence-review path, or explicit compatibility contract.

### Dead / obsolete service review

The remaining suspicious services were traced through their callers before disposition:

- `RotationRecoveryHealerRoleOutputService` was not dead; it was an unwired canonical capability. It is now bound by production healer Generate after recovery stabilization, and the focused healer gate was user-verified at **31 passed in 5.28s**.
- `RotationCandidateHealerRoleOutputService` remains intentionally retained for focused single-demand diagnostics/audits and lower-level runtime-context tests. Production Generate uses the canonical multi-demand path.
- `RotationHealerPeriodicObservationFixtureService` is intentionally retained because it is consumed by the reviewed runtime-evidence loader and healer observation/review tooling. It is observational evidence infrastructure, not a second mechanic authority.
- the plain/legacy Generate path remains supported fallback behavior when the caller has not supplied the optional advanced canonical context; it is not silently authoritative once canonical context is present.
- the saved-build `Two-Handed` attack-family compatibility mapping remains isolated to LA/HA family-level evaluation. It does not write a fabricated weapon subtype back into canonical saved-build identity and cannot establish subtype-specific mechanics.

No Rotation feature flag or TODO stub was found that represents unfinished production architecture.

### Authority review

The detailed ledger records and dispositions F001–F012. Important closeout outcomes include:

- canonical Character → Build identity is enforced at the Raid Plan → Rotation execution boundary;
- Comp Maker's blended `source_name` identity remains a countable deferred contract debt and is forbidden from becoming Rotation execution identity;
- runtime-output conditions and reviewed scribed semantics use versioned evidence data rather than Python constants;
- DD/healer periodic clock arithmetic delegates to shared runtime scheduling rather than competing role-local clocks;
- ordinary action-cost math remains shared between sustain/provider consumers;
- Tank target aliases remain soft priority evidence and cannot satisfy hard taunt obligations;
- healer role output and verified healer hard criteria now consume the same final stabilized runtime context;
- unsupported or source-unreviewed mechanics remain explicit rather than being converted to zero or guessed behavior.

### Deferred, countable boundaries

These items do **not** represent missing Rotation Engine architecture:

1. **F009 — Comp candidate identity contract debt.** Owner: broader Comp Maker candidate contract. `CompBuildCandidate.source_name` must not be adopted as canonical Rotation identity.
2. **Lightning Staff light-attack semantics.** Owner: source review. Production remains fail-closed because the preserved shock-LA modifier contract contains HA/Empower/DoT-shaped terms not sufficiently verified for modern light attacks.
3. **Exact Stampede replay anchors for the real DD validation plan.** Owner: reviewed observation evidence. Architecture is complete; exact planned-action anchors cannot be manufactured from aggregate timing statistics.
4. **Unreviewed continuous execute interpolation such as Executioner.** Owner: source review. Reviewed discrete execute semantics remain supported; unreviewed interpolation stays unresolved.

### Canonical team/build prerequisite

The live Raid Plan workstream is roadmap-complete and stable: persistence → assignments → Coverage → Rotation → Optimizer Adviser. Selected Raid Plan chairs resolve exact saved builds and enter Rotation through the existing canonical context seam. Rotation does not own a competing persistence, assignment, or team identity model.

## Verified closeout validation

The Rotation-specific closeout gates have now been reported green by the user:

- focused healer stabilization gate: **31 passed in 5.28s**;
- Exploiter-focused DD repair gate: **14 passed in 3.37s**;
- real `Rylonia` / `Corpsebuster DD` whole-plan damage audit: **0 actionable blockers**; remaining unresolved damage actions were classified as runtime-input-required because Exploiter requires authoritative target `CombatState` at each damage instant rather than a guessed standing bonus;
- broad Rotation regression across `services/tests`, `ui/tests`, `minmax/tests`, and `tools/tests` with `-k "rotation"`: **2425 passed, 6774 deselected in 73.26s**.
- final architecture/bootstrap/service-catalog focused gate: **25 passed in 17.61s**;
- restored canonical formula regression set: **127 passed in 1.41s**;
- full repository gate: **3026 passed in 46.93s**.

The broad Rotation gate initially exposed stale fixtures and compatibility-test drift around hardened canonical contracts. Those fixtures were updated without weakening production boundaries. The final rerun was fully green.

## Closeout gate

The repository-wide regression checkpoint is green. Phase 13 / 13.5 Rotation and its
required structural audit are closed. Remaining Lightning Staff, exact
Stampede-anchor, execute-interpolation, or similar items stay explicitly owned by
future source/evidence review and do not reopen engine architecture.
