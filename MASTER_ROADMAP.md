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
**Status: 🟡 Active · advanced backend foundation**

Prove the actual ESO database → effect resolver → build aggregation path across real saved builds.

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
Temporal Activation where required
 ↓
Coverage / Unresolved Evidence
```

Phase 5 inherits the real saved-build bridge from Phase 4 and is now actively proving what an actual saved character/build provides, requires, and leaves conditional or unresolved.

## Completed Phase 5 foundations

### Version-aware combat semantics

- 🟢 U50 remains reproducible as explicit historical/current semantics
- 🟢 U51 is represented as a separate game-update vocabulary rather than mutating U50 evidence
- 🟢 named combat buffs are update-aware
- 🟢 U51 Brutality/Savagery consolidation semantics are versioned
- 🟢 U51 Mundus changes are versioned
- 🟢 Alchemy trait migrations are versioned
- 🟢 strict U51 source resolution rejects obsolete U50 names unless a legacy saved-label migration explicitly opts in

### Character-owned progression

- 🟢 stable canonical character/build identity bridge
- 🟢 persisted character-owned skill-line ownership
- 🟢 canonical catalog schema v3 with character-scoped passive ranks
- 🟢 passive ranks survive build/legacy resync without contaminating build payloads
- 🟢 `Medicinal Use` rank can flow from canonical character progression into potion cadence

### U50 Alchemy source recovery and database import

Recovered U50 Alchemy evidence now forms a canonical source-backed corpus rather than a hand-maintained potion list.

- 🟢 **30** canonical U50 Alchemy effect names recovered
- 🟢 **1,399** canonical U50 formulas represented
- 🟢 source corpus rebuilt from recovered UESP pages with malformed/table-artifact rows quarantined rather than guessed
- 🟢 all expected U50 effect names accounted for
- 🟢 database import created/linked Potion and Poison `EffectVariant` rows without duplicating existing canonical effect names
- 🟢 **60** Alchemy variants imported: **30 Potion + 30 Poison**
- 🟢 source provenance attached to imported variants
- 🟢 pre-import database backup retained

Canonical U50 vocabulary includes:

`Breach, Cowardice, Defile, Detection, Enervation, Entrapment, Fracture, Heroism, Hindrance, Increase Armor, Increase Spell Power, Increase Spell Resist, Increase Weapon Power, Invisible, Lingering Health, Maim, Protection, Ravage Health, Ravage Magicka, Ravage Stamina, Restore Health, Restore Magicka, Restore Stamina, Speed, Spell Critical, Timidity, Uncertainty, Unstoppable, Vitality, Weapon Critical`.

Unsupported names such as `Vulnerability` are not promoted into the U50 Alchemy vocabulary without source evidence.

### Crafted-potion identity and saved-build availability

Potion architecture now separates effect family from reagent formula.

```text
Saved human label
      ↓
Known legacy alias or canonical formula ID
      ↓
Canonical effect family
      ↓
One or more valid reagent formulas
      ↓
Potion EffectVariants
      ↓
CONSUMABLE capability
```

- 🟢 exact canonical formula IDs identify one specific recipe
- 🟢 human legacy aliases identify an effect family and may resolve to multiple equivalent recipes
- 🟢 ambiguous unknown labels fail closed instead of selecting an arbitrary recipe
- 🟢 merchant/store names are compatibility aliases only, not the canonical potion catalog
- 🟢 `spell power` resolves to the exact U50 family:
  - Restore Magicka
  - Increase Spell Power
  - Spell Critical
- 🟢 `spell power` has **2** equivalent validated reagent formulas
- 🟢 legacy `Health Elixir` / `Elixir of Health` resolve to the Restore Health family without inventing tri-stat effects
- 🟢 Restore Health family currently exposes **37** equivalent U50 reagent formulas

A saved potion proves **availability only**. It is not applied to static/standing character stats.

### Source-backed explicit potion-use event

Potion activation now has its own temporal event model rather than being smuggled into standing state.

For the max-tier U50 source rows:

- 🟢 Essence of Magicka instant restore: **7,582 Magicka**
- 🟢 Essence of Health instant restore: **8,369 Health**
- 🟢 ordinary max-tier timed Alchemy duration: **36.6s**
- 🟢 source `triple_duration` candidate retained separately: **40.6s**
- 🟢 triple duration is **not** assumed unless formula evidence proves all three reagents carry the trait

Potion use separates instant and timed behavior:

```text
PotionUseEvent
├── Instant resource event
│    ├── Restore Health
│    ├── Restore Magicka
│    └── Restore Stamina
└── Timed named-buff grants
```

U50 named-buff routing now includes:

- Restore Health → Major Fortitude
- Restore Magicka → Major Intellect
- Restore Stamina → Major Endurance
- Increase Spell Power → Major Sorcery
- Increase Weapon Power → Major Brutality
- Spell Critical → Major Prophecy
- Weapon Critical → Major Savagery

These reuse the existing named-combat-buff semantics instead of duplicating stat percentages inside potion code.

### Explicit active potion windows

A caller can project one explicit potion-use event into a point-in-time combat snapshot.

For the current 36.6s ordinary source duration:

```text
t =  0.0s → active
t = 12.0s → active
t = 36.5s → active
t = 36.6s → expired
```

- 🟢 expiry is exact at the duration boundary
- 🟢 potion buffs merge into an existing explicit `CombatState` without overwriting unrelated buffs
- 🟢 instant resource restores are not repeated by the active-window projection
- 🟢 selected potions are never treated as permanently active

### Potion cooldown and Medicinal Use cadence

Potion cadence is modeled separately from effect duration.

- 🟢 base potion cooldown: **45.0s**
- 🟢 Medicinal Use rank 0: ×1.00 duration
- 🟢 Medicinal Use rank 1: ×1.10 duration
- 🟢 Medicinal Use rank 2: ×1.20 duration
- 🟢 Medicinal Use rank 3: ×1.30 duration
- 🟢 floating-point boundary arithmetic normalized so public timing values remain deterministic

For a 36.6s base buff:

```text
Medicinal Use rank 0
  duration = 36.60s
  cooldown = 45.00s
  gap      =  8.40s

Medicinal Use rank 3
  duration = 47.58s
  cooldown = 45.00s
  overlap  =  2.58s
```

The cadence model does not infer that a character owns Medicinal Use. The rank must come from canonical character progression; absent rank resolves to 0 without guessing.

### Real saved-build potion validation

**Magrat → DF Healer**

Saved potion: `spell power`

- resolved formulas: **2**
- instant Restore Magicka: **7,582**
- timed Increase Spell Power: **36.6s** base
- timed Spell Critical: **36.6s** base
- named buffs:
  - Major Intellect
  - Major Sorcery
  - Major Prophecy
- explicit active-window audit:
  - active at 36.5s
  - expired at 36.6s without Medicinal Use

**YOUR TANK BUILD**

Saved potion: `Health Elixir`

- resolved formulas: **37**
- instant Restore Health: **8,369**
- named buff: Major Fortitude
- active at 36.5s and expired at 36.6s without Medicinal Use

### Latest verified regression checkpoint

- 🟢 targeted canonical catalog tests green
- 🟢 character passive-rank persistence tests green
- 🟢 potion availability/use/window/cadence tests green
- 🟢 production saved-build potion audits resolve without unresolved potion errors
- 🟢 full regression suite: **1,586 passed** on **2026-09-01**

## Update 51 combat-semantics migration

Update 51 changes shared combat semantics across multiple source families, so this remains a Phase 5 architecture dependency rather than a potion-only patch.

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

Potion architecture therefore models **trait combinations / formulas**, not a fixed merchant-potion list. Merchant/Crown equivalents remain aliases/evidence only.

```text
saved legacy label
       ↓
version-aware alias
       ↓
canonical potion formula / trait combination
       ↓
versioned Alchemy trait definitions
       ↓
EffectVariant / temporal combat-state effects
```

**Migration safety rules:**

1. Preserve U50 evidence and aliases for historical/current-build reproducibility until U51 is live.
2. Do not silently reinterpret old source rows as U51 mechanics; record the active game update/provenance.
3. Prefer canonical shared effects over source-specific hard-coding.
4. Keep selected potion availability separate from timed potion activation/uptime.
5. Derive legal crafted potions from Alchemy trait/reagent compatibility rather than hand-maintaining a short named-potion catalog.
6. U51 temporal potion values must fail closed until a U51 tier-value source corpus exists.

## Remaining Phase 5 priorities

1. expose/edit character-owned skill lines and passive ranks in the Builds/character UI
2. replace free-text potion entry with a canonical crafted-potion/effect-family picker while preserving legacy aliases
3. continue running real saved builds through the production `EffectVariant` / capability path
4. verify passive, gear, mythic, arena weapon, skill, buff/debuff, and conditional-effect detection across broader saved-build samples
5. integrate consumable availability into build capability reporting without accidentally promoting `potion_use` effects to permanent/standing support
6. keep standing effects separate from conditional/triggered effects and hand temporal proc mechanics to Phase 7/8
7. import/verify U51 Alchemy tier values when authoritative source data exists
8. produce a broader auditable real-build capability/coverage report with explicit unresolved evidence
9. remove remaining final-layer patches where the canonical repository/resolver should own the behavior

**Exit criteria:** a real database-backed character correctly reports buffs, debuffs, passives, gear effects, mythics, arena effects, skills, potions, and conditional effects through the active game-update semantics without final-layer patching or guessed temporal uptime.

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
**Status: 🟢 Named-buff + explicit potion-window foundation / 🔴 full temporal engine**

Named active buffs and target states already route through static combat calculations. Phase 5 additionally delivered a first explicit source-backed temporal projection for potion-use events.

```text
Potion availability
      ↓
Explicit PotionUseEvent
      ↓
Instant restore + timed grants
      ↓
PotionActiveWindow(elapsed time)
      ↓
Explicit CombatState snapshot
```

Current temporal foundation can answer whether a potion-granted named buff is active at a caller-supplied elapsed time, can apply an explicit Medicinal Use duration multiplier, and can reason about refresh gap/overlap against potion cooldown.

It still does **not** automatically schedule potion use, infer rotation behavior, or simulate arbitrary proc/cooldown state.

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

**Remaining:** generalize the same explicit time/state discipline to skills, procs, set effects, cooldowns, stacks, encounter phases, and action scheduling.

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
