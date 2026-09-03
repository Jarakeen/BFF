# Phase 10 · Encounter Evaluation Closeout

**Status:** 🟢 Complete

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
- native core persistence for configured scribed-skill recipes so CLI and UI read the same build evidence
- exact canonical-source boundary handling for gear identities that exist in the canonical entity layer even when legacy `gear_set` effect rows are unavailable

## Verified real encounter path

### Real roster

- **Magrat → DF Healer**
  - 11 resolved EffectVariants
  - 0 capability-resolution gaps
- **Susan → Necro Tank**
  - 3 resolved EffectVariants
  - 0 capability-resolution gaps
- real saved builds: **2**
- unique real characters: **2**
- blank/template builds ignored: **0**

### Oaxiltso veteran

- Savage Blitz movement → `dodge`
- Savage Blitz positioning → `bait_farthest`
- Blistering Smash positioning → `avoid_hazard`
- Noxious Sludge movement → `move_to_interaction / cleanse_pool`
- Noxious Sludge positioning → `hazard_drop_management / noxious_pool`
- Noxious Sludge cleanse → `encounter_interaction / cleanse_pool`
- Summon Havocrel Annihilators positioning → `separate_add_from_boss`
- fully evaluable: **true**
- capability-ready: **true**
- execution rows: **7**
- provider rows: **0**

Provider rows are correctly zero for this validation encounter because the represented requirements are execution/compliance demands rather than provider-assignment demands. Provider selection remains Phase 11.

### Oaxiltso hard mode

- the five non-pool-dependent execution requirements remain covered
- Noxious Sludge movement becomes unknown because the documented cleanse-pool interaction is disabled
- Noxious Sludge cleanse becomes unknown for the same source-backed reason
- no alternate cleanse interaction is invented
- fully evaluable: false
- capability-ready: false

## Canonical-source boundary validation

The final real-roster closeout exposed three useful data-integration boundaries on Susan's saved tank build:

- configured `Leashing Soul`
- configured `Goading Throw`
- `Perfected Puncturing Remedy`

The two scribed skills already had complete saved recipe evidence. Core `PlayerBuild` persistence was extended so non-UI services consume those recipes directly instead of treating them as result-name-only crafted skills.

`Perfected Puncturing Remedy` is absent from the legacy `gear_set` table in the local database, but both `Puncturing Remedy` and `Perfected Puncturing Remedy` exist as exact canonical `gear_set` entities with ESO-Hub provenance. Phase 10 now distinguishes this known canonical-source boundary from a truly unknown gear identity rather than inventing missing effect rows.

No unsupported magnitude, uptime, proc behavior, or provider assignment was inferred to satisfy closeout.

## Corpus execution audit

Final closeout audit:

- encounters with requirements: **21**
- fully evaluable encounters: **6**
- fully ready encounters: **6**
- covered requirements: **25**
- unknown requirements: **31**
- conflicting requirements: **0**

Low corpus coverage is an encounter-enrichment boundary, not a negative claim about mechanics that are not yet represented by structured evidence.

## Final regression evidence

User-reported validation on 2026-09-02:

- focused final source-boundary / scribing checkpoint: **16 passed in 1.65s**
- full regression suite: **2031 passed in 94.10s**

## Exit criterion

Roadmap exit criterion:

> BFF reliably evaluates a real roster against a real encounter.

Final result:

- PASS: real saved-build data exists
- PASS: at least two unique real roster members selected
- PASS: selected roster has no capability-resolution gaps
- PASS: the real roster is capability-ready for Oaxiltso veteran

**PHASE 10 EXIT READY: true**

**Exit criteria met on 2026-09-02.**

Phase 11 begins provider assignment: determining who should provide a required capability, not merely whether the roster collectively has it.
