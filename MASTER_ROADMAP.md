# 🖤 Black Feather Foundry
## Updated Development Roadmap

## North Star

BFF becomes a trustworthy, database-backed ESO combat, effects, encounter, and optimization engine that can explain not only **what** is optimal, but **why**.

```text
REAL ESO DATA
      ↓
CANONICAL BUILD
      ↓
RULES / EFFECT ENGINE
      ↓
STATIC COMBAT MATH
      ↓
COMBAT STATE
      ↓
ENCOUNTER ENGINE
      ↓
ROSTER / COVERAGE
      ↓
PROVIDER ASSIGNMENT
      ↓
BUILD OPTIMIZATION
      ↓
ENCOUNTER OPTIMIZATION
      ↓
EXPLANATION
      ↓
LOG VALIDATION
```

---

# Roadmap Completion Standard

This section is authoritative for **every phase**, including phases previously marked complete.

A phase is not complete merely because its architecture exists, representative tests pass, or one happy-path example works. Phase completion means the phase's stated scope is demonstrably usable against the real data and downstream path it claims to support.

## Mandatory closeout gates

Every phase marked **🟢 Complete** must satisfy all applicable gates below.

1. **Architecture gate**
   - one authoritative implementation path exists;
   - no competing legacy implementation silently remains authoritative;
   - ownership and boundaries with adjacent phases are explicit.

2. **Data / corpus gate**
   - the required real-data corpus for the phase has a declared scope and denominator;
   - parse/import failures, missing rows, unresolved rows, conflicts, and intentionally unsupported cases are counted;
   - low coverage may be accepted only when the phase scope explicitly says coverage enrichment is deferred and downstream correctness does not depend on the missing data;
   - absence of evidence is never treated as evidence of absence.

3. **Persistence gate**
   - if the phase creates canonical or durable data, a dry run must validate the exact write set first;
   - writes must preserve provenance and review state;
   - rejected, conflicting, unresolved, or unsupported rows must not leak into canonical truth;
   - write paths must be idempotent or have another explicit duplicate-prevention guarantee;
   - a post-write audit must verify the persisted rows, not merely trust the writer's success message.

4. **Real integration gate**
   - at least one representative real saved build, roster, encounter, or other real production path must traverse the phase end-to-end;
   - synthetic fixtures are necessary but are not sufficient by themselves.

5. **Regression gate**
   - focused tests for the phase must be green;
   - a full regression checkpoint must be recorded when the phase changes shared engine behavior or when its closeout depends on broad compatibility;
   - tests are only claimed green from actual reported output.

6. **Unresolved-boundary gate**
   - remaining unknowns must be explicit, countable, and assigned to a later phase or supported limitation;
   - a deferral may not contradict the phase's own promised outcome;
   - `UNKNOWN`, unsupported, and conflicting states may not be silently converted to zero, false, unavailable, or safe.

7. **Downstream dependency gate**
   - when later work materially changes canonical inputs owned by an earlier phase, dependent completed phases receive a retrospective impact review;
   - dependent phases do not automatically reopen, but representative integration must be rerun when the changed upstream data could alter their conclusions.

## Corpus-bearing phase rule

Phases that claim to model a real corpus, including encounter data, effect data, or optimization candidates, must distinguish these four states:

```text
SOURCE EXISTS
    ↓
PARSED / PROJECTED
    ↓
REVIEWED / RESOLVED
    ↓
CANONICALLY PERSISTED + AUDITED
```

Completing the first or second step does **not** imply the third or fourth.

## Status meanings

- **🟢 Complete**: all applicable completion gates are satisfied.
- **🟢 Engine complete / 🟡 retrospective validation**: the implementation is complete, but later upstream hardening requires a recorded revalidation.
- **🟡 Active**: work required for the phase's exit criteria remains.
- **🔴 Planned**: not yet active.

If a later audit discovers that a required closeout gate was never satisfied, the roadmap must say so. Historical completion dates remain useful history, but they do not overrule current evidence.

---

# PHASE 0 · Data Foundation
**Status: 🟢 Complete**

Database-backed ESO information exists for skills, morphs, skill ranks, coefficients, gear, set effects, encounter imports, UESP encounter data, repositories, and data services.

**Hardened exit criteria:** BFF has reliable database-backed sources for required ESO information, provenance is retained, canonical and raw/source data remain distinguishable, and missing or unsupported source coverage is explicit.

---

# PHASE 1 · Canonical Build System
**Status: 🟢 Backend foundation / 🟡 UI & downstream adoption**

A Build is the reusable canonical representation of one character configuration.

```text
Character
 ├── Identity
 ├── Character-owned progression
 │    ├── Owned skill lines
 │    └── Passive ranks
 └── Build(s)
      ├── Race / Class
      ├── Gear / Traits / Enchants
      ├── Skills / Morphs / Ultimates
      ├── CP
      ├── Mundus / Food / Potions
      └── Configuration
```

Completed canonical persistence foundation includes stable character/build identity, many builds per character, character-scoped progression, stable build IDs, passive-rank persistence, and canonical progression surviving legacy sync.

Remaining adoption work:

- expose all character-owned progression in the Builds/character UI;
- make passive ranks and owned skill lines editable without direct JSON work;
- make saved Character → Build selection authoritative across downstream pages;
- migrate remaining page-specific identity/build reconstruction onto the canonical catalog.

**Exit criteria:** a real character can have reusable database-backed builds and character-owned progression that downstream systems consume directly, without page-specific reconstruction becoming a competing identity model.

---

# PHASE 2 · Effect Architecture
**Status: 🟡 Advanced foundation**

The existing `EffectVariant` / effect-resolution architecture remains authoritative for effect identity, category, magnitude, duration, chance, cooldown, trigger, target, conditions, and stacking.

```text
ESO Database
     ↓
Skill / Morph / Gear / Consumable
     ↓
EffectVariant
     ↓
Effect Repository
     ↓
Build Effect Resolver
     ↓
Normalized Effects
```

**Rule:** do not create a second competing hard-coded effect dictionary.

A selected potion represents available capability, not standing uptime. Temporal activation is projected explicitly later.

**Exit criteria:** a real build exposes the effects it actually provides, unsupported or conditional behavior remains explicit, and downstream consumers use this architecture rather than parallel effect truth.

---

# PHASE 3 · Static Combat Rules Engine
**Status: 🟢 Complete**

Phase 3 established one explainable static combat calculation with separate modifier stages rather than one giant multiplier bucket.

Authoritative damage path:

```text
Database coefficient
      ↓
Raw component value
      ↓
Attacker Damage Done
      ↓
Critical eligibility / expected crit
      ↓
Target Critical Resistance
      ↓
Resistance / penetration mitigation
      ↓
Target Damage Taken
      ↓
Final damage
```

Closeout evidence:

- real `eso.db` classified component traversed the full static pipeline;
- type-8 coefficient formula unified as `A * MaxStat + B * Power + C`;
- modifier stages remain separate and explainable;
- unresolved evidence remains explicit;
- full suite at historical closeout: **1305 passed**;
- exit criteria met on **2026-08-31**.

Supported limitation: unresolved/ambiguous component semantics remain explicit rather than guessed and are not silently routed as zero-value mechanics.

---

# PHASE 4 · Resource & Sustain Engine
**Status: 🟢 Complete**

Phase 4 models resource state, verified ability costs, ordinary recovery timing, temporary recovery modifiers, explicit restoration events, deterministic resource timelines, and sustain failure/margin interpretation.

Closeout evidence:

- real **Magrat → DF Healer** saved build traversed the complete resource path;
- deterministic same-timestamp ordering is cost → recovery tick → restoration event;
- failure, shortfall, minimum-resource, ending-margin, cost, and wasted-restore diagnostics are explicit;
- unresolved mechanics remain explicit;
- full regression suite at historical closeout: **1,444 passed**;
- exit criteria met on **2026-08-31**.

Deferred runtime trigger scheduling remains owned by later temporal phases rather than being guessed in sustain math.

---

# PHASE 5 · Real Build Resolution
**Status: 🟢 Complete**

Phase 5 proves the actual ESO database → canonical character/build → resolver → `EffectVariant` / capability path across authoritative saved builds while keeping temporal and conditional mechanics explicit.

Historical closeout evidence:

- authoritative saved build **Magrat → DF Healer** resolved through production paths;
- Spaulder of Ruin, Serpent's Disdain, Master Architect, Combat Prayer, Expansive Frost Cloak, Overflowing Altar, Aggressive Horn, and selected potion capability resolved through the effect architecture;
- authoritative roster closeout reported **0 genuine unresolved** capability gaps;
- full regression suite: **1,619 passed** on **2026-09-01**;
- detailed closeout: `docs/phase5_real_build_resolution_closeout.md`.

**Exit criteria met on 2026-09-01.**

---

# PHASE 6 · Damage / Effect Components
**Status: 🟢 Complete**

Phase 6 makes coefficient-local ability semantics explicit without turning runtime combat state into static facts. It bridges per-component identity into the existing effect architecture and records static relationships that Phase 7 can execute over time.

Historical closeout evidence on **2026-09-02**:

- residual audit rows: **403**;
- needs Phase 6 review: **0**;
- parser-coverage rows: **0**;
- source-evidence blocked: **4**;
- unsupported source alignment: **4**;
- unresolved source blocks: **0**;
- classification cleanup: **356**;
- ownership negatives: **8**;
- Phase 7 boundaries: **35**;
- targeted final regression checkpoint: **14 passed**;
- **RESULT: PASS**.

Four Engulfing Dragonfire coefficient-3 rows remain explicit unsupported source-alignment cases rather than invented semantics.

**Exit criteria met on 2026-09-02.**

---

# PHASE 7 · Conditional Effects & Proc Engine
**Status: 🟢 Complete**

Phase 7 executes the static component/effect relationships established in Phase 6 over deterministic runtime state while preserving `EffectVariant` as authoritative.

Historical closeout evidence:

- deterministic runtime event contract;
- canonical timing/state binding;
- explicit proc chance without hidden RNG;
- global/per-target cooldowns;
- active windows, stacking, refresh, status state, triggered restoration/healing, and target caps;
- closeout boundary rows: **24**;
- trigger-resolution gaps: **0**;
- timing unresolved: **0**;
- targeted checkpoint: **105 passed in 48.20s**;
- `python tools\check_phase7_closeout.py`: **RESULT: PASS**;
- detailed closeout: `docs/phase7_conditional_runtime_closeout.md`.

**Exit criteria met on 2026-09-02.**

---

# PHASE 8 · Combat State
**Status: 🟢 Complete**

Phase 8 answers: **what is true right now?** It projects canonical build state plus runtime history into an auditable `CombatState` snapshot without becoming the rotation or simulation engine.

```text
Canonical Build + Static Character State
                 ↓
       Runtime Event History
                 ↓
    Phase 7 Effect Runtime State
                 ↓
      CombatState Snapshot at t
                 ↓
Static Combat / Sustain / Encounter Consumers
```

**Exit criteria met on 2026-09-02.** Detailed closeout: `docs/phase8_combat_state_closeout.md`.

---

# PHASE 9 · Encounter Model
**Status: 🟢 Engine complete / 🟡 Retrospective corpus hardening**

Phase 9 owns the deterministic, source-backed encounter model for boss identity, structural encounter data, mechanics, phases, requirements, positioning demands, timers, transitions, target-count constraints, add groups, damage windows, canonical facts, evidence, and unresolved/conflicting state.

## Historical Phase 9 closeout

The original closeout on **2026-09-02** proved the encounter architecture and projection/evidence boundaries:

- focused Phase 9 regression checkpoint: **23 passed in 3.94s**;
- encounter corpus audited: **490 encounters**;
- mechanics represented at that time: **35 encounters**;
- phases represented: **2 encounters**;
- requirements represented: **21 encounters**;
- positioning constraints represented: **12 encounters**;
- temporal evidence represented: **4 encounters**;
- transition evidence represented: **6 encounters**;
- target constraints represented: **3 encounters**;
- reconciled evidence represented: **8 encounters**;
- explicit add-group evidence represented: **1 encounter**;
- explicit damage-window evidence represented: **1 encounter**.

Detailed historical closeout: `docs/phase9_encounter_model_closeout.md`.

That closeout was sufficient to prove the **engine**, but under the hardened roadmap standard it did not fully close the **required corpus review/persistence gate**. The phrase “low coverage is an enrichment gap” was too permissive because later encounter-aware optimization depends on the truth of those mechanics.

## Retrospective hardening completed

The later corpus audit established:

- boss source files: **490**;
- canonical boss encounter identities: **490 / 490 committed**;
- inferred mechanic rows requiring explicit semantic review: **109 across 35 bosses**;
- review decisions: **109 / 109**;
- accepted: **94**;
- rejected as currently inferred: **15**;
- pending: **0**;
- accepted rows persisted as `reviewed_single_source`: **94**;
- UESP evidence rows persisted: **94**;
- rejected rows persisted as canonical facts: **0**;
- first apply: **94 facts inserted / 94 evidence rows inserted**;
- second apply: **0 inserted / 94 facts existing / 94 evidence rows existing**, proving idempotency.

The reviewed-single-source path remains deliberately separate from corroboration-based promotion. Human review does not impersonate a second source.

## Remaining Phase 9 hardening gates

Phase 9 returns to plain **🟢 Complete** only after both are recorded:

1. **Post-persistence canonical audit**
   - expected reviewed-single-source facts: 94;
   - expected matching canonical facts: 94;
   - expected matching evidence rows: 94;
   - missing/conflicting canonical or evidence rows: 0.

2. **Structural boss-row verification**
   - confirm whether the prepared 490-boss structural import of abilities, explicit phases, and dialogue was actually applied to the canonical database;
   - if not applied, perform dry run → backup → controlled apply → post-write audit;
   - inferred mechanics must remain outside the structural-import shortcut.

**Hardened Phase 9 exit criteria:** the required boss corpus has canonical identities, source-backed structural data is verified in storage, every inferred mechanic has an explicit decision, accepted single-source mechanics are persisted with provenance, rejected/unsupported rows remain outside canonical truth, and post-write audits prove the database matches the reviewed plan.

---

# PHASE 10 · Encounter Evaluation
**Status: 🟢 Engine complete / 🟡 Retrospective revalidation required**

Phase 10 combines Encounter + Requirements + Roster + Builds and produces covered, redundant, insufficient, missing, conflict, and unknown outcomes while preserving the boundary between collective capability and provider assignment.

Historical closeout evidence:

- real saved builds: **2**;
- unique real characters: **2**;
- authoritative exit roster: **Magrat → DF Healer** and **Susan → Necro Tank**;
- both selected builds: **0 capability-resolution gaps**;
- Oaxiltso veteran: **fully evaluable = true**;
- Oaxiltso veteran: **capability-ready = true**;
- execution rows: **7**;
- provider rows: **0**, as expected for that validation encounter;
- execution corpus: **21 encounters with requirements**;
- fully evaluable encounters: **6**;
- fully ready encounters: **6**;
- covered requirements: **25**;
- unknown requirements: **31**;
- conflicting requirements: **0**;
- focused final checkpoint: **16 passed in 1.65s**;
- full suite after final historical Phase 10 changes: **2031 passed in 94.10s**;
- detailed closeout: `docs/phase10_encounter_evaluation_closeout.md`.

The evaluator architecture remains complete. However, Phase 9's later corpus hardening materially changes canonical encounter inputs, so the hardened dependency rule requires a retrospective integration rerun.

## Phase 10 retrospective gate

After Phase 9 hardening closes:

- rerun at least one real canonicalized encounter through Encounter + Requirements + Roster + Builds;
- prefer Oaxiltso for continuity plus one additional encounter whose mechanics entered through the reviewed-single-source path;
- verify covered/unknown/conflict outcomes remain explainable;
- record focused test output and the real integration result;
- do not require provider assignment here; that remains Phase 11.

**Hardened Phase 10 exit criteria:** BFF reliably evaluates a real roster against canonically persisted encounter facts and requirements, preserves unknown/conflicting evidence, and remains valid after upstream encounter-corpus hardening.

---

# PHASE 11 · Provider Assignment
**Status: 🟢 Complete**

Phase 11 moved BFF from “does the roster have the required support capability?” to “who should provide it here?” while preserving the boundary between encounter facts, raid-support requirements, provider capability, suitability, responsibility conflicts, and later build optimization.

Historical closeout evidence:

- provider assignment preserves Phase 10 VIABLE / UNRESOLVED / CONFLICTING evidence;
- suitability is explicit and evidence-backed;
- deterministic assignment does not use roster order as a hidden tie-breaker;
- responsibility-conflict evidence is explicit;
- Oaxiltso veteran + default raid coverage + real roster produced a deterministic War Horn provider assignment;
- focused checkpoint: **39 passed in 0.69s**;
- full regression suite: **2031 passed in 73.87s**;
- real configured provider evaluation: **PASS**;
- detailed closeout: `docs/phase11_provider_assignment_closeout.md`.

Phase 11 does not automatically reopen for Phase 9 mechanic enrichment because provider requirements are a separate semantic layer. If Phase 10 retrospective validation changes requirement/capability conclusions used by provider assignment, Phase 11 receives its own dependency-impact rerun.

**Exit criteria met on 2026-09-03.**

---

# PHASE 12 · Build Optimization
**Status: 🟡 Active**

The optimizer varies gear, sets, mythics, weapons, traits, enchants, skills, morphs, ultimates, CP, Mundus, food, potions, and configuration. It does not contain ESO math itself; it asks the rules engine.

Phase 12 must optimize **within the verified architecture** rather than creating a second combat model. Candidate changes must be scored through existing build, effect, static combat, sustain, combat-state, encounter, coverage, and provider-assignment systems. UNKNOWN and unsupported mechanics remain explicit and may not be silently treated as zero-cost improvements.

## Active priorities

1. inventory existing optimizer/minmax candidate-generation code before creating new search logic;
2. define one immutable build-candidate contract preserving canonical character/build identity and exact changes;
3. establish deterministic objective/result contracts before broad search;
4. score candidates only through authoritative existing math/effect/sustain services;
5. preserve required raid coverage and Phase 11 provider responsibilities while evaluating changes;
6. reject or explicitly mark candidates whose required mechanics cannot be evaluated;
7. start with tightly bounded candidate dimensions before combining gear, skills, CP, food, potions, and configuration;
8. validate against a real saved build and require an explainable baseline-vs-candidate comparison.

## Hardened Phase 12 exit criteria

Phase 12 may close only when all of the following are true:

- one authoritative immutable candidate representation exists;
- candidate generation is deterministic for identical inputs;
- objective metrics are explicit and named, with no hidden fallback score;
- the optimizer delegates ESO math to authoritative engine services rather than duplicating formulas;
- unsupported/unknown candidate consequences remain explicit and cannot win by being treated as zero;
- required raid coverage and assigned provider responsibilities are preserved or the candidate is explicitly rejected/degraded;
- at least one real saved build completes baseline → candidates → scoring → ranking → explanation;
- winning-candidate reasoning lists changed inputs, expected improvement, sustain/coverage tradeoffs, and unresolved assumptions;
- focused optimizer tests are green;
- a full regression checkpoint is recorded before Phase 12 is marked complete;
- any Phase 9/10 dependency required by the selected optimization mode is green under the hardened roadmap standard.

---

# PHASE 13 · Rotation Engine
**Status: 🔴 Planned**

Start with semi-static rotations, then add dynamic priorities, duration/recast windows, resource awareness, proc alignment, execute, movement, interruptions, mechanic handling, and healing rotations.

**Hardened exit criteria:** BFF can produce and evaluate a realistic damage, support, or healing rotation from verified skill behavior and resource constraints; action timing is deterministic from identical inputs; unsupported mechanics remain explicit; at least one real build is validated end-to-end; focused and appropriate regression gates pass.

---

# PHASE 14 · Combat Simulation
**Status: 🔴 Planned**

```text
CombatState
      ↓
Action
      ↓
Effect / Damage
      ↓
Resource Change
      ↓
State Change
      ↓
Next Action
```

**Hardened exit criteria:** BFF can model combat over time with explicit event ordering, resource/state changes, supported target behavior, deterministic replay from identical deterministic inputs, and auditable unresolved boundaries.

---

# PHASE 15 · Encounter-Aware Optimization
**Status: 🔴 Planned**

Compare builds across DPS, burst, sustained damage, execute, uptime, sustain, survivability, positioning, mechanic compliance, support contribution, phase compression, and execution complexity.

**Prerequisite gate:** Phases 9 and 10 must be green under the hardened completion standard. Encounter-aware optimization may not consume partially reviewed encounter truth as if it were complete.

**Hardened exit criteria:** BFF answers which build produces the better outcome in a real canonically persisted encounter, explains why, preserves unknown/conflicting mechanics, and demonstrates the result against at least one real saved build and encounter.

---

# PHASE 16 · Explanation Engine
**Status: 🔴 Planned**

Every recommendation should expose change, expected impact, reason, tradeoff, encounter effect, confidence, and evidence.

**Hardened exit criteria:** recommendations are inspectable and defensible, distinguish modeled fact from assumption, expose provenance/confidence, and never fabricate explanations for unsupported outcomes.

---

# PHASE 17 · ESO Logs Validation
**Status: 🔴 Planned**

Use logs as a later validation feedback loop:

```text
MODEL
  ↓
Expected Result
  ↓
Observed Log Result
  ↓
Difference
  ↓
Diagnosis
  ↓
Model Refinement
```

Logs are validation/corroboration, not a substitute for authoritative static rules when those rules can be sourced directly.

**Hardened exit criteria:** log-derived observations remain attributable to specific logs/patch context, discrepancies are measured rather than patched with unexplained fudge factors, and model changes preserve canonical-source precedence.

---

# PHASE 18 · Strategy Engine
**Status: 🔴 Planned**

Evaluate safe, balanced, aggressive, and experimental strategies against roster capability, encounter risk, execution difficulty, confidence, expected gain, and failure cost.

**Hardened exit criteria:** BFF can compare practical strategies for an actual roster and encounter, explain risk/reward and uncertainty, and prefer a lower theoretical ceiling when evidence indicates a better expected real outcome.

---

# PHASE 19 · Full Raid Optimizer
**Status: 🔴 Planned**

```text
12 CHARACTERS
       ↓
12 BUILDS
       ↓
ENCOUNTER / REQUIREMENTS
       ↓
CAPABILITY ANALYSIS
       ↓
PROVIDER ASSIGNMENT
       ↓
BUILD CANDIDATES
       ↓
COMBAT SIMULATION
       ↓
EXPECTED OUTCOME
       ↓
STRATEGY OPTIONS
       ↓
RECOMMENDATION + EXPLANATION
```

**Hardened exit criteria:** a real 12-player roster can be optimized end-to-end against a canonically persisted encounter; assignments, candidate changes, simulation assumptions, strategy tradeoffs, and explanations remain auditable; unsupported data cannot silently improve the score; rerunning identical deterministic inputs yields the same recommendation; appropriate full regression and real-world validation gates pass.
