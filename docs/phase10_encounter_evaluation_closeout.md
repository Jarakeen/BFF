# Phase 10 · Encounter Evaluation Closeout

**Status:** Implementation-ready; final real-roster exit validation pending

## Goal

Phase 10 combines the canonical encounter model, structured requirements, saved-build capability resolution, roster identity, execution handling, and provider coverage into one deterministic evaluation surface.

The Phase 10 boundary remains strict:

- Phase 10 answers whether the selected roster has sufficient known capability to handle the encounter requirements.
- Phase 11 assigns specific providers.
- Phase 10 does not silently convert generic movement, positioning, cleanse, or interrupt requirements into build-provider requirements.
- Missing or conflicting source evidence remains explicit.

## Completed implementation

- explicit requirement semantics: provider capability vs execution/compliance vs unknown
- covered / redundant / insufficient / missing / conflict / unknown provider classifications
- explicit provider cardinality keyed by canonical requirement ID
- target count kept separate from provider count
- stable canonical roster identity with duplicate-character protection
- exact EffectVariant identity mapping for saved-build capabilities
- capability-scoped unresolved evidence so unrelated stat/state gaps do not poison provider coverage
- build-independent cleanse method semantics
- build-independent interrupt method semantics with sourced core-bash fallback
- source-backed movement and positioning handling methods
- difficulty-aware execution availability
- hard-mode invalidation of handling methods when structured evidence says an interaction is disabled
- real saved-build evaluator CLI
- corpus execution-readiness audit
- Phase 10 closeout audit
- multi-member orchestration regression coverage

## Verified real encounter path

Authoritative saved build:

- Magrat → DF Healer
- 11 resolved EffectVariants
- 0 capability-resolution gaps
- 1 retained stat/state gap: Frozen Armor passive rank is not recorded

Oaxiltso veteran:

- Savage Blitz movement → `dodge`
- Savage Blitz positioning → `bait_farthest`
- Blistering Smash positioning → `avoid_hazard`
- Noxious Sludge movement → `move_to_interaction / cleanse_pool`
- Noxious Sludge positioning → `hazard_drop_management / noxious_pool`
- Noxious Sludge cleanse → `encounter_interaction / cleanse_pool`
- Summon Havocrel Annihilators positioning → `separate_add_from_boss`
- fully evaluable: true
- capability-ready: true

Oaxiltso hard mode:

- the five non-pool-dependent execution requirements remain covered
- Noxious Sludge movement becomes unknown because the documented cleanse-pool interaction is disabled
- Noxious Sludge cleanse becomes unknown for the same source-backed reason
- no alternate cleanse interaction is invented
- fully evaluable: false
- capability-ready: false

## Latest verified regression checkpoint

User-reported focused Phase 10 checkpoint on 2026-09-02:

- **68 passed in 7.21s**

## Corpus execution audit

Latest user-reported closeout audit:

- encounters with requirements: **21**
- fully evaluable encounters: **6**
- fully ready encounters: **6**
- covered requirements: **25**
- unknown requirements: **31**
- conflicting requirements: **0**

Low corpus coverage is an encounter-enrichment boundary, not a negative claim about mechanics that are not yet represented by structured evidence.

## Real saved-roster inventory

Latest local closeout audit:

- real saved builds: **1**
- unique real characters: **1**
- blank/template builds ignored: **1**

The canonical character catalog likewise contains only Magrat as a real character at this checkpoint.

## Exit criterion status

Roadmap exit criterion:

> BFF reliably evaluates a real roster against a real encounter.

Current result:

- PASS: real saved-build data exists
- BLOCK: at least two unique real roster members selected
- PASS: selected roster has no capability-resolution gaps
- PASS: the selected real build is capability-ready for Oaxiltso veteran

**PHASE 10 EXIT READY: false**

The remaining blocker is validation data, not missing evaluator architecture. One additional genuine saved character/build is required to perform the final multi-member real-roster exit evaluation without using templates or synthetic players.

## Boundary moving into final validation

Do not weaken the exit criterion by treating `YOUR TANK BUILD`, blank placeholders, or multiple builds belonging to the same canonical character as additional roster members.

Once a second real character/build exists, rerun:

```powershell
python tools\audit_phase10_closeout.py --encounter oaxiltso --difficulty veteran
```

If multiple builds exist for either character, select one authoritative build per character explicitly:

```powershell
python tools\audit_phase10_closeout.py --encounter oaxiltso --difficulty veteran --build "DF Healer" --build "<SECOND REAL BUILD>"
```

Provider assignment remains Phase 11.
