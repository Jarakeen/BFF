# Phase 9 Encounter Model Closeout

## Result: PASS

Phase 9 provides a read-only, source-backed encounter domain model that answers **what an encounter explicitly demands from the evidence currently available** without converting prose, strategy, or manual planning into hidden canonical truth.

## Delivered

- immutable encounter definitions with canonical encounter identity, boss actor, mechanics, phases, source provenance, and reconciled evidence;
- strict repository lookup by canonical encounter ID with malformed, duplicate, and missing-source failures kept explicit;
- exact health parsing with annotations preserved and unknown values left unresolved;
- exact single-percentage phase-threshold parsing without promoting compound threshold prose into phases;
- structured requirements projected only from explicit mechanic fields for movement, positioning, cleanse, and interrupt demands;
- explicit target-count constraints without selecting targets or inventing targeting rules;
- positioning constraints that record only the encounter demand, not manual Encounter Board coordinates or group strategy;
- reconciled temporal evidence retaining the original seconds-field meaning, approximation status, source count, and reconciliation status;
- exact transition-evidence access with conflicting values preserved unresolved;
- exact `add_group` and `damage_window` evidence channels so later enrichment can model adds and immunity/burn windows without prose inference;
- real source-backed `add_group` and `damage_window` evidence for Archcustodian, using tracked UESP source material;
- requirement, phase/transition, health, temporal, and full encounter-model coverage audits;
- runnable corpus audit: `python tools/audit_phase9_encounter_model.py`.

## Final validation

Focused Phase 9 regression checkpoint reported on **2026-09-02**:

- **23 passed in 3.94s**

Corpus audit:

- encounters: **490**
- with mechanics: **35**
- with phases: **2**
- with requirements: **21**
- with positioning constraints: **12**
- with temporal evidence: **4**
- with transition evidence: **6**
- with target constraints: **3**
- with reconciled evidence: **8**
- with explicit add-group evidence: **1**
- with explicit damage-window evidence: **1**

These counts measure structured coverage, not live-game absence. Low or zero coverage in any future audit is an enrichment gap, not permission to infer that the mechanic does not exist.

## Boundary discipline

Phase 9 describes encounter truth; it does not assign providers, choose players, invent target selections, plan rotations, simulate combat, or promote raid strategy into source truth.

Missing structured evidence remains missing. In particular:

- summon prose does not create add actors or add groups;
- invulnerability, shield, or burn prose does not create damage windows;
- manual Encounter Board positions do not become canonical geometry;
- a target count does not identify the selected targets;
- single-source timing remains source-qualified evidence rather than silently promoted canon;
- conflicting evidence never receives an automatic winner.

## Exit criteria

**PASS.** BFF now has a deterministic encounter contract capable of representing bosses, mechanics, phases, requirements, positioning demands, timers, transitions, target-count constraints, source evidence, add groups, and damage windows while preserving unknown and conflicting evidence explicitly.

Phase 10 can now consume Encounter + Requirements + Roster + Builds without needing to reinterpret source prose or invent encounter truth.

**Exit criteria met on 2026-09-02.**
