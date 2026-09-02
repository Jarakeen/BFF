# Phase 9 Encounter Model Closeout

## Result: PENDING CORPUS AUDIT

Phase 9 now provides a read-only, source-backed encounter domain model that answers **what an encounter explicitly demands from the evidence currently available** without converting prose, strategy, or manual planning into hidden canonical truth.

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
- requirement, phase/transition, health, temporal, and full encounter-model coverage audits;
- runnable corpus audit: `python tools/audit_phase9_encounter_model.py`;
- focused Phase 9 checkpoint reported on 2026-09-02: **21 passed**.

## Boundary discipline

Phase 9 describes encounter truth; it does not assign providers, choose players, invent target selections, plan rotations, simulate combat, or promote raid strategy into source truth.

Missing structured evidence remains missing. In particular:

- summon prose does not create add actors or add groups;
- invulnerability, shield, or burn prose does not create damage windows;
- manual Encounter Board positions do not become canonical geometry;
- a target count does not identify the selected targets;
- single-source timing remains source-qualified evidence rather than silently promoted canon;
- conflicting evidence never receives an automatic winner.

## Final closeout gate

Before marking Phase 9 complete in `MASTER_ROADMAP.md`, run:

```powershell
python tools\audit_phase9_encounter_model.py
```

Record the corpus coverage output here. Zero counts are enrichment gaps, not negative claims about the live encounter. The final closeout decision should be based on whether the domain model cleanly represents supported truth and leaves unsupported truth explicitly unresolved, not on pretending every encounter in the corpus is fully enriched.
