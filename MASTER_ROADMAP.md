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
**Status: 🟢 / 🟡**

A Build is the reusable canonical representation of one character configuration.

```text
Character
 └── Build
      ├── Race / Class
      ├── Gear / Traits / Enchants
      ├── Skills / Morphs / Ultimates
      ├── Passives / CP
      ├── Mundus / Food / Potions
      └── Configuration
```

A character may have many builds. The same saved Character → Build must ultimately be selectable everywhere, including Optimization, Raid Planning, Encounter Analysis, and Log Analysis. No rebuilding the same person five times because software apparently developed paperwork envy.

**Remaining:** finish shared character-level progression/ownership persistence and make saved Character → Build selection authoritative across downstream pages.

**Exit criteria:** a real character can have reusable database-backed builds that downstream systems consume directly.

---

# PHASE 2 · Effect Architecture
**Status: 🟡 Advanced foundation**

The existing EffectVariant / effect-resolution architecture remains authoritative for effect identity, category, magnitude, duration, chance, cooldown, trigger, target, conditions, and stacking.

```text
ESO Database
     ↓
Skill / Morph / Gear
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
- 🟢 deterministic same-timestamp ordering: cost → recovery → restoration
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

The following remain deferred and explicit rather than guessed:

- unverified percentage cost-increase ordering
- unmeasured Light Armor Evocation piece counts
- exact current heavy-attack base restore values where live precision is insufficient
- automatic heavy-attack scheduling
- potion resource events/effects
- actual conditional-proc trigger/cooldown scheduling
- Enlivening Overflow / Nature's Gift / Absorb trigger timing from combat events
- exceptional recovery suppression/remapping such as Stormweaver's Cavort
- dynamic/unmapped Champion Point behavior
- canonical persisted character-level skill-line ownership

These boundaries feed later real-build, conditional-effect, and temporal-combat phases. They are not hidden inside the Phase 4 calculation.

### Final closeout evidence

- 🟢 real saved build traversed the complete Phase 4 pipeline
- 🟢 build-relevant unresolved mechanics remain explicit
- 🟢 full regression suite at closeout: **1,444 passed**

**Exit criteria met on 2026-08-31.**

---

# PHASE 5 · Real Build Resolution
**Status: 🔴 Next active phase**

Prove the actual ESO database → effect resolver → build aggregation path across real saved builds.

```text
REAL DB
 ↓
Skill / Morph / Gear
 ↓
EffectVariant
 ↓
Repositories
 ↓
Build Resolver
 ↓
Normalization
 ↓
Coverage
```

Phase 5 now inherits a working real saved-build bridge from Phase 4. The focus shifts from “can this build sustain this modeled activity?” to “what does this actual build provide, require, and leave conditional/unresolved?”

## Update 51 combat-semantics migration

Update 51 changes shared combat semantics across multiple source families, so this is a Phase 5 architecture dependency rather than a potion-only patch.

**Canonical rule:** version the combat-effect meaning, not just the source label. Skills, buffs, Alchemy, Mundus, class passives, gear, and saved-build aliases must resolve through the same update-aware effect vocabulary.

Confirmed U51 migration targets from the current PTS evidence:

- Major/Minor Brutality provide both Weapon and Spell Damage; Sorcery is removed/replaced by Brutality.
- Major/Minor Savagery provide both Weapon and Spell Critical Chance; Prophecy is removed/replaced by Savagery.
- Exploitation replaces Minor Prophecy with a unique 2974 Offensive Penetration group buff.
- Illuminate replaces Minor Sorcery with a unique 2974 Armor group buff.
- The Warrior grants both Weapon and Spell Damage.
- The Apprentice stops granting Spell Damage and instead grants 8% Experience and Inspiration gain.
- Alchemy Weapon/Spell Power traits consolidate into Increase Power.
- Alchemy Weapon/Spell Critical traits consolidate into Critical.
- Alchemy gains Mending, Vexation, Damage Shield, Heal Absorption, and Force.
- Alchemy Maim is removed/replaced by Cowardice, including previously crafted potions.

Potion architecture must therefore model **trait combinations / formulas**, not a fixed merchant-potion list. Merchant/Crown equivalents are aliases/evidence only. Common legacy saved labels such as `spell power`, `weapon power`, `tri-stat`, and `health` remain loadable aliases but must not become canonical mechanics.

```text
saved legacy label
       ↓
version-aware alias
       ↓
canonical potion formula / trait combination
       ↓
versioned Alchemy trait definitions
       ↓
EffectVariant / combat-state effects
```

Likewise, skill and buff sources must resolve through the same version-aware vocabulary so U50 Sorcery/Prophecy evidence can remain reproducible without leaking obsolete semantics into U51 calculations.

**Migration safety rules:**

1. Preserve U50 evidence and aliases for historical/current-build reproducibility until U51 is live.
2. Do not silently reinterpret old source rows as U51 mechanics; record the active game update/provenance.
3. Prefer canonical shared effects over source-specific hard-coding.
4. Keep selected potion availability separate from timed potion activation/uptime.
5. Derive legal crafted potions from Alchemy trait/reagent compatibility rather than hand-maintaining a short named-potion catalog.

Immediate Phase 5 priorities:

1. establish the version-aware combat-effect vocabulary required by U51 before expanding potion resolution
2. persist/resolve character-level progression and skill-line ownership authoritatively rather than relying on audit assumptions
3. run real saved builds through the existing EffectVariant/effect repository path
4. verify passive, gear, mythic, arena weapon, skill, buff/debuff, and conditional-effect detection
5. separate standing effects from conditional/triggered effects without promoting proc behavior to permanent sheet state
6. build the crafted-potion formula/trait catalog with U50 legacy aliases and U51 migration semantics
7. produce an auditable real-build capability/coverage report with explicit unresolved evidence
8. remove final-layer patches where the canonical repository/resolver should own the behavior

**Exit criteria:** a real database-backed character correctly reports buffs, debuffs, passives, gear effects, mythics, arena effects, skills, potions, and conditional effects through the active game-update semantics without final-layer patching.

---

# PHASE 6 · Damage / Effect Components
**Status: 🟢 Foundation delivered early in Phase 3 / 🟡 expansion later**

Per-coefficient component identity and independent damage routing now exist. Later expansion adds richer secondary damage, proc, status, execute, and utility relationships.

**Exit criteria:** BFF can explain each meaningful ability component and how it routes through combat math.

---

# PHASE 7 · Conditional Effects & Proc Engine
**Status: 🔴**

Model triggers, conditions, chance, cooldown, duration, stacks, targets, status effects, proc sets, enchantments, and conditional buffs/debuffs.

Proc critical-eligibility policy exists as a static foundation, but temporal proc behavior belongs here.

**Exit criteria:** BFF can calculate expected conditional effect behavior without treating procs as permanent sheet stats.

---

# PHASE 8 · Combat State
**Status: 🟢 Named-buff/static-state foundation / 🔴 temporal engine**

Named active buffs and target states already route through static combat calculations. Full time-aware CombatState remains later work.

```text
CombatState
├── Time / Phase
├── Target State
├── Player State
├── Resources
├── Buffs / Debuffs
├── Cooldowns / Stacks
├── Position
└── Active Mechanics
```

**Exit criteria:** BFF can answer “what is true right now?” rather than only “what can this build theoretically provide?”

---

# PHASE 9 · Encounter Model
**Status: 🟡**

Mature the existing encounter framework into structured phases, bosses, mechanics, requirements, positioning, timers, state transitions, targets, damage windows, and evidence.

**Exit criteria:** BFF understands what an encounter actually demands.

---

# PHASE 10 · Encounter Evaluation
**Status: 🟡**

Combine Encounter + Requirements + Roster + Builds and produce covered, redundant, resilient, insufficient, missing, conflict, and unknown outcomes.

**Exit criteria:** BFF reliably evaluates a real roster against a real encounter.

---

# PHASE 11 · Provider Assignment
**Status: 🔴**

Move from “does the roster have Major Force?” to “who should provide it here?” using role, build, uptime, range, target, conditions, positioning, conflicts, stacking, redundancy, and player restrictions.

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
