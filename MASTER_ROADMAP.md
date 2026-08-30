🖤 Black Feather Foundry
Updated Development Roadmap
North Star

BFF becomes a trustworthy, database-backed ESO combat, effects, encounter, and optimization engine that can explain not only what is optimal, but why.

The core architecture is:

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
PHASE 0 · Data Foundation
Status: 🟢 Complete

The database and core ESO data infrastructure already exist.

Includes
ESO database
skills
morphs
skill ranks
coefficients
scaling information
gear
set effects
encounter imports
UESP encounter data
repositories
data services
Exit criteria

BFF has a reliable database-backed source for ESO information.

PHASE 1 · Canonical Build System
Status: 🟢 / 🟡

This is the foundation for everything else.

A Build becomes the single canonical representation of a character configuration.

Character
 └── Build
      ├── Race
      ├── Class
      ├── Gear
      │    ├── Sets
      │    ├── Traits
      │    └── Enchants
      ├── Skills
      ├── Morphs
      ├── Ultimates
      ├── Passives
      ├── CP
      ├── Mundus
      ├── Food
      ├── Potions
      └── Configuration
Important architectural rule

A character may have multiple builds.

The same character/build must then be available everywhere:

Builds
   ↓
Optimization
   ↓
Raid Planning
   ↓
Encounter Analysis
   ↓
Log Analysis

No rebuilding the same character five times because apparently software enjoys administrative punishment.

Exit criteria

A real character can have a reusable, database-backed Build.

------------------------------------

PHASE 2 · Effect Architecture
Status: 🟡

Make the existing effect architecture authoritative.

EffectVariant already supports concepts such as:

identity
category
magnitude
duration
chance
cooldown
trigger
target
conditions
stacking

Pipeline
ESO Database
     ↓
Skill / Morph
     ↓
EffectVariant
     ↓
Effect Repository
     ↓
Build Effect Resolver
     ↓
Normalized Effects
Critical rule

Do not create a second hard-coded effect dictionary.

The existing effect-resolution system remains authoritative.

Exit criteria

A real build can expose the effects it actually provides.

------------------------------------

PHASE 3 · Static Combat Rules Engine
Status: 🟢 foundation / 🟡 integration

This is where the math you've provided becomes useful.

The authoritative path should be:

Build
 ↓
Skill / Morph
 ↓
Scaling Resolution
 ↓
Database Coefficient
 ↓
Raw Skill Damage
 ↓
Build / Stat Modifiers
 ↓
Crit
 ↓
Penetration
 ↓
Target Mitigation
 ↓
Target Critical Resistance
 ↓
Final Damage

This is already the intended architecture documented in the project.

Required components
Character stats
Max Magicka
Max Stamina
Max Health
Weapon Damage
Spell Damage
Critical Chance
Critical Damage
Penetration
Recovery
cost reduction
Damage
coefficients
scaling
raw damage
damage type
direct damage
DoT
mixed damage
proc damage
status damage
Defense
physical resistance
spell resistance
debuffs
penetration
mitigation
critical resistance
damage taken
Modifier ordering

This is important.

Penetration, mitigation, damage done, damage taken, critical modifiers, etc. cannot simply be dumped into one multiplier bucket.

Known missing pieces

The current project audit already identified:

Damage Done → skill damage wiring
Damage Taken → skill damage wiring
Critical Resistance

Exit criteria

One authoritative static combat calculation.

No duplicate formulas living in random corners of the codebase.

------------------------------------

PHASE 4 · Resource & Sustain Engine
Status: 🔴

This gets promoted earlier because the math shows it isn't merely a character-sheet stat.

Sustain includes:

recovery
cost reduction
heavy attack restoration
flat restoration
external resource restoration
resource costs
resource consumption

The engine needs to understand:

Resource State
├── Current
├── Maximum
├── Recovery
├── Cost Reduction
├── Flat Restoration
├── Heavy Attack Restoration
├── External Restoration
└── Recovery Restrictions
Eventually
Resource
 ↓
Combat Actions
 ↓
Resource Consumption
 ↓
Restoration
 ↓
Resource Curve
Exit criteria

BFF can determine whether a build can sustain its modeled activity rather than merely reporting recovery numbers.

------------------------------------

PHASE 5 · Real Build Resolution
Status: 🟡 CURRENT

This is the immediate problem I'd prioritize.

The abstraction works in tests, but the actual ESO database → effect resolver → build aggregation path has not yet been proven reliable.

Debug path
REAL DB
 ↓
Skill / Morph
 ↓
EffectVariant
 ↓
SkillEffectRepository
 ↓
CharacterBuildSupportEffectResolver
 ↓
Build Aggregation
 ↓
Normalization
 ↓
Coverage
Rule

Trace the actual object at every stage.

Do not patch the final coverage layer because the test says everything is wonderful while the actual character says otherwise.

Exit criteria

A real database-backed character correctly reports:

buffs
debuffs
passives
gear effects
mythics
arena effects
skills
conditional effects

------------------------------------

PHASE 6 · Damage / Effect Components
Status: 🔴

Turn abilities into meaningful components.

Ability
├── Direct Damage
├── DoT
├── Secondary Damage
├── Proc
├── Status Effect
├── Execute
└── Utility

And every damage event carries:

DamageEvent
├── Source
├── Target
├── Type
├── Component
├── Scaling
├── Modifiers
└── Result

This matters because direct damage and DoTs do not interact with every amplifier in the same way.

Exit criteria

BFF can explain what kind of damage an ability actually produces.

------------------------------------

PHASE 7 · Conditional Effects & Proc Engine
Status: 🔴

Now effects become temporal.

Model:

triggers
conditions
chance
cooldown
duration
stacks
targets
status effects
proc sets
enchantments
conditional buffs
conditional debuffs

Conceptually:

Trigger
 ↓
Condition Check
 ↓
Probability
 ↓
Effect
 ↓
Duration
 ↓
Expiration

Status effects and proc sets belong here because their contribution depends on events rather than simply existing on the character sheet.

Exit criteria

BFF can calculate expected conditional effect behavior.

------------------------------------

PHASE 8 · Combat State
Status: 🔴

Now we introduce time.

CombatState
├── Time
├── Phase
├── Target State
├── Player State
├── Resources
├── Buffs
├── Debuffs
├── Cooldowns
├── Stacks
├── Position
└── Active Mechanics

This becomes the bridge between static math and actual combat.

Exit criteria

BFF can answer:

"What is true right now?"

rather than only:

"What does this build theoretically have?"

------------------------------------

PHASE 9 · Encounter Model
Status: 🟡

The encounter framework already exists.

It needs to mature into structured encounter requirements:

Encounter
├── Phases
├── Bosses
├── Mechanics
├── Requirements
├── Positioning
├── Timers
├── State Transitions
├── Targets
├── Damage Windows
└── Evidence

The encounter model already defines mechanics, requirements, state transitions, conditions, and evidence concepts.

Exit criteria

BFF understands what an encounter actually demands.

------------------------------------

PHASE 10 · Encounter Evaluation
Status: 🟡 Current Phase 5 finish line

Combine:

Encounter
+
Requirements
+
Roster
+
Builds

and produce:

Result	Meaning
🟢 Covered	Requirement satisfied
🔵 Redundant	Multiple valid providers
🛡️ Resilient	Requirement has backup
🟡 Insufficient	Partially satisfied
🔴 Missing	Not satisfied
⚔️ Conflict	Requirements compete
❔ Unknown	Insufficient evidence

This is the practical Phase 5 finish line already identified in the project state.

Exit criteria

BFF can reliably evaluate a real roster against a real encounter.

------------------------------------

PHASE 11 · Provider Assignment
Status: 🔴

Now we stop asking:

"Does someone have Major Force?"

and start asking:

"Who should provide Major Force?"

Consider:

role
build
uptime
range
target
conditions
positioning
conflicts
stacking
redundancy
player restrictions
12 Players
    ↓
Encounter Requirements
    ↓
Available Capabilities
    ↓
Candidate Providers
    ↓
Optimal Assignment

This is the bridge between Coverage and Optimization.

------------------------------------

PHASE 12 · Build Optimization
Status: 🔴

Now the optimizer is finally allowed to touch things.

Candidate variables include:

gear
set
mythic
monster set
weapon
trait
enchant
skill
morph
ultimate
CP
Mundus
food
potion
configuration

The optimizer itself does not know ESO math.

It asks the rules engine.

Current Build
     ↓
Change One Variable
     ↓
Evaluate
     ↓
Recalculate
     ↓
Compare
     ↓
Rank

That separation is already explicitly called for in the project architecture.

Exit criteria

BFF can make a recommendation such as:

Replace X with Y because it increases expected encounter damage by Z while preserving required coverage and sustain.

------------------------------------

PHASE 13 · Rotation Engine
Status: 🔴

Start with the thing you've actually been asking for recently:

Semi-static rotations

Rather than immediately attempting a perfect combat simulator.

Priority
 ↓
Skill Duration
 ↓
Recast Window
 ↓
Resource Cost
 ↓
Proc Alignment
 ↓
Ultimate

Then expand into:

dynamic priorities
resource awareness
proc alignment
execute
movement
interruptions
mechanic handling

Rotations must account for skill duration, cost, damage, resource constraints, and utility.

------------------------------------

PHASE 14 · Combat Simulation
Status: 🔴

Only after the preceding pieces are trustworthy.

CombatState
      ↓
Action
      ↓
Effect
      ↓
Damage
      ↓
Resource Change
      ↓
State Change
      ↓
Next Action

Eventually:

0s ─────────────────────────────── 180s
│       │          │       │
Cast    Proc       Move    Phase
│       │          │       │
Damage  Buff       Mechanic Transition
Exit criteria

BFF can model an encounter over time.

------------------------------------

PHASE 15 · Encounter-Aware Optimization
Status: 🔴

This is where BFF becomes substantially more interesting than a build calculator.

The optimizer can finally compare:

Build A
vs
Build B

across:

DPS
burst
sustained damage
execute
uptime
sustain
survivability
positioning
mechanic compliance
support contribution
phase compression
complexity

The question becomes:

"Which build produces the better outcome in this encounter?"

not:

"Which build has the biggest number on the character sheet?"

That distinction is the entire point.

------------------------------------

PHASE 16 · Explanation Engine
Status: 🔴

Every recommendation should be explainable.

RECOMMENDATION

Change:
     X → Y

Expected Impact:
     +4.7% encounter damage

Why:
     Better scaling during the primary damage window

Tradeoff:
     -8% sustain margin

Encounter Effect:
     Still sustainable

Confidence:
     High

Evidence:
     Database + validated combat model

The existing project direction already envisions this level of explanation rather than simply displaying "Insufficient Major Force."

------------------------------------

PHASE 17 · ESO Logs Validation
Status: 🔴

Finally:

MODEL
  ↓
Expected Result
  ↓
REAL ESO LOG
  ↓
Observed Result
  ↓
Difference
  ↓
Diagnosis
  ↓
Model Refinement

This becomes the feedback loop that keeps BFF honest.

------------------------------------

PHASE 18 · Strategy Engine
Status: 🔴

Separate from raw optimization.

The strategy layer decides things like:

Safe Push
Balanced
Aggressive
Experimental

while considering:

player preferences
roster capability
encounter risk
execution difficulty
confidence
evidence
expected gain
failure cost

This is where BFF can eventually say:

"This is technically 2.3% better, but it requires perfect uptime during a mechanic your group currently struggles with. The safer option is probably better."

Which is much more useful than worshipping the spreadsheet.

------------------------------------

PHASE 19 · Full Raid Optimizer
Status: 🔴

The final system becomes:

12 CHARACTERS
       ↓
12 BUILDS
       ↓
ENCOUNTER
       ↓
REQUIREMENTS
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
RECOMMENDATION
       ↓
EXPLANATION

And eventually:

"Here is the strongest configuration for this specific roster, encounter, strategy, and execution level."

🧭 Where We Actually Are

Based on the material you've given me so far:

Area	Status
ESO database	🟢
Skill/morph data	🟢
Skill coefficients	🟢
Skill scaling	🟢
Raw skill damage	🟢
Crit calculation	🟢
Penetration	🟢
Mitigation	🟢
External math validation	🟢
Gear → effects	🟢/🟡
Build effect orchestration	🟡
Real build effect detection	🟡 Needs debugging
Damage Done → skills	🔴
Damage Taken → skills	🔴
Critical Resistance	🔴
Damage components	🔴
Sustain model	🔴
Status/proc engine	🔴
Conditional uptime	🔴
Combat State	🔴
Encounter requirements	🟡
Encounter evaluation	🟡
Provider assignment	🔴
Build optimization	🔴
Rotation evaluation	🔴
Combat simulation	🔴
Encounter optimization	🔴
Explanation engine	🔴
Log validation	🔴
Strategy engine	🔴

The important correction is that we are not starting from scratch. The underlying database-backed calculation path already exists, and the mitigation math has been externally validated under the tested assumptions. The remaining problem is connecting the islands and expanding them into a coherent rules engine.

🎯 Immediate Development Order

If I were directing the work from here, I would make the next sequence:

1. REAL BUILD EFFECT RESOLUTION
          ↓
2. COMPLETE STATIC DAMAGE PIPELINE
          ↓
3. DAMAGE COMPONENT MODEL
          ↓
4. RESOURCE / SUSTAIN MODEL
          ↓
5. CONDITIONAL EFFECT / PROC ENGINE
          ↓
6. COMBAT STATE
          ↓
7. ENCOUNTER REQUIREMENTS
          ↓
8. ENCOUNTER EVALUATION
          ↓
9. PROVIDER ASSIGNMENT
          ↓
10. BUILD OPTIMIZATION
          ↓
11. ROTATION / SIMULATION
          ↓
12. ENCOUNTER-AWARE OPTIMIZATION
          ↓
13. EXPLANATION
          ↓
14. LOG VALIDATION
          ↓
15. STRATEGY