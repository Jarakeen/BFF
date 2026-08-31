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
**Status: 🟢 Complete pending final real-DB closeout audit / full-suite confirmation**

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
- real classified database component can traverse the complete static damage path
- full test suite green

---

# PHASE 4 · Resource & Sustain Engine
**Status: 🔴 Next major math phase**

Model recovery, cost reduction, skill costs, heavy-attack restoration, flat restoration, external restoration, and recovery restrictions over time.

```text
Resource State
├── Current
├── Maximum
├── Recovery
├── Cost Reduction
├── Flat Restoration
├── Heavy Attack Restoration
├── External Restoration
└── Recovery Restrictions
```

**Exit criteria:** BFF can determine whether a build sustains modeled activity rather than merely displaying recovery numbers.

---

# PHASE 5 · Real Build Resolution
**Status: 🟡**

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

**Exit criteria:** a real database-backed character correctly reports buffs, debuffs, passives, gear effects, mythics, arena effects, skills, and conditional effects without final-layer patching.

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

**Exit criteria:** BFF can recommend the strongest configuration for a specific roster, encounter, strategy, and execution level.

---

# 🧭 Where We Actually Are

| Area | Status |
|---|---|
| ESO database | 🟢 |
| Skill / morph data | 🟢 |
| Skill coefficients | 🟢 |
| Type-8 coefficient semantics | 🟢 unified |
| Skill scaling | 🟢 |
| Raw skill damage | 🟢 |
| Normal skill crit eligibility | 🟢 |
| Crit calculation | 🟢 |
| Critical Healing | 🟢 |
| Critical Resistance | 🟢 |
| Penetration | 🟢 |
| Mitigation | 🟢 |
| Damage Done → skills | 🟢 |
| Damage Taken → skills | 🟢 |
| Per-component damage routing | 🟢 foundation |
| Component classification DB | 🟢 2,376 persisted / 824 explicit unresolved |
| Block Cost | 🟢 |
| Block Mitigation | 🟢 |
| Named CombatState buffs | 🟢 foundation |
| Proc crit eligibility | 🟢 policy foundation |
| Combat Prayer tooltip validation | 🟢 ~0.085% residual accepted |
| Gear → effects | 🟢 / 🟡 |
| Build effect orchestration | 🟡 |
| Real build effect detection | 🟡 |
| Sustain model | 🔴 |
| Full status/proc temporal engine | 🔴 |
| Conditional uptime | 🔴 |
| Temporal Combat State | 🔴 |
| Encounter requirements | 🟡 |
| Encounter evaluation | 🟡 |
| Provider assignment | 🔴 |
| Build optimization | 🔴 |
| Rotation evaluation | 🔴 |
| Combat simulation | 🔴 |
| Encounter optimization | 🔴 |
| Explanation engine | 🔴 |
| Log validation | 🔴 |
| Strategy engine | 🔴 |

---

# 🎯 Immediate Development Order After Phase 3

1. **Phase 3 closeout:** real-DB end-to-end classified damage audit + final full suite
2. **Style / UX cleanup checkpoint** before the next large systems phase
3. **Real build effect resolution** and shared Character → Build reuse
4. **Resource / sustain engine**
5. **Conditional effect / proc engine**
6. **Temporal Combat State**
7. **Encounter requirements and evaluation**
8. **Provider assignment**
9. **Build optimization**
10. **Rotation / simulation**
11. **Encounter-aware optimization**
12. **Explanation**
13. **Log validation**
14. **Strategy engine**

The project is no longer a set of disconnected calculators. Phase 3 establishes a coherent, auditable static combat rules engine that later systems can consume without reimplementing ESO math.