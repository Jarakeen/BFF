# Phase 11 · Provider Assignment Closeout

**Status:** 🟢 Complete

## Goal

Phase 11 answers **who should provide a required capability** after Phase 10 has already established whether the roster can provide it.

The boundary remains strict:

- Phase 10 owns capability/evidence classification.
- Phase 11 owns provider candidacy, suitability, assignment, and responsibility conflicts.
- Phase 11 does not invent encounter requirements.
- Phase 11 does not mutate builds or optimize gear/skills.
- Generic movement, positioning, cleanse, and interrupt mechanics remain execution/compliance requirements unless an explicit provider requirement exists.
- UNKNOWN remains first-class and is never converted to missing or unsupported.

## Completed implementation

### Provider candidate contract

Phase 10 provider evidence is projected into explicit Phase 11 candidate states:

- `VIABLE`
- `UNRESOLVED`
- `CONFLICTING`

Each candidate remains tied to an exact requirement ID, encounter ID, capability type, stable member identity, build identity, and carried-forward evidence sources.

### Provider assignment

The assignment layer supports:

- `ASSIGNED`
- `UNRESOLVED_SELECTION`
- `UNRESOLVED_CAPABILITY`
- `UNRESOLVED_SUITABILITY`
- `CONFLICT`
- `INSUFFICIENT`

Assignment is conservative:

- roster order is never used as a tie breaker
- exactly-required viable providers may be assigned deterministically
- multiple equally viable providers remain unresolved until explicit suitability evidence differentiates them
- unresolved capability evidence remains unresolved
- conflict evidence remains conflict
- explicit unsuitable candidates may be removed from assignment consideration

### Explicit suitability evidence

Provider suitability is modeled only from supplied evidence dimensions:

- role
- build
- active bar
- eligibility
- uptime
- range
- target type
- condition
- positioning
- conflict
- player restriction

Suitability facts are assessed as `SATISFIED`, `UNSATISFIED`, or `UNKNOWN`, with aggregate states of suitable, unsuitable, unresolved, or unassessed. Phase 11 suitability cannot promote a roster member that Phase 10 did not already establish as a viable capability provider.

### Responsibility conflicts

The responsibility layer records explicit double-duty conflict evidence between exact requirement pairs for the same provider. Merely assigning the same player to two responsibilities does not automatically create a conflict.

This keeps simultaneous-duty conflicts source-backed instead of inferred from role stereotypes or generic mechanics.

## Requirement-source boundary

A Phase 11 readiness audit established that the canonical boss corpus currently contains:

- encounters: **490**
- structured requirements: **56**
- provider requirements: **0**
- compliance requirements: **56**
- unknown requirement semantics: **0**

This is not a Phase 11 failure. Boss mechanics and raid-support planning are separate domains.

The existing Coverage page already represented a configured raid coverage profile. Phase 11 extracted that profile into reusable domain data and added an encounter-requirement overlay so configured support requirements can be evaluated alongside canonical boss mechanics without pretending the boss itself requires a named support skill.

The default profile currently contains **15 required coverage entries**. Exact provider-capability mapping remains deliberately conservative:

- mapped: **1**
  - War Horn → canonical capability identity `force`
- unmapped: **14**

The unmapped entries remain visible as a data-enrichment boundary rather than being converted into guessed effect identities.

## Real saved-roster validation

### Roster

- **Magrat → DF Healer**
  - stable character ID: `ecf73a63-70a4-5b0a-81de-bf89bcd35e69`
  - resolved effects: **11**
  - capability-resolution gaps: **0**
- **Susan → Necro Tank**
  - resolved effects: **3**
  - capability-resolution gaps: **0**

Real saved builds: **2**  
Unique roster members: **2**

### Validation context

Encounter: **Oaxiltso**  
Difficulty: **veteran**

- canonical mechanic rows: **7**
- mapped configured coverage rows: **1**
- unmapped required coverage rows: **14**
- provider evaluation rows: **1**

### Deterministic provider result

Requirement:

`oaxiltso:coverage:war_horn`

Capability:

`force`

Phase 10 coverage classification:

`covered`

Phase 11 candidate evidence:

- Magrat → `VIABLE`
- evidence source: `Aggressive Horn`

Phase 11 assignment:

- status: `ASSIGNED`
- primary provider: **Magrat**
- backup providers: none
- reason: every proven viable provider is required, so the assignment is uniquely determined without applying a strategy preference

**Real provider validation result: PASS.**

BFF moved from “the roster has this capability” to “Magrat should provide this configured capability here” using the same saved-build and effect evidence already validated by Phase 10.

## Regression evidence

User-reported validation on 2026-09-03:

- focused Phase 11/provider/coverage checkpoint: **39 passed in 0.69s**
- full regression suite: **2031 passed in 73.87s**

Earlier Phase 11 candidate/suitability/assignment/responsibility checkpoint:

- focused tests: **30 passed in 0.95s**

No regression was introduced into the Phase 10 encounter/compliance path.

## Explicit deferred boundaries

The following are intentionally not Phase 11 closeout blockers:

- mapping the remaining 14 default coverage entries to exact canonical effect identities
- broad encounter-specific support strategy profiles
- automatic build mutation
- gear/skill optimization
- rotation planning
- combat simulation
- strategy preference selection
- inferred uptime or timing
- automatic responsibility reassignment after a conflict

Those belong to later data-enrichment, optimization, rotation, simulation, or strategy phases.

## Exit criterion

Roadmap exit criterion:

> BFF chooses sensible providers instead of merely listing coverage.

Final result:

- PASS: Phase 10 evidence is reused rather than reinterpreted
- PASS: provider candidates preserve viable / unresolved / conflict states
- PASS: deterministic assignment does not use roster-order tie breaking
- PASS: explicit suitability and responsibility-conflict evidence are represented
- PASS: boss mechanics remain separate from raid-support coverage requirements
- PASS: real saved roster has zero capability-resolution gaps
- PASS: a real configured provider requirement receives a deterministic primary provider
- PASS: Magrat is selected as the provider for the mapped War Horn / Force requirement in the Oaxiltso evaluation context
- PASS: full regression suite remains green

**PHASE 11 EXIT READY: true**

**Exit criteria met on 2026-09-03.**
