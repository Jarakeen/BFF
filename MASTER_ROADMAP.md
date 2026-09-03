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

# PHASE 0 · Data Foundation
**Status: 🟢 Complete**

Database-backed ESO information exists for skills, morphs, skill ranks, coefficients, gear, set effects, encounter imports, UESP encounter data, repositories, and data services.

**Exit criteria:** BFF has a reliable database-backed source for ESO information.

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

A character may have many builds. The same saved Character → Build must ultimately be selectable everywhere, including Optimization, Raid Planning, Encounter Analysis, and Log Analysis. No rebuilding the same person five times because software apparently developed paperwork envy.

## Completed canonical persistence foundation

- 🟢 stable canonical character identity separate from build identity
- 🟢 same account + same character can own many builds without duplication
- 🟢 different characters on the same account remain distinct
- 🟢 existing `character_id` survives legacy roster resync
- 🟢 stable build IDs preserved through canonical build persistence
- 🟢 blank/template legacy rows do not become authoritative canonical builds
- 🟢 character-scoped `owned_skill_lines` persist independently of build payloads
- 🟢 canonical catalog schema v3 adds character-scoped `passive_ranks`
- 🟢 passive-rank updates are case-insensitive, normalized, and removable by rank 0
- 🟢 character progression survives legacy build resync and does not mutate individual build payloads
- 🟢 `Medicinal Use` can now be resolved from canonical character progression into potion cadence

## Remaining Phase 1 adoption work

- expose character-owned progression in the Builds/character UI
- make passive ranks and owned skill lines editable without requiring direct JSON manipulation
- make saved Character → Build selection authoritative across downstream pages
- migrate remaining page-specific identity/build reconstruction onto the canonical catalog

**Exit criteria:** a real character can have reusable database-backed builds and character-owned progression that downstream systems consume directly.

---

# PHASE 2 · Effect Architecture
**Status: 🟡 Advanced foundation**

The existing EffectVariant / effect-resolution architecture remains authoritative for effect identity, category, magnitude, duration, chance, cooldown, trigger, target, conditions, and stacking.

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

The architecture now also includes a dedicated `CONSUMABLE` effect layer. A selected potion represents **available capability**, not standing uptime. Temporal activation is projected explicitly later.

**Remaining:** broaden real-build effect detection and character-owned passive coverage while keeping conditional effects out of standing state.

**Exit criteria:** a real build exposes the effects it actually provides, with unresolved/conditional behavior explicit.

---

# PHASE 3 · Static Combat Rules Engine
**Status: 🟢 Complete**

Phase 3 establishes one explainable static combat calculation with separate modifier stages rather than one giant multiplier bucket.

## Authoritative static damage path

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

## Completed Phase 3 foundations

### Shared character / healer / tank math
- 🟢 standing primary/derived stat pipeline retained and audited
- 🟢 Critical Healing represented separately
- 🟢 Block Cost first-class calculator
- 🟢 Block Mitigation first-class calculator
- 🟢 ranged/projectile block-family routing for Deflect Bolts
- 🟢 named CombatState buffs for major/minor offensive, defensive, recovery, healing, vulnerability/protection families

### Damage routing
- 🟢 Damage Done routed by generic, type, Direct/DoT, AoE/single-target categories
- 🟢 Damage Taken kept target-side and later than mitigation
- 🟢 Protection/Vulnerability do not leak into attacker stats
- 🟢 target Critical Resistance modeled separately from armor resistance
- 🟢 CP160+ Critical Resistance conversion: 66 rating removes 1 percentage point of crit bonus, floor at zero

### Skill coefficients
- 🟢 type-8 formula unified: `A * MaxStat + B * Power + C`
- 🟢 UESP `r` retained as regression-fit metadata and never multiplied into game value
- 🟢 only the exact UESP `-1/-1/-1/-1` coefficient sentinel is inactive
- 🟢 valid negative coefficients are preserved
- 🟢 duplicate legacy coefficient path reconciled with the verified Phase 3 implementation

### Per-component semantics
- 🟢 canonical key: `skill_rank_id + coefficient_number`
- 🟢 effect kind: damage / heal / shield / utility / unknown
- 🟢 damage type, periodicity, target shape and crit eligibility stored independently
- 🟢 normal skill damage and healing are crit-eligible by default
- 🟢 shield / utility crit eligibility is not applicable (`NULL`)
- 🟢 proc/set crit eligibility lives in a separate policy layer
- 🟢 current proc policy foundation:
  - offensive-stat-scaled proc → crit eligible
  - Max-Health-scaled proc → cannot crit
  - Oblivion damage → cannot crit
  - escalating/modifier-style proc → cannot crit
  - unresolved/flat proc → remains unknown until proven

### Component database coverage
- Active coefficient rows audited: **3,208**
- Persisted qualified classifications: **2,376**
- Intentionally unresolved active rows: **824**
- Missing fragments: **8**
- Slot mismatches: **0**

The unresolved rows are not a Phase 3 blocker. They remain explicit rather than being guessed from names or vague tooltip text.

### Tooltip / healing validation
Combat Prayer was used as a real saved-build downstream validation case.

- observed tooltip: **9436**
- closest auditable modeled scenario: **9444.014264**
- residual: **8.014264 points ≈ 0.085%**

This residual is accepted for Phase 3. It is small enough to plausibly reflect hidden precision, tooltip rounding, exact live state, or saved-build drift. The formula will **not** be altered with an unexplained correction factor merely to force an exact historical match.

### Final closeout evidence
- 🟢 real `eso.db` classified component traversed the full static pipeline successfully
- 🟢 audited sample: Corrosive Armor, ability `17878`, skill rank `4400`, coefficient `#1`
- 🟢 full suite after closeout: **1305 passed**

## Phase 3 non-goals / deferred work
- exhaustive resolution of all 824 ambiguous components
- full proc/set temporal engine
- sustain-over-time simulation
- rotation engine
- encounter simulation
- ESO Logs as a canonical skill-math dependency
- exact integer tooltip reproduction for every ESO ability

Runtime/log observations may be used later as validation/corroboration, not as the normal source of static skill semantics.

## Phase 3 exit criteria
- one authoritative static combat calculation
- no competing coefficient formulas
- modifier stages remain separated and explainable
- unresolved evidence remains explicit
- real classified database component traverses the complete static damage path
- full test suite green

**Exit criteria met on 2026-08-31.**

---

# PHASE 4 · Resource & Sustain Engine
**Status: 🟢 Complete**

Phase 4 models resource state, verified ability costs, ordinary recovery timing, temporary recovery modifiers, explicit restoration events, deterministic resource timelines, and sustain failure/margin interpretation.

```text
Saved Build
   ↓
Static Resource State
   ↓
Named Ability → Base Cost
   ↓
Verified Build Cost Modifiers
   ↓
Action Cost Events
   ↓
Recovery Ticks / Suppression
   ↓
Timed Recovery Modifiers
   ↓
Explicit Restoration Events
   ↓
Deterministic Timeline
   ↓
Sustain Result
```

## Completed Phase 4 foundations

- 🟢 static Health/Magicka/Stamina resource pools reuse the audited character-sheet state
- 🟢 canonical ability `base_cost` and `base_mechanic` resolution
- 🟢 compound resource costs remain independent per resource
- 🟢 verified flat-before-percentage action-cost ordering
- 🟢 nearest-half-up final action-cost rounding
- 🟢 Breton Magicka Mastery and verified armor cost-passive behavior
- 🟢 CP160 jewelry cost glyph integration
- 🟢 2-second ordinary in-combat recovery cadence
- 🟢 explicit Stamina suppression while blocking, sprinting, or sneaking
- 🟢 Warden Flourish remains upstream in standing character-sheet recovery
- 🟢 timed additive recovery modifiers such as Enlivening Overflow
- 🟢 explicit flat restoration events with cap/waste accounting
- 🟢 heavy-attack restoration contract with verified modifier ordering and caller-supplied verified base
- 🟢 Restoration Staff Absorb and Warden Nature's Gift event foundations
- 🟢 deterministic same-timestamp ordering: cost → recovery tick → restoration event
- 🟢 first-failure, shortfall, minimum resource, ending margin, total-cost, and wasted-restore diagnostics
- 🟢 saved skill name → canonical rank → ability cost → saved-build modifier → timeline bridge
- 🟢 deterministic saved-bar audit planner for real-build integration testing

### Real saved-build validation

Phase 4 was validated end-to-end against **Magrat → DF Healer** using the current local `eso.db` / saved build data.

Audit snapshot:

- Warden / Breton
- front bar
- Magicka
- 20-second deterministic integration window
- Max Magicka: **31,629**
- Magicka Recovery: **2,533 per ordinary recovery tick**
- resolved saved-skill Magicka costs:
  - Budding Seeds: **1,993**
  - Race Against Time: **3,100**
  - Combat Prayer: **3,764**
  - Illustrious Healing: **2,878**
  - Energy Orb: **3,100**

The synthetic one-cast-per-second audit does not claim to be a real healer rotation. It deliberately stress-tests the pipeline. In that modeled sequence, first failure occurred at **18.0s Combat Prayer**, with **2,295** Magicka available against a **3,764** cost, producing a **1,469** shortfall.

The audit explicitly separates ordinary recovery from explicit restores and states that it does not automatically schedule heavy attacks, potion resource events, conditional recovery windows, or triggered restore procs.

### Explicit Phase 4 boundaries

The following were deferred from Phase 4 rather than guessed:

- unverified percentage cost-increase ordering
- unmeasured Light Armor Evocation piece counts
- exact current heavy-attack base restore values where live precision is insufficient
- automatic heavy-attack scheduling
- actual conditional-proc trigger/cooldown scheduling
- Enlivening Overflow / Nature's Gift / Absorb trigger timing from combat events
- exceptional recovery suppression/remapping such as Stormweaver's Cavort
- dynamic/unmapped Champion Point behavior

Two important Phase 4 deferrals have since advanced in Phase 5:

- 🟢 potion resource-use events and timed potion effects now have an explicit source-backed temporal foundation
- 🟢 canonical character-level skill-line ownership and passive-rank persistence now exist

These later improvements do not change the historical Phase 4 closeout boundary; they extend the engine in the intended later phases.

### Final closeout evidence

- 🟢 real saved build traversed the complete Phase 4 pipeline
- 🟢 build-relevant unresolved mechanics remain explicit
- 🟢 full regression suite at closeout: **1,444 passed**

**Exit criteria met on 2026-08-31.**

---

# PHASE 5 · Real Build Resolution
**Status: 🟢 Complete**

Phase 5 proves the actual ESO database → canonical character/build → resolver → `EffectVariant` / capability path across authoritative saved builds while keeping temporal and conditional mechanics explicit.

```text
REAL DB
 ↓
Skill / Morph / Gear / Consumable
 ↓
EffectVariant
 ↓
Repositories
 ↓
Saved Build + Canonical Character
 ↓
Build / Capability Resolver
 ↓
Explicit Boundaries for Deferred Temporal Mechanics
 ↓
Auditable Coverage
```

## Completed Phase 5 foundations

- 🟢 stable canonical character/build identity and character-owned progression
- 🟢 progression UI for owned skill lines, passive ranks, and passive Champion Points
- 🟢 canonical potion/effect-family picker with legacy-label compatibility
- 🟢 source-backed U50 Alchemy corpus and Potion/Poison EffectVariants
- 🟢 explicit potion-use events, active windows, cooldown, and Medicinal Use cadence
- 🟢 U50/U51 version-aware combat semantics and migration boundaries
- 🟢 exact purchased racial passive rank resolution from canonical `skill_rank` + `ability` data
- 🟢 aggregate race-stat shortcut removed from the Phase 5 canonical path
- 🟢 saved-build capability service defaults to the Phase 5 canonical context
- 🟢 active-bar gear set counting, including two-handed weapon set-slot semantics
- 🟢 real skill, gear, mythic, consumable, buff/debuff, and conditional-effect capability reporting through `EffectVariant`
- 🟢 standing availability kept separate from explicit activation/uptime
- 🟢 dynamic/non-combat Champion Points classified as explicit deferred boundaries instead of false unresolved failures
- 🟢 known template/sample builds excluded from authoritative closeout totals while remaining available for stress testing
- 🟢 broader real-build resolution matrix with explicit boundary and unresolved reporting

## Closeout evidence

Authoritative saved build: **Magrat → DF Healer**

- canonical character ID resolved
- canonical character progression resolved
- racial passives resolved from exact purchased ranks
- Spaulder of Ruin, Serpent's Disdain, Master Architect, Combat Prayer, Expansive Frost Cloak, Overflowing Altar, Aggressive Horn, and selected potion capability resolved through the production path
- **11 unique resolved EffectVariants** in the closeout sample
- **0 genuine unresolved items**

Authoritative roster closeout:

- `DF Healer`: **0 genuine unresolved**
- `YOUR TANK BUILD`: retained as a diagnostic/template sample and excluded from authoritative closeout totals
- **TOTAL GENUINE UNRESOLVED: 0**

Regression checkpoint:

- 🟢 template classifier tests green
- 🟢 full regression suite: **1,619 passed** on **2026-09-01**

## Explicit Phase 5 deferrals

The following remain intentionally outside Phase 5 rather than being guessed:

- automatic proc/cooldown scheduling
- status-effect chance models, including Charged and related CP behavior
- typed/attacker-specific incoming-damage mitigation
- attack-damage-type conditional offensive modifiers
- movement-speed and movement-state behavior
- Bash / Break Free / Sprint / Roll Dodge utility-cost channels
- incoming status-effect duration and resurrection-state mechanics
- stealth-detection/PvP utility
- conditional racial bonuses that require live combat state
- general ability-cost channels not represented in standing stat state
- U51 temporal Alchemy tier values until authoritative source data exists

These move forward to Phase 6 where they are component semantics, or to Phase 7/8 where they require conditional/temporal state.

**Exit criteria met on 2026-09-01.**

Detailed closeout: `docs/phase5_real_build_resolution_closeout.md`.

---

# PHASE 6 · Damage / Effect Components
**Status: 🟢 Complete**

Phase 6 makes coefficient-local ability semantics explicit without turning runtime combat state into static facts. It bridges per-component identity into the existing effect architecture and records static relationships that Phase 7 can execute over time.

## Completed Phase 6 foundations

- 🟢 explicit component → named-effect applications, including status effects and named buffs/debuffs
- 🟢 target-health and self-health threshold conditions with coefficient ownership
- 🟢 conditional consequences such as component activation and execute-style damage amplification
- 🟢 damage-linked secondary healing and missing-health healing
- 🟢 shield parsing with neighbor ownership kept conservative
- 🟢 resource restoration semantics, including coefficient, percent-missing, percent-resource, and current-display rules
- 🟢 utility effects including stun, immobilize, movement changes, knockback, pull, taunt, and interrupt immunity
- 🟢 dynamic damage scaling such as accumulated-damage caps and per-tick increments
- 🟢 dynamic stat scaling such as Elder Dragon missing-health recovery
- 🟢 explicit secondary component roles for additional damage and healing
- 🟢 component trigger relationships for attacks, effect completion, stun completion, damage events, enemy death, delay completion, and charge thresholds
- 🟢 current-stat bonus display semantics for armor-piece and slotted-ability passives
- 🟢 resource-restore display semantics for Constitution and Undaunted Command
- 🟢 coordinated damage-list parsing for Pestilent Colossus-style `$1/$2/$3` shared damage-type prose
- 🟢 source-mapped passive stat rules for Twin Blade and Blunt and Death Knell
- 🟢 explicit unsupported source-alignment representation instead of guessed mechanics

## Phase 6 boundary discipline

Phase 6 records **what the component means and what static relationship exists**. It deliberately does not execute runtime timing/state.

Deferred to Phase 7/8:

- trigger occurrence and event detection
- durations and active windows
- tick cadence and repeated-event scheduling
- proc chance and cooldown enforcement
- stack accumulation / expiration
- target selection and target-count changes over time
- current execute/health conditions
- status-effect runtime application behavior
- proc-set and enchantment scheduling
- combat-state truth at a specific instant

## Closeout evidence

Final Phase 6 closeout gate on **2026-09-02**:

- residual audit rows: **403**
- needs Phase 6 review: **0**
- parser-coverage rows: **0**
- source-evidence blocked: **4**
- unsupported source alignment: **4**
- unresolved source blocks: **0**
- classification cleanup: **356**
- ownership negatives: **8**
- Phase 7 boundaries: **35**
- **RESULT: PASS**

Targeted final regression checkpoint: **14 passed**.

### Explicit retained source limitation

Four Engulfing Dragonfire coefficient-3 rows use UESP special coefficient type `-73`. The normalized/raw coefficient slot is real, but UESP's raw placeholder numbering maps `<<3>>` to channel-duration prose while the coefficientized display does not expose `$3` as a trustworthy mechanic. BFF therefore records these rows as **unsupported source alignment** and does not invent a semantic mapping.

This is an intentional supported limitation, not an unresolved Phase 6 blocker.

**Exit criteria met on 2026-09-02.** BFF can explain each meaningful supported ability component and how its static relationships route into combat math, while unsupported source anomalies remain explicit rather than guessed.

---

# PHASE 7 · Conditional Effects & Proc Engine
**Status: 🟢 Complete**

Phase 7 executes the static component/effect relationships established in Phase 6 over deterministic runtime state while preserving the existing `EffectVariant` architecture as authoritative.

## Completed Phase 7 foundations

- 🟢 shared deterministic `RuntimeEvent` contract for Phase 6 component triggers and `EffectVariant.trigger`
- 🟢 canonical timing/state binding for caller-active windows, explicit state windows, fixed-count duration windows, and stack-count bounds
- 🟢 deterministic trigger eligibility and caller-supplied proc chance without hidden RNG
- 🟢 global and per-target cooldown enforcement
- 🟢 explicit bounded active windows from canonical duration metadata
- 🟢 `UNIQUE`, `STACKS`, and `HIGHEST_ONLY` runtime stacking/refresh behavior without inventing alternate effect identities
- 🟢 ordered complete runtime effect streams carrying cooldown, window, stacking, and unresolved state forward
- 🟢 target-scoped status-effect application and active-status queries
- 🟢 triggered resource restoration reusing the Phase 4 restoration contracts
- 🟢 triggered healing with caller-resolved canonical healing amounts
- 🟢 deterministic target-count enforcement and explicit target selection when candidates exceed the cap
- 🟢 unresolved runtime evidence remains explicit rather than guessed

## Closeout evidence

Final Phase 7 closeout gate on **2026-09-02** against the real local `data/eso.db`:

- Phase 7 boundary rows: **24**
- need trigger resolution: **0**
- runtime-review rows: **0**
- timing unresolved: **0**
- timing bound kinds:
  - caller active window: **12**
  - stack count: **4**
  - explicit state window: **4**
  - fixed count duration: **4**
- targeted closeout regression checkpoint: **105 passed in 48.20s**
- `python tools\check_phase7_closeout.py`: **RESULT: PASS**

### Runtime capability gate

The closeout gate verifies all required contracts are present:

- shared runtime event contract
- component timing and state binding
- effect trigger eligibility
- deterministic proc chance
- global and target cooldowns
- active duration windows
- stacking and refresh
- ordered effect streams
- status-effect runtime state
- triggered resource restoration
- triggered healing
- target-count and explicit selection

## Explicit Phase 7 boundaries moving forward

Phase 7 intentionally does not become a general combat simulator. The following remain Phase 8 or later concerns, or explicit caller inputs when canonical source evidence is absent:

- full current-player/current-target CombatState snapshots
- health percentages and execute truth at arbitrary instants
- positional/range eligibility and encounter geometry
- automatic choice among multiple eligible targets when ESO targeting rules are not canonically represented
- rotation/action scheduling
- encounter phase state
- broad proc-set/enchantment ingestion where canonical static metadata is still absent
- unresolved status-duration/chance source data
- arbitrary natural-language condition parsing
- general combat simulation and Monte Carlo modeling

Detailed closeout: `docs/phase7_conditional_runtime_closeout.md`.

**Exit criteria met on 2026-09-02.** BFF can calculate deterministic or explicitly probabilistic conditional effect behavior over time without treating procs, conditional buffs, status effects, triggered healing, or runtime restores as permanent sheet stats.

---

# PHASE 8 · Combat State
**Status: 🟢 Complete**

Phase 8 turns the verified static and runtime foundations into one canonical answer to a deceptively simple question: **what is true right now?**

Phase 7 already knows how individual conditional effects behave over time. Phase 8 must assemble those truths into a coherent snapshot without becoming the later rotation or combat-simulation engine.

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

## Existing foundation entering Phase 8

- 🟢 static named buffs and target-side states already route through combat math
- 🟢 explicit potion-use events and potion active windows
- 🟢 deterministic runtime events, cooldowns, chance decisions, windows, stacking, statuses, heals/restores, and target caps from Phase 7
- 🟢 canonical build identity and build-resolved `EffectVariant` capability
- 🟢 deterministic resource timelines from Phase 4

## Initial Phase 8 priorities

1. inventory every existing `CombatState` / target-state / resource-state representation and identify overlap before adding fields
2. define the smallest canonical immutable snapshot contract for a specific `time_seconds`
3. project Phase 7 runtime windows and statuses into active buffs/debuffs/statuses at that instant
4. represent current player and target Health/resource values and percentages explicitly, including execute-threshold truth
5. expose cooldown/stack state needed to answer current eligibility without duplicating Phase 7 transition logic
6. keep position/range/encounter mechanics explicit inputs until Phase 9 provides authoritative encounter geometry/state
7. bridge the snapshot into existing static damage/healing/sustain consumers
8. validate against representative saved-build scenarios before broadening coverage

## Phase 8 boundary discipline

Phase 8 owns **state projection**, not action planning. It should answer what is currently true from known events and caller-supplied state. It should not automatically invent a rotation, choose the next action, simulate an encounter, or guess missing position/target-selection rules.

**Exit criteria:** BFF can construct an auditable CombatState snapshot for a specific instant and use it to evaluate current player/target conditions, resources, active effects, cooldowns, stacks, and supported combat math without treating theoretical capability as current truth.

**Exit criteria met on 2026-09-02.** Detailed closeout: `docs/phase8_combat_state_closeout.md`.

---

# PHASE 9 · Encounter Model
**Status: 🟢 Complete**

Phase 9 matures the encounter framework into a deterministic, source-backed model for bosses, mechanics, phases, requirements, positioning demands, timers, transitions, target-count constraints, add groups, damage windows, and reconciled evidence.

## Closeout evidence

- focused Phase 9 regression checkpoint: **23 passed in 3.94s**
- encounter corpus audited: **490 encounters**
- mechanics represented: **35 encounters**
- phases represented: **2 encounters**
- requirements represented: **21 encounters**
- positioning constraints represented: **12 encounters**
- temporal evidence represented: **4 encounters**
- transition evidence represented: **6 encounters**
- target constraints represented: **3 encounters**
- reconciled evidence represented: **8 encounters**
- explicit add-group evidence represented: **1 encounter**
- explicit damage-window evidence represented: **1 encounter**

Low coverage is an enrichment gap, not a negative claim about the live encounter. Missing and conflicting evidence remains explicit rather than guessed.

Detailed closeout: `docs/phase9_encounter_model_closeout.md`.

**Exit criteria met on 2026-09-02.** BFF understands what an encounter explicitly demands from available structured evidence and provides stable unresolved boundaries where evidence is absent or conflicting.

---

# PHASE 10 · Encounter Evaluation
**Status: 🟢 Complete**

Phase 10 combines Encounter + Requirements + Roster + Builds and produces covered, redundant, insufficient, missing, conflict, and unknown outcomes while preserving the boundary between collective capability and provider assignment.

## Closeout evidence

- real saved builds: **2**
- unique real characters: **2**
- authoritative exit roster: **Magrat → DF Healer** and **Susan → Necro Tank**
- both selected builds: **0 capability-resolution gaps**
- Oaxiltso veteran: **fully evaluable = true**
- Oaxiltso veteran: **capability-ready = true**
- execution rows: **7**
- provider rows: **0**, as expected for this validation encounter
- execution corpus: **21 encounters with requirements**
- fully evaluable encounters: **6**
- fully ready encounters: **6**
- covered requirements: **25**
- unknown requirements: **31**
- conflicting requirements: **0**
- focused final regression checkpoint: **16 passed in 1.65s**
- full regression suite after final Phase 10 changes: **2031 passed in 94.10s**

Phase 10 also made configured scribed-skill recipes native to the core build model and distinguishes exact canonical source boundaries from genuine capability gaps rather than treating newer canonical entity data as nonexistent.

Detailed closeout: `docs/phase10_encounter_evaluation_closeout.md`.

**Exit criteria met on 2026-09-02.** BFF reliably evaluates a real roster against a real encounter without selecting providers prematurely.

---

# PHASE 11 · Provider Assignment
**Status: 🟡 Active**

Move from “does the roster have Major Force?” to “who should provide it here?” using role, build, uptime, range, target, conditions, positioning, conflicts, stacking, redundancy, and player restrictions.

Phase 11 owns **provider choice**, not whether a requirement exists and not build optimization. It should consume Phase 10 capability/evidence and produce deterministic, explainable assignments while preserving UNKNOWN where provider suitability cannot be established.

Initial priorities:

1. inventory existing provider/coverage/assignment code before adding a parallel planner
2. define one canonical provider-candidate contract per requirement
3. score or rank only from explicit evidence: role, exact capability, eligibility, range/target constraints, uptime/timing evidence, positioning, conflicts, and restrictions
4. keep multiple viable providers visible until the assignment step actually chooses one
5. distinguish primary provider, backup/redundant provider, and unresolved candidate states
6. prevent the same player/build from being double-counted where simultaneous responsibilities conflict
7. make assignment reasons auditable and deterministic
8. validate against real saved rosters and real encounter requirements before broadening strategy logic

**Exit criteria:** BFF chooses sensible providers instead of merely listing coverage.

---

# PHASE 12 · Build Optimization
**Status: 🔴**

The optimizer varies gear, sets, mythics, weapons, traits, enchants, skills, morphs, ultimates, CP, Mundus, food, potions, and configuration. It does not contain ESO math itself; it asks the rules engine.

**Exit criteria:** BFF can explain why one candidate build improves expected outcome while preserving required coverage and sustain.

---

# PHASE 13 · Rotation Engine
**Status: 🔴**

Start with semi-static rotations, then add dynamic priorities, duration/recast windows, resource awareness, proc alignment, execute, movement, interruptions, and mechanic handling.

**Exit criteria:** BFF can produce/evaluate a realistic rotation from verified skill behavior and resource constraints.

---

# PHASE 14 · Combat Simulation
**Status: 🔴**

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

**Exit criteria:** BFF can model combat over time.

---

# PHASE 15 · Encounter-Aware Optimization
**Status: 🔴**

Compare builds across DPS, burst, sustained damage, execute, uptime, sustain, survivability, positioning, mechanic compliance, support contribution, phase compression, and execution complexity.

**Exit criteria:** BFF answers which build produces the better outcome in this encounter, not merely which one has the largest character-sheet number.

---

# PHASE 16 · Explanation Engine
**Status: 🔴**

Every recommendation should expose change, expected impact, reason, tradeoff, encounter effect, confidence, and evidence.

**Exit criteria:** recommendations are inspectable and defensible.

---

# PHASE 17 · ESO Logs Validation
**Status: 🔴**

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

---

# PHASE 18 · Strategy Engine
**Status: 🔴**

Evaluate safe, balanced, aggressive, and experimental strategies against roster capability, encounter risk, execution difficulty, confidence, expected gain, and failure cost.

**Exit criteria:** BFF can prefer a slightly lower theoretical ceiling when it produces the better practical outcome for the actual group.

---

# PHASE 19 · Full Raid Optimizer
**Status: 🔴**

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