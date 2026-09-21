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
**Status: 🟢 Complete**

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

## Retrospective hardening closeout

The hardened corpus review and persistence gate completed on **2026-09-03**:

- boss source files: **490**;
- canonical boss encounter identities: **490 / 490**;
- inferred mechanic rows requiring semantic review: **109 across 35 bosses**;
- review decisions: **109 / 109**;
- accepted: **94**;
- rejected as currently inferred: **15**;
- pending: **0**;
- accepted rows persisted as `reviewed_single_source`: **94**;
- UESP evidence rows persisted: **94**;
- rejected rows persisted as canonical facts: **0**;
- first apply: **94 facts inserted / 94 evidence rows inserted**;
- second apply: **0 inserted / 94 facts existing / 94 evidence rows existing**, proving idempotency;
- post-persistence audit: **94 / 94 canonical facts matched**, **94 / 94 evidence rows matched**, **0 missing**, **0 conflicting**;
- focused persisted-mechanic audit tests: **3 passed in 0.22s**;
- structural source audit: **490 / 490 health**, **2070 / 2070 abilities**, **4 / 4 explicit phases**, **2274 / 2274 dialogue rows**, **2450 / 2450 section rows**, **0 problems**;
- structural dry run: **490 ready**, **0 blocked**;
- controlled structural apply created a SQLite backup before write and independently verified the same exact counts after commit.

The reviewed-single-source path remains deliberately separate from corroboration-based promotion. Human review does not impersonate a second source. Inferred mechanics remain outside the structural-import shortcut.

Detailed retrospective closeout: `docs/phase9_retrospective_hardening_closeout.md`.

**Hardened Phase 9 exit criteria met on 2026-09-03.**

---

# PHASE 10 · Encounter Evaluation
**Status: 🟢 Complete**

Phase 10 combines Encounter + Requirements + Roster + Builds and produces covered, redundant, insufficient, missing, conflict, and unknown outcomes while preserving the boundary between collective capability and provider assignment.

Historical closeout evidence:

- real saved builds: **2**;
- unique real characters: **2**;
- authoritative exit roster: **Magrat → DF Healer** and **Susan → Necro Tank**;
- both selected builds: **0 capability-resolution gaps**;
- Oaxiltso veteran: **fully evaluable = true**;
- Oaxiltso veteran: **capability-ready = true**;
- provider rows: **0**, as expected for that validation encounter;
- focused final checkpoint: **16 passed in 1.65s**;
- full suite after final historical Phase 10 changes: **2031 passed in 94.10s**;
- detailed historical closeout: `docs/phase10_encounter_evaluation_closeout.md`.

## Retrospective revalidation after Phase 9 hardening

The dependency-impact rerun completed on **2026-09-03** against the reviewed canonical mechanic corpus.

Canonical consumption boundary:

- raw inferred source mechanics: **109**;
- canonical mechanic facts: **94**;
- accepted inferred replacements: **94**;
- rejected/unpersisted inferred: **15**;
- canonical facts without raw inferred source rows: **0**;
- raw inferred downstream leaks: **0**;
- result: **PASS**.

Focused regression checkpoint:

- **38 passed in 3.34s**.

Current canonical-filtered execution corpus:

- encounters with requirements: **18**;
- fully evaluable encounters: **6**;
- fully ready encounters: **6**;
- covered requirements: **20**;
- unknown requirements: **24**;
- conflicting requirements: **0**.

Real roster revalidation used **Magrat → DF Healer** and **Susan → Necro Tank**, with **0 capability-resolution gaps** on both selected builds.

Oaxiltso veteran control result:

- fully evaluable: **true**;
- capability-ready: **true**;
- execution rows: **6**;
- provider rows: **0**;
- Phase 10 exit ready: **true**.

Hiath the Battlemaster veteran boundary result:

- execution rows: **5**;
- covered: Agony interrupt, Purifying Light cleanse, Solar Disturbance interrupt;
- unknown: Invisibility positioning because no source-backed execution-method fact is persisted;
- unknown: Roll Dodge movement because the source describes **Hiath's own roll dodge**, exposing an actor-semantics limitation in the current requirement contract rather than a player movement action;
- conflicting requirements: **0**;
- provider rows: **0**.

The Hiath result is an expected preserved-UNKNOWN boundary, not a reason to manufacture player execution semantics. Phase 10's promise is correct evaluation and explicit uncertainty, not universal encounter completeness.

Detailed retrospective closeout: `docs/phase10_retrospective_revalidation_closeout.md`.

**Hardened Phase 10 exit criteria met on 2026-09-03.**

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
**Status: 🟢 Complete**

Phase 12 established the authoritative bounded build-optimization path. The optimizer represents exact immutable candidate changes, delegates ESO math and capability evidence to existing engine services, keeps hard constraints separate from objective score, and ranks only candidates that have enough evidence to be rankable.

The closed real-data scope is deliberately bounded one-change optimization for Mundus, armor traits, armor enchants, and food/drink. The candidate/evaluator contracts are reusable for later gear-set, mythic, weapon, skill, morph, ultimate, CP, potion, and configuration expansion; Phase 12 closeout does not pretend those broader combinatorial dimensions are already exhaustively searched.

Closeout evidence on **2026-09-03**:

- one immutable `BuildCandidate` / `BuildChange` representation preserves canonical identity and exact before/after changes;
- deterministic candidate generation and ranking use explicit named objective metrics with no hidden fallback score;
- `WORSENED`, `UNSATISFIED`, and `UNKNOWN` hard-constraint states block ranking rather than becoming point penalties;
- candidate scoring delegates to existing static build/healing, sustain, capability, encounter-evaluation, and provider-assignment services;
- required capability coverage and baseline provider responsibility remain explicit gates;
- unsupported or unresolved evidence cannot win by being treated as zero;
- real saved build **Magrat → DF Healer** completed baseline → candidates → scoring → ranking → explanation with Oaxiltso provider context and **Necro Tank** roster support;
- winning recommendation: **Witchmother's Potent Brew → Ghastly Eye Bowl**;
- winning healing comparison delta: **+2150.139**;
- winning Magicka sustain: **repaired**, minimum **3573**, ending **6314**;
- capability coverage: **preserved**;
- provider responsibility: **preserved**;
- selected-candidate unresolved evidence: **none**;
- provisioning search hardening reduced the real audit from **121 discovered** to **73 evaluated** candidates without changing the winner or hard-constraint conclusions;
- focused optimizer/performance checkpoint: **117 passed in 8.94s**;
- final full regression checkpoint: **2232 passed in 87.58s**;
- detailed closeout: `docs/phase12_build_optimization_closeout.md`.

The healing value used by the closeout audit is a modeled comparison score, not HPS. The healer/DD role boundary remains explicit; diagnostic role mismatch does not become a valid healer recommendation.

**Hardened Phase 12 exit criteria met on 2026-09-03.**

---

# PHASE 12.5 · Team Workflow Integration
**Status: 🟢 Complete**

Phase 12.5 is the product-integration bridge between the completed bounded build optimizer and the later temporal engines. It does **not** expand Phase 12's mathematical search scope and it does **not** substitute UI plumbing for Phase 13 Rotation Engine work.

The authoritative user workflow is:

```text
COMP MAKER
   ↓
NAMED TEAM + EXACT CHAIR / BUILD ASSIGNMENTS
   ↓
ROSTER
   ↓
LOAD TEAM IN OPTIMIZATION
   ↓
AUDIT / IMPROVE / COMPARE
   ↓
ROSTER
```

Active scope, in order:

1. **Canonical team identity**
   - a named team created in Comp Maker, displayed in Roster, and loaded in Optimization is the same user-facing team identity;
   - generated-plan persistence may remain an implementation detail, but it must not create a second competing team concept in the UI;
   - recruits remain assignment slots, never fabricated roster people.

2. **Structured assignment persistence**
   - preserve slot, player/recruit state, class, role, exact selected build, source identity, gear, skills/abilities, Mundus, candidate/template identity, and explicit unresolved fields where known;
   - do not reconstruct structured application state by scraping human-readable evidence text when a canonical field can be persisted instead.

3. **Visible assigned state in Comp Maker**
   - each chair clearly shows the exact build/source currently assigned before transfer;
   - explicit manual choices remain authoritative and are never silently reranked during transfer.

4. **Hard-constraint routing integrity**
   - class and required-gear constraints apply to every candidate source, including saved builds, reference templates, and ESO Logs snapshots;
   - wrapper/install order may not bypass hard constraints.

5. **Static Optimization integration groundwork**
   - Optimization loads a named team from Roster and consumes existing canonical build, coverage, provider, sustain, and bounded optimization evidence;
   - placeholder recommendation surfaces are replaced only where existing engine evidence supports the claim;
   - temporal/rotation-dependent conclusions remain deferred to Phases 13–15.

6. **Team A / Team B bounded comparison groundwork**
   - compare only currently supported canonical/static metrics;
   - do not label modeled single-event or bounded objective values as parse DPS, raid ceiling, or simulated encounter outcome.

7. **Recruit → real player → reusable build workflow**
   - a prescribed recruit chair can later be assigned to a real roster player without rebuilding the team;
   - the player may keep an existing build or save the prescribed setup as a new reusable Build while preserving the original Build unchanged.

Current Phase 13.2 bridge work now also supplies reusable Comp Maker / Optimization provider contracts without weakening Phase 12.5 identity and persistence boundaries:

- source-neutral named-buff marginal value and duplicate suppression;
- recipient-capacity modeling, including repeated applications and concurrent coverage limits;
- sequential roster context so later chairs do not receive credit for already-covered effects;
- timed provider windows and intentional staggered multi-carrier strategies;
- scoped uptime targets with explicit provenance rather than universal hard-coded percentages;
- provider requirement compatibility remains backward compatible when coverage/timing policy is not supplied.

Verified focused checkpoints supplied by the user:

- Extreme / Comp optimization contract: **147 passed in 25.38s**;
- marginal provider bridge: **50 passed in 1.08s**;
- recipient-coverage bridge: **33 passed in 0.88s**.

The temporal/provider suite exposed one fixture mismatch after later distinct-carrier work; the fixture was corrected in commit `72c25c0`, but the corrected expanded temporal suite still requires a fresh reported rerun before it is recorded green here.

**Phase 12.5 exit criteria:** a representative real team can be created in Comp Maker, saved and inspected in Roster, loaded into Optimization, and transferred back without losing or silently changing team identity, exact assignment choice, source, gear/skill evidence, hard constraints, recruit state, or unresolved boundaries. Focused regression tests must pass, a real-data end-to-end workflow must be demonstrated, and an appropriate full regression checkpoint must be recorded before Phase 12.5 is closed.

### Phase 12.5 canonical closeout audit — pending validation

A current-architecture, read-only closeout gate now exists at
`tools/audit_phase12_5_closeout.py`. It audits persisted `RaidPlan` state against
the reusable saved-Build library and Roster rather than treating the older
generated-roster draft as current authority.

The audit checks:

- stable team, chair, player, character, and Build identity;
- explicit recruit/open-chair state without fabricated player/Build ownership;
- class, role, gear-lock, and assignment integrity;
- structured provenance for non-saved Comp candidates;
- preservation of explicit unresolved evidence;
- Raid Plan persistence through a temporary round-trip only;
- Optimizer Adviser read-only behavior without rewriting the Raid Plan.

The older generated-draft Phase 12.5 audit remains useful as migration/legacy
compatibility evidence but is not the canonical closeout authority.

**Validation still required before changing Phase 12.5 to Complete:** focused tests
for the new audit, one real saved 12-player Raid Plan audit, the relevant
provider/temporal checkpoint, and a fresh full-suite regression. No green result
is claimed until those commands are actually reported passing.

### Phase 12.5 validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **34 passed in 22.84s** across the canonical Phase 12.5 workflow audit, legacy
  workflow audit, Raid Plan saved-build resolution, Raid Plan repository, and
  Optimizer Adviser suites.

Real saved Raid Plan audit:

- plan: **Performance Mode GS** (`sunspire-performance-mode-gs`);
- trial: **Sunspire**;
- chairs: **12**;
- assigned players: **8**;
- recruit/open chairs: **4**;
- selected saved Builds: **0**;
- resolved saved Builds: **0**;
- explicit unresolved chairs: **8**;
- every reported identity, recruit-state, class/role/gear constraint, assignment,
  unresolved-state, temporary persistence, and read-only Optimizer invariant: **PASS**;
- audit problems: **0**;
- Optimizer Adviser findings: **12 blockers / 35 actionable**, correctly treated as
  plan-readiness evidence rather than workflow-pipeline failure;
- overall canonical workflow audit: **PASS**.

This real audit proves the current Raid Plan workflow preserves incomplete planning
state honestly, including open recruits and unresolved evidence. Because this specific
plan has no selected saved Builds, it does **not** satisfy the separate real selected-
Build round-trip proof by itself.

### Phase 12.5 full regression checkpoint — 2026-09-19

User-reported full-suite regression:

- **3029 passed in 439.31s (0:07:19)**
- **0 failures**

The canonical real-data workflow audit and the focused Phase 12.5 integration suites
were already green. The only unperformed exercise is a live Raid Plan containing an
explicit selected saved Build. The user is not assigning a Build at this time, so that
exercise is deferred until natural use rather than manufactured solely for validation.

**Phase 12.5 status: Complete.**

The completed contract covers team/chair/player/character identity, recruit state,
structured candidate provenance, class/role/gear constraints, assignment ownership,
explicit unresolved boundaries, durable Raid Plan persistence, and read-only Optimizer
consumption. A future real selected-Build audit remains a non-blocking verification
exercise and must not silently change or fabricate Build ownership.



---

# PHASE 13 · Rotation Engine
**Status: 🟡 Active on `phase13.2`**

Phase 13 is active in controlled overlap with the still-open Phase 12.5 product-integration work. Phase 13 closeout remains gated on canonical Character → Build → Team identity integration; current engine development may proceed so long as it does not invent a competing identity or persistence model.

Start with semi-static rotations, then add dynamic priorities, duration/recast windows, resource awareness, proc alignment, execute, movement, interruptions, mechanic handling, and healing rotations.

## Phase 13.2 current engine work

The active line now includes two mutually reinforcing tracks.

### A. Extreme build / class-route search

BFF can efficiently search the reviewed pure-class / Class Mastery and legal subclass structural universe without recomputing static route structure for every request.

Implemented and covered:

- precomputed Extreme Build Catalog with database fingerprint and subclass-rule version;
- **3,220** legal class configurations, **1,330** unique three-line sets, and **21** class skill lines in the generated catalog used by the current local database snapshot;
- independent front/back six-slot allocation search;
- active-bar versus either-bar standing-effect scope;
- reviewed passive formulas and standing-skill families;
- source-neutral named-buff stacking and external-context marginal value;
- stale or malformed catalog rejection with canonical live fallback;
- structural pruning and unique-line-set memoization instead of blind 28×28 repeated scoring;
- physical-resistance regression preserving the independent-bar **10,414** reviewed result rather than the older **9,174** compromised result;
- verified expanded Extreme / Comp contract checkpoint: **147 passed in 25.38s**.

The output remains a **best reviewed lower bound**, not an unsupported claim of a globally optimal ESO build. Broader class passive, gear, race, Mundus, CP, enchantment, proc, runtime, and encounter coverage must continue to expand before that boundary changes.

#### Extreme Builds role-complete completion roadmap

Extreme Builds is one shared legal-character optimization engine with role-specific objective packages for **Healer, Tank, and Damage Dealer**. It must not fork into separate competing build engines. All roles reuse the same canonical Character → Build identity, legal class/subclass search, static combat math, runtime/effect evidence, candidate pruning, unresolved-boundary handling, and search-space audit contracts.

Current engineering estimate toward a role-complete Extreme product is approximately **55–60% overall**. Architecture is farther along than exhaustive ESO mechanic/corpus coverage. Percentages below are planning estimates, not phase-closeout claims.

##### E1. Unified runtime snapshot — 🟢 Complete

E1 now replaces fragmented runtime scenario inputs with one deterministic runtime history plus one exact snapshot time:

```text
Runtime History
  ├── potion activations
  ├── cast buffs
  ├── triggered skills
  ├── gear procs
  ├── cooldown history
  ├── deterministic chance rolls
  ├── condition evidence
  ├── stacking / refresh
  ├── bar provenance / transitions
  ├── source-persistence semantics
  ├── explicit condition windows
  └── target applicability
          +
   exact snapshot time
          ↓
      CombatState
```

Closeout on **2026-09-15** proved one role-neutral runtime contract for named buffs, generic timed effects, potion windows, triggered skills, gear procs, `SELF_OR_ALLY`, explicit condition evidence, ordered event streams, cooldowns, stacking, exact active-window boundaries, bar-tagged activation, coherent bar-transition history, and reviewed source-persistence behavior. Restoration-heavy and Sacred Ground runtime windows now enter the production Extreme healer path through the same snapshot instead of parallel healer-only truth.

The closed Weapon Damage and Spell Damage records also expose machine-readable ownership and deterministic runtime witnesses. E1 owns only ordered player runtime history; target Health / Off Balance remain `target_state`, same-build higher resource remains `structural_state`, Font / Calculated Defense remain `class_runtime`, and Sorcerer slot legality remains `active_bar`.

Real integration used the canonical saved **Margrat → DF Healer** build and reported `snapshot_unresolved_count=0`, `e1_real_integration_ready=True`, `e1_healer_runtime_bridge_closed=True`, `e1_power_runtime_bridge_closed=True`, and `e1_closeout_audit_ready=True`. Focused E1 regression: **45 passed in 8.29s**. Full repository regression: **2970 passed in 198.10s**, failures **0**. Detailed closeout: `docs/extreme_e1_unified_runtime_closeout.md`.

The audit also exposed a separate canonical identity discrepancy: the live healer build is currently owned by `Margrat`, while a distinct `Magrat` character exists with zero builds. That issue belongs to Phase 1 / identity cleanup and does not reopen E1.

##### E2. Complete shared legal-character search — 🟡 partial

The universal candidate generator must eventually cover, search, safely prune, or explicitly block every relevant legal dimension:

- race;
- base class and legal subclass route;
- character progression and class passives;
- attributes;
- Mundus;
- food / drink;
- potion capability and explicit use state;
- armor weights and armor passives;
- gear sets, mythics, monster sets, arena weapons, and proc mechanics;
- armor, jewelry, and weapon traits;
- glyphs / enchantments;
- front/back weapon configuration and weapon passives;
- active skills, morphs, ultimates, and standing/slotted effects;
- Champion Points;
- Class Mastery where legally available;
- exact event/runtime state required by the selected objective.

The existing Extreme catalog already provides the legal class/subclass structural universe, independent bars, active-bar/either-bar scope, reviewed passive families, memoization, and structural pruning. Remaining work is primarily exhaustive dimension integration and mechanic coverage rather than a replacement combinatorial engine.

##### E3. Mechanic-coverage audit — 🟡 continuous requirement

For every candidate mechanic, Extreme must preserve one of four states:

```text
SUPPORTED
CONDITIONAL + PROVABLE
UNRESOLVED
UNSUPPORTED
```

Unknown mechanics never silently become zero. Exhaustive audits must cover class/racial/armor/weapon passives, sets and procs, mythics, arena weapons, skills/morphs/ultimates, CP, Mundus, consumables, traits/enchants, and Class Mastery. Inventory coverage is not mechanic coverage.

##### Healer objective package

**H1. MOST Actual Heal — ~80% engineering estimate.** This is the most mature role objective. Existing coverage includes legal heal discovery, HEAL-only component math, mixed damage/heal exclusion, Critical Healing and cap behavior, Healing Done and ability-family modifiers, conditional/passive modifiers, low-health scenarios, Major Mending, named buffs, potion/skill source discovery, triggered skills, gear procs, runtime conditions, self-or-ally targeting, ordered runtime history, and exact expiration. Remaining work is unified snapshot orchestration plus exhaustive race/attributes/gear/CP/traits/glyphs/weapon/skill/mechanic search and denominator proof.

**H2. MOST Emergency Heal — ~70%.** Reuse H1 with explicit low-health and emergency-state assumptions. Complete the same exhaustive character/mechanic dimensions before claiming a global maximum.

**H3. MOST Sustained Healer — ~30–35%.** Requires rotations, HoTs, burst healing, resources, cooldowns, proc windows, recipient/target-count policy, overheal interpretation, and fight duration. This depends materially on Phase 13 Rotation Engine and later Phase 14 Combat Simulation rather than static snapshot optimization alone.

**H4. MOST Raid-Support Healer — ~50%.** Multi-objective search across healing adequacy, buff/debuff coverage and uptime, provider workload, sustain, and survivability. Reuse Phase 11/12.5 provider evidence rather than inventing a healer-specific support score.

##### Tank objective package

**T1. MOST Raw Physical Resistance — ~65%.** Finish exhaustive race, attributes, armor, traits, enchants, Mundus, sets, skills/passives, CP, temporary buffs, and active-bar state. Keep raw stat maximum separate from effective mitigation/cap interpretation.

**T2. MOST Raw Spell Resistance — ~60%.** Reuse T1 architecture with spell-resistance-specific modifier coverage.

**T3. MOST Health — ~55%.** Exhaustively search race, attributes, food, enchants, gear, CP, passives, and temporary Max Health effects.

**T4. MOST Blocky — ~40%.** Treat largest block mitigation, lowest block cost, and longest sustainable block as distinct objectives. Model block mitigation, block cost, stamina state, recovery constraints, weapon legality, CP, sets, passives, and runtime buffs without collapsing them into one arbitrary tank score.

**T5. MOST Survivable Tank — ~25–30%.** Combine incoming-damage sequence, resistance/mitigation, block, shields, self-healing, health, recovery, and sustain. A true survivability maximum depends on Phase 14 temporal combat simulation.

**T6. MOST Support Tank — ~45%.** Optimize raid buffs/debuffs and provider coverage subject to tank legality, sustain, survivability, recipient reach, and uptime. Encounter-specific conclusions belong later to Phase 15.

##### Damage Dealer objective package

**D1. MOST Single Hit — ~55%.** DD snapshot counterpart to MOST Actual Heal. Search the complete legal character plus target state, buffs/debuffs, proc state, resistance/penetration, and exact damage-event semantics to find the largest legal single damage event.

**D2. MOST Critical Hit — ~50%.** Find the largest legally crittable event without multiplying by critical chance. Preserve crit eligibility and target Critical Resistance semantics.

**D3. MOST Execute Hit — ~40%.** Add explicit target-health state, execute scaling, execute passives/skills, target debuffs, and runtime conditions.

**D4. MOST AoE Event — ~35%.** Keep largest hit to one target separate from aggregate damage across an explicit target count. Never silently convert multi-target aggregation into a single-target objective.

**D5. MOST Bash Damage — 🟡 existing novelty lane.** Fold existing MOST Bashy infrastructure into the shared DD/tank objective framework rather than maintaining a separate build engine. Outstanding bash-channel and dual-bar One Hand + Shield legality/mechanic gaps remain explicit blockers.

**D6. MOST Sustained DPS — ~30–35%.** Requires build + deterministic rotation + DoT/proc/cooldown/resource/execute state + simulation duration. This is intentionally downstream of the snapshot Extreme core and depends on Phases 13–14. **Phase 14 handoff now exists:** one saved DD build plus its canonical saved RotationPlan can be evaluated through Combat Simulation against explicit target Health/resistance and normalized into an Extreme sustained-DPS lower-bound record. **Candidate-set comparison also exists:** multiple explicitly supplied saved-build witnesses can be evaluated under the same target assumptions and ranked, but a leader is withheld when any candidate is incomplete, execution horizons differ, or the top value is tied. **Saved-state discovery/search now exists:** the optimizer can discover the complete eligible canonical saved DD/DPS denominator, preserve blocking versus informational exclusions, and compare every eligible saved build/rotation witness under one scenario. This is complete only for saved user state. **Generated structural frontier now exists:** race, legal class route, all 64-point attribute allocations, and active-bar coordinates are deterministically pageable from the canonical Extreme global universe without materializing the whole Cartesian product. **Proof-safe sustained-DPS pruning now exists:** generated branches may be discarded only when an externally proven optimistic DPS ceiling is strictly below a legal incumbent; missing/unproven bounds and tie-capable equal ceilings remain open. **Dynamic refinement inventory now exists:** generated structural candidates can enumerate canonical Mundus, mapped food/drink, modeled armor trait/enchant, and route-filtered active-skill identity axes without fabricating a finished build. **Rotation-ceiling aggregation now exists:** an explicit RotationPlan can receive a proof-safe whole-plan DPS ceiling only when every scheduled DD action has an externally proven optimistic total covering direct, periodic, and triggered consequences within the plan horizon. **Action-bound promotion now exists:** exact canonical action occurrences can become pruning ceilings only when a supplied dominance proof covers every required still-open mutation axis; otherwise the branch remains fail-open. **First concrete mutation-axis dominance producer now exists:** one exact action witness can exhaust the canonical joint Mundus × mapped provisioning grid and prove an absolute action-damage ceiling for those two axes when every combination resolves. **Lazy armor trait/enchant frontier now exists:** sustained-DPS search can preserve the full modeled armor trait/enchant denominator for actually equipped armor slots and page it deterministically without materializing the Cartesian product. **Jewelry and weapon identity frontiers now exist:** sustained-DPS search can lazily enumerate equipped jewelry trait/glyph-family states and weapon trait/enchant-family states without materializing their Cartesian products. Weapon enchant scoring remains runtime-owned. Dynamic build synthesis for gear topology, CP, potions, passives, full skill-bar topology/morph legality, runtime state, dominance/scoring over equipment frontiers and remaining axes, generated rotation families, frontier scoring, and proof of a theoretical maximum remain open.

##### E4. Search-space proof — 🔴 required before “global maximum”

Every definitive Extreme result must report the legal search denominator and disposition of candidates. At minimum expose counts for class routes, races, attribute configurations, Mundus choices, gear combinations discovered/pruned, CP configurations, skills, unsupported mechanics, and unresolved mechanics. The solver must demonstrate that every relevant legal category was searched, safely pruned, or explicitly unresolved before the UI may label a result a **global maximum**. Otherwise the result remains a **best reviewed lower bound**.

##### E5. Search-performance engineering — 🟡 partial

Continue objective-aware dominance pruning, safe upper-bound pruning, memoization, equivalent-state deduplication, branch-and-bound, and staged candidate expansion. Existing Extreme catalog memoization/structural pruning is the foundation; exhaustive gear/CP/skill search must not become a blind Cartesian product.

##### E6. Real-build validation — 🔴 required closeout gate

Validate at least one real saved character/build for each role through baseline → Extreme search → winning build → explanation → unresolved audit → comparison:

- Healer: **Magrat → DF Healer** is the primary real validation path;
- Tank: use a real canonical saved tank build;
- Damage Dealer: use a real canonical saved DD build.

Synthetic fixtures remain necessary but cannot satisfy the real-integration gate by themselves.

##### E7. Role-complete Extreme product surface — 🔴 planned

The final Extreme UI should select **role**, **objective**, **scenario**, target/runtime assumptions, and reviewed-vs-exhaustive search depth, then show the complete winning build, exact objective result, why it won, runtime/buff proof, search coverage, candidates eliminated, unresolved mechanics, and proof/confidence status. No unexplained maximum number may be presented as authoritative.

##### Cross-role constrained optimization

After single-objective role packages are trustworthy, add constrained multi-objective searches rather than arbitrary universal scores. Examples:

- healer: maximize healing subject to required support effects, minimum sustain, and survivability;
- tank: maximize survivability subject to taunt/support obligations and minimum sustain;
- DD: maximize damage subject to sustain, assigned raid support, and mechanic compliance.

These constrained builds are the bridge from laboratory Extreme objectives to raid-usable recommendations and ultimately Phase 15 encounter-aware optimization.

##### Planned completion order from current state

```text
1. Unified runtime snapshot orchestration
2. Finish Healer single-event snapshot objectives
3. Generalize exact-event optimizer to DD single-hit / crit / execute
4. Finish Tank static/snapshot objectives
5. Complete shared race / attributes / gear / CP / traits / glyphs / weapon search
6. Run exhaustive mechanic-corpus and search-space denominator audits
7. Validate one real saved build per role
8. Close snapshot Extreme Engine
9. Use Phase 13 rotations for sustained role objectives
10. Use Phase 14 simulation for sustained DPS / healing / survivability
11. Use Phase 15 encounter context for raid-usable Extreme recommendations
```

Planning snapshot from 2026-09-09:

| Extreme area | Approximate engineering progress |
| --- | ---: |
| Shared legal class/subclass architecture | 90% |
| Static character calculation infrastructure | 90% |
| Runtime/proc architecture | 85% |
| Unified runtime snapshot orchestration | 100% |
| Whole-character exhaustive candidate dimensions | 55% |
| Mechanic corpus coverage | 50% |
| Search-space proof / exhaustive audit | 30% |
| Healer snapshot Extreme | 80% |
| Tank snapshot Extreme | 55% |
| DD snapshot Extreme | 50% |
| Sustained/temporal Extreme | 25–30% |
| Encounter-aware Extreme | 20% |
| **Role-complete Extreme product** | **55–60%** |

These estimates track engineering readiness only. They do not supersede the roadmap completion standard, corpus audits, real-integration gates, or regression requirements above.

### B. Team provider orchestration for Comp Maker / Optimization

The team optimization bridge now distinguishes four questions that were previously easy to collapse into one misleading “provider exists” flag:

```text
DOES THE TEAM HAVE THE EFFECT?
          ↓
DOES THIS CANDIDATE ADD MARGINAL VALUE?
          ↓
CAN THE PROVIDER REACH THE REQUIRED RECIPIENTS?
          ↓
IS THE EFFECT ACTIVE AT THE RIGHT TIMES / UPTIME?
```

Implemented contracts include:

- duplicate named effects receive zero marginal tie-break credit when already supplied by a skill, potion, set, passive, or group provider;
- hard provider IDs and role constraints remain authoritative and cannot be weakened by marginal-value scoring;
- recipient coverage supports targets per application and maximum useful/concurrent applications per refresh cycle;
- six-target mechanics can require repeated applications to cover a 12-player group, while a one-instance six-target provider can remain explicitly partial;
- provider effects selected for one open chair are carried into the evolving team context for later chairs;
- timed applications can be staggered across multiple carriers rather than being incorrectly deleted as duplicates;
- strategy may explicitly require a minimum number of distinct carriers, such as tank + healer support-ultimate rotations;
- temporal evaluation reports covered time, uncovered gaps, overlap, active sources, and target-uptime attainment;
- target uptime is effect/encounter/phase policy, not a universal constant.

### C. BTVTools calibration evidence

User-supplied BTVTools screenshots from a Lokke hard-mode fight are now accepted as **benchmark/calibration evidence**, not canonical static ESO mechanics. They demonstrate why provider policy needs encounter/effect scope and provenance.

Visible examples include:

- Major Berserk: **27.9% observed / 96% BTV target**;
- Major Slayer: **56.0% observed / 90% BTV target**;
- Powerful Assault: **85% observed / 95% BTV target**;
- Minor Courage: **84% observed / 97% BTV target**;
- Major Vulnerability: **38.3% observed / 56% BTV target**;
- Off Balance: **6.6% observed**, with BTV showing a theoretical maximum around **31.8%** for its displayed **7s / 22s cycle**.

The screenshot corpus also includes buff pages and critical-damage timelines that can support later calibration of overlapping Major Force / Brittle / other support windows. Screenshot-derived benchmarks must retain provenance and fight scope and may not silently become universal game constants.

### D. Provider rotation-workload comparison

The first source-neutral provider-workload contract now sits on top of the existing
recipient and temporal coverage gates. It can aggregate one or more contributor
rotations and expose, without inventing a universal weighted score:

- provider applications and refreshes per minute;
- provider GCD occupancy;
- resource spend by resource type;
- Ultimate spend;
- occupied provider bar slots;
- whole-plan skill, Ultimate, heavy-attack, bar-swap, and other action counts;
- caller-evidenced primary-role displacement;
- unresolved cost, action binding, and bar ownership as comparison-blocking evidence.

Two plans may be compared only when both meet recipient coverage, meet temporal
coverage, and have resolved workload evidence. The comparison deliberately reports
independent deltas rather than declaring that one heavy attack, GCD, bar slot,
resource cost, or Ultimate point has a universal exchange rate.

The canonical workload bridge now derives provider-action evidence from the exact
saved Character → Build identity and scheduled action. It reuses authoritative
ability-cost, saved-build slot, and imported cast/channel-timing services to resolve:

- final Magicka, Stamina, or Health skill cost after currently verified racial,
  armor, and jewelry cost modifiers;
- final ordinary canonical Ultimate cost after currently verified build modifiers;
- independent cost accounting for supported compound-resource skills;
- exact scheduled-bar legality and occupied provider slot;
- cast/channel occupancy for each provider application;
- only action-relevant unresolved evidence, without allowing an unrelated unused
  skill gap elsewhere on the build to poison the comparison.

General GCD duration and primary-role displacement remain explicit caller policy or
evidence. They are not inferred from zero cast/channel time.

Provider workload can now retain the canonical recipient-capacity and temporal-
coverage result objects that authorized the comparison. Their actual conclusions
override stale copied booleans, and UI-ready explanation evidence exposes recipient
counts, covered time, targets, gaps, distinct-carrier failures, casts, resources,
Ultimate, bar space, and role displacement without inventing a universal winner.

Comp Maker and Team Optimization now share a theme-native Provider Rotation Workload
card and typed presentation path for those exact workload/comparison objects. Until
a canonical rotation result is attached, the visible card explicitly distinguishes
static capability availability from recipient coverage, uptime, sustain, and role
disruption. Editing the composition or optimization selection clears attached
workload evidence so a result from an older team cannot remain on screen as if it
still applied.

The shared team surfaces can now generate candidate workload projections from their
currently selected exact saved builds when supplied explicit provider strategy,
coverage, rotation-plan, progression, GCD, and role-displacement evidence. The
orchestrator binds contributors by exact Character → Build identity, matches only
explicit action names, retains every scheduled matching cast, and renders missing
plans, progression, contributors, or actions as candidate blockers. Reference and
ESO Logs candidates do not silently become saved-build rotation evidence.

Persistent/summoned Ultimates with an explicit secondary activation contract now
reuse the existing canonical ability-description resolver. For example, a zero-base-
cost Eternal Guardian can contribute the evidenced 75-Ultimate Guardian's Wrath
activation cost; unsupported zero-cost Ultimates remain unresolved.

Expanded canonical provider-workload, coverage, explanation, presentation, final-
cost, saved-slot, timing, and Ultimate checkpoint: **122 passed, 1 skipped in 1.07s**.
The single local skip is the real PySide widget check because PySide6 is unavailable
in the Linux scratch runtime; the source-level dual-surface/install checks passed and
the widget test remains included for the user's Windows environment.
Latest user-reported full-suite checkpoint after the canonical workload slice:
**2,626 passed in 73.30s** on Windows / Python 3.12.4.
Candidate-generation focused checkpoint: **98 passed, 1 skipped in 0.69s**. The
skip remains the PySide6 widget check in the Linux scratch runtime.

Active next work:

1. convert the user-supplied BTV screenshot corpus into structured benchmark fixtures with provenance, encounter scope, observed uptime, target/reference uptime where visible, theoretical maximum where visible, and explicit unknown fields rather than guessed values;
2. test policy selection, target-vs-theoretical-max validation, temporal window scoring, overlap/gap explanation, and BTV-style feedback against those fixtures;
3. connect those benchmark fixtures to Comp Maker / Optimization explanation paths without treating them as canonical ESO mechanics;
4. feed encounter/provider assignment policies and the growing set of saved team rotation plans into the new Comp Maker / Optimization candidate-generation seam;
5. continue thorough healer, tank, and DD rotation coverage with class passives, armor/set duration modifiers, runtime proc conditions, and encounter-specific timing.

Fight-horizon policy: most raid fights are expected to finish within roughly six minutes in the user's working context, so **360 seconds may be used only as an overrideable fallback planning ceiling when encounter-specific timing is unavailable**. It is not a canonical encounter duration. Optimization should prioritize important burn/mechanic windows over meaningless attempts to force every support effect to 100% global uptime.

### Phase 13 / current Phase 13.5 closeout structural audit

**Closeout result (2026-09-17): COMPLETE.** The detailed ledger and architecture
audit have dispositions for every material finding, the architecture closeout gate has
zero blockers, and the full repository checkpoint is **3026 passed in 46.93s**. The
remaining UI class-patch and service-catalog candidate lists are explicit migration
inventories, not undispositioned correctness findings.

Before the current Phase 13 line is considered ready to close, and before Phase 14 begins building on top of it, perform a deliberate repository-wide structural audit. This is a stabilization gate, not a feature-expansion pass.

The audit must cover:

- **dead and obsolete code:** identify unreachable services, unused helpers, stale imports, abandoned flags, superseded adapters, and compatibility paths that no longer have a supported caller;
- **duplicate or competing authority:** find multiple services, repositories, factories, registries, dictionaries, or UI paths that claim ownership of the same concept and resolve them to one authoritative implementation where appropriate;
- **semantic conflicts:** trace important ESO concepts across the codebase to catch two active implementations that encode different rules even when both are individually tested. Priority examples include penetration, buff/debuff duration, periodic classification, execute scaling, potion effects, resource costs, proc timing, bar ownership, healing modifiers, and target/recipient semantics;
- **architecture drift:** identify code that works but bypasses canonical Character → Build → Team identity, canonical effect/runtime services, repositories, source/provenance boundaries, or other rules defined by the architecture documents;
- **stale tests and shims:** remove or rewrite tests that protect obsolete behavior, and review temporary wrappers, feature flags, migration shims, compatibility aliases, and fallback paths to determine whether they are still intentionally required;
- **dependency and configuration cruft:** review unused dependencies, duplicated configuration, stale data files, logging/debug leftovers, exception-swallowing fallbacks, and documentation that no longer describes the actual authoritative path;
- **recorded disposition:** every material finding must be fixed, explicitly retained with a reason, or recorded as a countable deferred item with an owner/phase boundary. Unknown or conflicting behavior may not be cleaned up by silently choosing whichever implementation is convenient;
- **post-cleanup validation:** rerun the affected focused suites and an appropriate full regression checkpoint after removals or consolidations so cleanup cannot become an untested behavior change.

The purpose is not to minimize line count. The purpose is to prove that the architecture BFF intends to carry into simulation has one coherent set of authorities and that historical implementation layers are not quietly contradicting the canonical engine.

**Prerequisite / integration gate:** Phase 12.5 must be green before Phase 13 is closed. Rotation evaluation must consume the canonical Character → Build → Team assignment path rather than introducing another page-specific build/team identity model.

**Hardened exit criteria:** BFF can produce and evaluate a realistic damage, support, or healing rotation from verified skill behavior and resource constraints; action timing is deterministic from identical inputs; class passives and build-derived effect-duration modifiers are respected; provider recipient and temporal obligations can be represented where relevant; unsupported mechanics remain explicit; at least one real build is validated end-to-end; the Phase 13 structural audit above is completed with findings dispositioned; focused and appropriate regression gates pass.

---

# PHASE 14 · Combat Simulation
**Status: 🟡 Active**

The `phase14` branch was opened from the completed Phase 13.5 release baseline on
2026-09-17. Phase 12.5 is now closed and the first Combat Simulation implementation
slice is active.

### Phase 14A — deterministic simulation kernel

The first kernel consumes the authoritative Phase 13 `RotationPlan` directly rather
than creating a second action model. It currently:

- requires an immutable `EffectiveBuildSnapshot`;
- fails closed when Rotation character/build identity does not match the frozen Build;
- reuses `RotationActiveBarAssessor` for canonical bar progression and legality;
- emits an ordered immutable simulation event stream;
- preserves same-timestamp `(time, sequence)` order;
- exposes deterministic replay equality/signature;
- records unsupported skill/light/heavy/ultimate/potion/block/dodge consequences as
  explicit unresolved evidence instead of treating them as zero;
- treats WAIT and BAR_SWAP as orchestration actions whose kernel consequences are
  already understood.

Initial real-role control is a short healer sequence using Combat Prayer, light attack,
bar swap, and Illustrious Healing. Resource, healing, damage, and proc consequences are
the next wiring slices and remain owned by their existing canonical engines.

### Phase 14A validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **15 passed in 2.08s**
- deterministic replay, same-timestamp ordering, build/rotation identity, bar legality,
  and runtime-state integration tests are green.

**Phase 14A kernel status: green.**

### Phase 14B — healer resource execution

The simulation kernel now projects **Magicka** through the existing
`RotationSustainService` / Phase 4 resource timeline instead of adding a second
resource calculator.

Implemented:

- supported named healer skills resolve through canonical ability-cost data;
- verified build cost modifiers remain owned by the Phase 4 sustain path;
- ordinary recovery ticks retain Phase 4 cadence and ordering;
- resource timeline events are merged into the Phase 14 event stream with explicit
  simulation priorities;
- before/attempted/applied/after, shortfall, and wasted-restore evidence is preserved;
- resource starting/ending amounts are part of the immutable simulation result;
- unsupported or incomplete resource evidence remains unresolved;
- wiring a skill cost does **not** imply its healing/damage/effect outcome is modeled:
  non-resource skill consequences remain explicitly unresolved.

Initial scope is Magicka for the healer control. Stamina/Health primary-resource
projection and Ultimate economy remain later resource slices rather than being guessed.

### Phase 14B validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **23 passed in 3.04s**
- resource adapter, simulation kernel, Rotation sustain, named-build sustain, and
  Phase 4 build sustain tests are green.

**Phase 14B healer Magicka/resource slice status: green.**

### Phase 14C — healer output bridge

The simulation kernel now consumes the existing canonical healer action-output path
rather than introducing new healing formulas.

Implemented:

- `RotationHealerActionHealingService` remains authoritative for component identity
  and modeled healing magnitude;
- canonical static front/back build contexts are resolved through
  `RotationStaticBuildContextService`;
- verified direct healing becomes `direct_heal` simulation events;
- periodic, delayed, and channel components become explicit typed simulation seeds
  carrying their canonically resolved magnitude;
- unresolved build context or component evidence fails closed;
- periodic magnitude does **not** imply tick timing: exact tick events remain
  unresolved until reviewed runtime timing evidence supplies first-tick/expiry/recast
  behavior;
- healer output events merge into the same deterministic Phase 14 event stream;
- healing resolution does not imply damage, buff/debuff, or proc consequences.

Initial control behavior: Combat Prayer can emit a real direct-heal event. Illustrious
Healing can emit a canonical periodic-heal seed, while exact tick placement remains
explicitly unresolved instead of being guessed.

### Phase 14C validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **45 passed in 4.92s**
- healer output bridge, resource bridge, simulation kernel, canonical healer action
  projection, periodic runtime, and Rotation sustain suites are green.

**Phase 14C healer output slice status: green.**

### Phase 14D — reviewed periodic healer timing

The simulation healer bridge now expands periodic-heal seeds into concrete heal events
only when reviewed runtime timing evidence is available.

Implemented:

- canonical periodic component cadence/duration remains owned by
  `RotationHealerCanonicalPeriodicTimingService`;
- first-tick, expiry-boundary, and repeated-application refresh behavior remain owned
  by reviewed runtime observations and `RotationHealerPeriodicRuntimeEvidenceService`;
- `RotationHealerPeriodicRuntimeService` schedules exact periodic heal events from
  that evidence;
- Phase 14 preserves the original `periodic_heal_seed` event as cast/source
  provenance and emits additional `periodic_heal` events for reviewed ticks;
- missing reviewed timing leaves the seed visible and exact ticks unresolved;
- explicit reviewed timing fixtures can be loaded through
  `RotationHealerReviewedRuntimeEvidenceLoader`, with optional reviewed refresh-policy
  composition;
- candidate evidence is not auto-promoted and no fixture path is guessed implicitly;
- explicit observation injection and fixture-backed evidence are mutually exclusive
  to prevent ambiguous runtime authority.

Illustrious Healing is the first control. Reviewed timing can expand the cast-resolved
periodic magnitude into deterministic tick events clipped to the simulation horizon.

### Phase 14D validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **63 passed in 13.48s**
- Phase 14 healer simulation, reviewed timing evidence, runtime tick scheduling,
  observation-fixture loading, and refresh-policy composition suites are green.

**Phase 14D reviewed periodic healer timing status: green.**

### Phase 14E — reviewed healer skill effects

The simulation kernel now consumes reviewed cast-time skill effects through the existing
skill-effect and runtime-window architecture.

Implemented:

- `SkillEffectRepository` remains authoritative for imported + reviewed supplemental
  skill effects;
- Phase 14 projects bounded unconditional CAST effects into deterministic
  `effect_apply` / `effect_expire` events;
- `RuntimeEffectActiveWindow` remains the canonical bounded-window contract;
- `apply_runtime_effect_window_stacking` remains authoritative for UNIQUE/STACKS/
  HIGHEST_ONLY behavior;
- repeated UNIQUE applications refresh by truncating the previous overlapping window
  and starting a new canonical window;
- unresolved conditions, target scope, duration, or stacking fail closed instead of
  being guessed;
- triggered effects remain owned by the Phase 7 runtime path and are not treated as
  unconditional cast effects;
- group-target effects preserve `target_scope=group` without fabricating exact
  recipients.

First control: Combat Prayer's reviewed supplemental **Minor Resolve** effect
(2974 resistance, 10 seconds, GROUP, UNIQUE) becomes a timed simulation window.
Exact group-recipient membership remains a later target/encounter-state responsibility.

### Phase 14E validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **39 passed in 5.37s**
- reviewed skill-effect projection, healer-output/resource/kernel integration, runtime
  windows, runtime stacking, and verified known-effect support tests are green.

**Phase 14E reviewed healer skill-effect status: green.**

### Phase 14F — exact-time simulation snapshots

The deterministic simulation result now preserves canonical effect windows and can be
projected into an exact-time read model without re-running ESO calculations.

Implemented:

- `CombatSimulationResult` carries canonical runtime effect windows alongside the
  ordered event stream and resource summaries;
- `CombatSimulationSnapshotService` projects the active bar at an exact instant from
  the already-ordered BAR_SWAP history;
- current resource amounts come from the canonical Phase 4-derived resource events,
  not from a second resource formula;
- active timed effects are selected through
  `partition_runtime_effect_windows`, preserving Phase 7 window semantics;
- unresolved simulation boundaries propagate into every snapshot;
- snapshot times outside the deterministic simulation horizon fail closed.

This is intentionally a Phase 14 orchestration/read model rather than a replacement for
the richer Phase 8 `CombatStateSnapshot`. Target health/status/recipient state will be
bridged when supported target behavior enters the simulator.

### Phase 14F validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **41 passed in 12.03s**
- exact-time snapshots, reviewed skill effects, healer output, resource projection,
  main simulation ordering, runtime windows, and stacking suites are green.

**Phase 14F exact-time simulation snapshot status: green.**

### Phase 14G — explicit combatants and recipient binding

Phase 14 now carries an explicit combatant map and event-scoped recipient bindings
through the deterministic simulation result and exact-time snapshots.

Implemented:

- `CombatSimulationCombatant` identifies known SELF / ALLY / ENEMY combatants;
- `CombatSimulationRecipientBinding` binds one exact simulation consequence to an
  explicit recipient set using time, sequence, event type, source, and optional
  coefficient/effect identity;
- `CombatSimulationTargetState` carries combatants + bindings and rejects duplicate
  combatant or duplicate binding identities;
- `CombatSimulationTargetBindingService` attaches recipients only to
  `direct_heal`, `periodic_heal`, and `effect_apply` events;
- missing target state or missing event binding preserves the original event and
  reports an explicit unresolved recipient boundary;
- unknown recipients or ally/enemy/self scope conflicts fail closed;
- `CombatSimulationService.simulate(..., target_state=...)` carries this state through
  deterministic replay;
- `CombatSimulationSnapshotService` preserves the same target state at exact-time
  snapshots;
- no geometry, cone coverage, ground-area membership, encounter positioning, or ESO
  target-selection algorithm is inferred.

Combat Prayer is the first control: its direct heal and Minor Resolve application can
now be bound to known allies when exact recipient evidence is supplied. Without that
evidence, recipient identity remains unresolved rather than becoming “the group.”

### Phase 14G validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **28 passed in 5.84s**
- explicit recipient binding, target-state preservation, snapshots, healer output,
  reviewed skill effects, resources, and main simulation integration are green.

**Phase 14G explicit recipient binding status: green.**

### Phase 14H — recipient-aware Health state

Phase 14 now projects explicit recipient-bound healing into deterministic Health changes.

Implemented:

- `CombatSimulationCombatant` may carry explicit current and maximum Health;
- `CombatSimulationHealthService` consumes only explicitly bound
  `direct_heal` / `periodic_heal` events;
- each applied heal records before, attempted heal, applied heal, overheal, after, and
  maximum Health;
- sequential heals consume the prior projected Health state in deterministic order;
- Health is capped at the explicit maximum and overheal remains visible rather than
  being discarded;
- missing current/maximum Health fails closed and does not imply effective healing;
- `CombatSimulationService` preserves the original heal event and adds auditable
  `health_change` consequence events;
- `CombatSimulationSnapshotService` projects exact combatant Health at the queried
  simulation instant from those already-computed changes.

This remains healing-only state mutation. Incoming damage, deaths, shields, resurrection,
and encounter-target behavior are not inferred by this slice.

### Phase 14H validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **33 passed in 11.84s**
- recipient-aware Health projection, recipient binding, snapshots, healer output,
  reviewed skill effects, resource projection, and main simulation integration are green.

**Phase 14H recipient-aware Health state status: green.**

### Phase 14I — explicit incoming damage and Health loss

Phase 14 now accepts explicit post-mitigation incoming-damage events and projects them
into deterministic Health loss for known combatants.

Implemented:

- `CombatSimulationIncomingDamage` supplies exact time, sequence, source, recipient,
  resolved damage amount, and optional damage type;
- the main simulation queues `incoming_damage` alongside actions and other
  consequences;
- `CombatSimulationHealthService` applies incoming damage and recipient-bound healing
  in one ordered Health timeline;
- damage records before, attempted damage, applied damage, overkill, after, and maximum
  Health;
- Health bottoms at zero and overkill remains auditable;
- later heals consume the Health state produced by earlier damage events;
- exact-time snapshots project Health after incoming damage from already-computed
  `health_change` events;
- missing combatant or Health state fails closed.

Boundary: incoming damage is explicitly **post-mitigation/resolved**. This slice does not
infer armor/resistance mitigation, blocking, shields, dodge, damage type modifiers, or
encounter mechanic values. Those must be connected through their canonical engines or
reviewed encounter evidence later.

### Phase 14I validation checkpoint — 2026-09-19

User-reported focused checkpoint:

- **39 passed in 7.30s**
- incoming-damage Health projection, target binding, snapshots, healer output,
  reviewed effects, resource projection, and main simulation integration are green.

**Phase 14I incoming damage Health state status: green.**

### Phase 14J — explicit death state

Phase 14 now turns deterministic Health depletion into an explicit death-state
transition.

Implemented:

- when a known combatant moves from Health > 0 to Health = 0, the simulation emits
  one deterministic `death` event after the causal `health_change`;
- nonlethal damage emits no death transition;
- exact-time Health snapshots expose `is_dead`;
- healing a combatant already at zero Health does not silently resurrect them and
  instead reports resurrection semantics as unresolved;
- death remains derived from explicit Health state only.

This slice does **not** model resurrection, soul gems, revive channel timing, encounter
wipe logic, corpse targetability, death-triggered set behavior, or encounter-specific
failure conditions.

### Phase 14J validation checkpoint — 2026-09-21

Focused validation:

- **87 passed in 2.56s**
- explicit death transitions, Health/damage/healing projection, exact-time snapshots,
  recipient/target binding, outgoing damage, and main simulation integration are green;
- lethal damage emits one causal death transition after the Health change;
- nonlethal damage emits no death transition;
- dead recipients remain dead until explicit resurrection semantics exist;
- snapshots expose deterministic `is_dead` state without inventing revive behavior.

**Phase 14J explicit death state status: green.**

### Phase 14 closeout checkpoint — 2026-09-20

Dedicated closeout validation:

- **201 passed in 12.77s** across the focused Combat Simulation gate;
- deterministic event ordering, canonical replay signatures, and exact-time snapshot
  projection are green;
- canonical resource, healing, reviewed skill-effect, recipient-binding, and DD damage
  paths are integrated through the main simulation;
- result-level resource summaries must reconcile with event continuity, shortfall,
  restore-waste, and same-time resource-maximum ordering evidence;
- Health transitions must reconcile before/after state, attempted/applied damage or
  healing, overkill/overheal, lethal attribution, and no-resurrection semantics;
- Damage Summary preserves proven partial totals but withholds modeled DPS whenever
  damage-relevant evidence is incomplete, while keeping unrelated unresolved evidence
  separate;
- Health, incoming/outgoing damage, death state, exact-time snapshots, fight termination,
  saved-build DD simulation, sequential target-Health feedback, and occurrence-level
  periodic damage are included in the closeout gate;
- canonical Combat Simulation kernel, saved-build DD bridge, Damage Summary, deterministic
  replay, and snapshot responsibilities are registered in the service catalog so no
  parallel authority is implied by discovery metadata;
- unsupported mechanics remain explicit unresolved evidence rather than silently
  improving modeled outcomes;
- real saved-build DD end-to-end audit remains data-gated when no actual saved DD/DPS
  build exists; audit completion must not fabricate one.

**Phase 14 Combat Simulation status: COMPLETE / GREEN.**

**Comp Maker / Optimizer ownership update (2026-09-19):** Assignments owns WHO
is responsible for required buffs/debuffs. Comp Maker owns roster construction plus HOW
those assigned chairs will supply their jobs: compatible class/build/gear/skill/provider
choices, missing-provider detection, duplicate-provider visibility, and preservation of
fixed player/class/role/gear decisions. Comp Maker must not invent new responsibility
ownership from generic coverage gaps. Optimizer starts from the completed saved Raid Plan
and proposes better provider arrangements, opportunity-cost reductions, and coverage
improvements without silently rebuilding the roster or transferring responsibility.

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

### Parked Live Raid integration — encounter intelligence

Route the canonical **boss encounter information and encounter timelines** into the
**Live Raid** workspace wherever that information is useful during an active run.

Target behavior:

- Live Raid consumes the active Raid Plan's selected trial / encounter context rather
  than maintaining a separate boss-data selection or duplicate encounter model.
- Surface concise boss/phase information, mechanic timing, phase transitions, add or
  priority windows, and other reviewed encounter timeline facts on the Live Raid page
  where they help raid-leading decisions.
- Reuse the existing canonical encounter/timeline services and any reviewed
  position/timeline data rather than copying encounter prose into Live Raid.
- Keep the display contextual: show information appropriate to the selected boss and,
  when an explicit current phase is available, the relevant phase/window rather than
  dumping an entire guide into the run surface.
- Live Raid remains a **consumer**, not an encounter editor. Strategy/mechanic edits
  continue to belong to their owning planning/reference surfaces.
- Do not infer live telemetry, boss health, elapsed phase, or current mechanic from the
  mere existence of a timeline. Automatic "what is happening now" behavior requires a
  real/manual runtime clock or another explicit live-state source.
- Preserve unresolved/conflicting encounter evidence as unresolved rather than turning
  it into a confident live callout.
- Prefer compact, raid-lead-readable presentation with the detailed boss/encounter
  pages remaining available for deeper reference.

### Live Raid encounter-intelligence validation checkpoint — 2026-09-21

Implemented and validated:

- Live Raid consumes the selected Raid Plan trial and explicit encounter selection;
- canonical boss-guide and reviewed encounter-evidence services supply phase guides,
  callouts, checklists, threshold conditions, and reviewed wall-clock timeline facts;
- **Next 60 Seconds** is driven only by reviewed persisted clock facts plus the manual
  pull timer;
- health/phase thresholds remain threshold guidance and are never converted into guessed
  timestamps;
- Live Raid remains a consumer of encounter truth and labels guide/reference state
  separately from unavailable observed telemetry;
- focused encounter-context validation: **7 passed in 0.46s**.

**Status: COMPLETE / VALIDATED.** The parked integration is closed without duplicating
encounter authority or claiming unsupported live telemetry.

---

# PHASE 15 · Encounter-Aware Optimization
**Status: 🔴 Planned**

Compare builds across DPS, burst, sustained damage, execute, uptime, sustain, survivability, positioning, mechanic compliance, support contribution, phase compression, and execution complexity.

**Prerequisite gate:** Phases 9 and 10 must be green under the hardened completion standard. Encounter-aware optimization may not consume partially reviewed encounter truth as if it were complete. Phase 12.5 may expose bounded static comparison groundwork, but temporal or encounter-outcome claims require the later rotation/simulation dependencies they actually use.

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
