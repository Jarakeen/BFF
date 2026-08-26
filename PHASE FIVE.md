## We are still in Phase 5, but Phase 5 is NOT "finish the stat engine."

The document's current authoritative project-level designation is:
Phase 5 — Champion Points

Connect CP allocations and their resulting modifiers.


🔶 PHASE 5 — Encounter Mechanics → Requirements

Status: 🟡 NEXT

This is where we are now.

We discovered something important while investigating boss ability mapping:

UESP's encounter data gives us mechanics, but those mechanics frequently aren't player abilities.

For example:

Meteor Shower
Timeshift
Focused Fire
Aerial Onslaught
Molten Meteor

These are legitimate encounter mechanics even though they don't exist as matching rows in ability or combat_effect.

The raw UESP data preserves the actual mechanic descriptions. For example, Nahviintaas's data explicitly records Timeshift and Meteor Shower, including their timing and behavior.

Yolnahkriin similarly gives us Focused Fire and Aerial Blast with their mechanical descriptions.

Therefore:

We do NOT make ability mapping a prerequisite for encounter reasoning.

Instead:

UESP Boss
   ↓
Encounter Mechanic
   ↓
Structured Mechanic Facts
   ↓
Encounter Requirement
   ↓
Encounter Evaluation

Optional ESO ability/effect mappings can enrich that later.

What we need to build next

A structured representation of things like:

Meteor Shower
├── trigger: 30% HP
├── targets: entire group
├── behavior: spread
├── persistent_hazard: true
└── HM_overlap: true

and:

Focused Fire
├── target: player
├── behavior: group stack
├── damage_distribution: shared
└── failure_severity: high

without destroying the original UESP description.

Source evidence stays source evidence.


Phase 5 — Encounter Mechanics → Requirements

The encounter importer successfully preserves uniquely named UESP encounter
mechanics such as Meteor Shower, Timeshift, Focused Fire, Aerial Onslaught,
and Molten Meteor.

These mechanics frequently have no exact representation in the player
ability/combat-effect tables. They must therefore remain first-class encounter
mechanics rather than being forced into ability mappings.

### Next Work

1. Define structured encounter-mechanic facts while preserving original source text.
2. Derive encounter requirements from those structured mechanic facts.
3. Populate real encounter requirement sets from imported UESP mechanics.
4. Integrate real ESO database-backed character capabilities with encounter evaluation.
5. Establish real end-to-end trial evaluation tests.
6. Build provider assignment / roster feasibility optimization.
7. Connect optimization to build, gear, and effect candidates.
8. Build explainable recommendations.

### Architectural Principles

- Source evidence must remain distinct from derived interpretation.
- Encounter mechanics are first-class entities and do not require an ESO ability ID.
- Ability/combat-effect mappings are optional enrichment, not prerequisites for
  encounter evaluation.
- Do not infer a mechanical relationship solely from similar names.
- Preserve unknown/unmapped states rather than manufacturing confidence.
- Coverage analysis determines whether requirements are satisfied.
- Recommendation intents do not themselves perform optimization.
- Optimization remains a later layer.
- Existing behavior and public APIs should remain backward-compatible where practical.

### Current Branch

integrate-uesp-into-wireframe
Where we actually are

I'd put a big mental marker here:

We are no longer building the foundation. We're starting to build the brain.

The next genuinely important milestone isn't another repository or another importer.

It's this:

Take one real trial, turn its actual mechanics into structured requirements, run an actual roster against them, and get a defensible answer.

Once we can do that for Sunspire, we've crossed a pretty significant line. Then we repeat it across the other trials rather than inventing architecture in the abstract. 🖤

And yes, there are still Lego bricks on the floor. But at least we're finally building the castle.



Phase 5: Encounter Mechanics → Requirements

And it explicitly says the next work is to turn the imported UESP mechanics into structured requirements, populate real encounter requirement sets, connect real DB-backed capabilities, test end-to-end evaluation, and then move into provider assignment/optimization.

Where we actually stand
Area	Status
ESO data foundation	🟢 Complete
UESP encounter import	🟢 Complete
Gear/effect database	🟢 Complete locally
Character → capability resolution	🟢 Complete
Roster coverage/gaps/conflicts	🟢 Complete
Encounter evaluation framework	🟢 Built
Encounter mechanics → structured requirements	🟡 Current Phase 5 work
Real encounter requirement sets	🟡 Not populated yet
Real DB builds → encounter evaluation	🟡 Next
Provider assignment optimization	🔴 Next phase
Build/gear optimization	🔴 Later
Encounter-aware build optimization	🔴 Later

The completed coverage system already goes substantially beyond a simple buff checker. It resolves providers, gaps, conflicts, classifications and recommendation intents.

The Min/Max engine is farther along than I thought from the earlier conversation

This is the other important correction.

The document says we now have a real database-backed gear-set calculation path:

eso.db
   ↓
GearSetRepository
   ↓
GearSetEffectService
   ↓
GearSetEffectResolver
   ↓
Effect[]
   ↓
Build
   ↓
StatEngine
   ↓
CalculationResult
   ↓
StatBreakdown

And it has actually been verified against real database data using Akaviri Dragonguard, including explainable stat contributions.

So when we previously said:

"The DB math isn't represented in the Build/Optimization numbers yet."

that was directionally correct for the application/UI, but technically the underlying engine has already crossed the important threshold of doing database-backed gear-set calculation.

The missing piece is orchestration and breadth, not the existence of the calculation engine.

What is actually missing from the stat engine

The document lays this out pretty cleanly.

Current

Gear sets → effects → StatEngine

Still needed

Build-level automatic orchestration

So instead of a caller manually doing:

add gear
↓
resolve gear effects
↓
feed effects into StatEngine

the Build itself becomes the complete calculation input:

Build
├── base stats
├── gear sets
└── explicit effects
        ↓
Build Effect Orchestration
        ↓
resolved effects
        ↓
StatEngine
        ↓
final stats + breakdown

That's explicitly identified as the immediate Min/Max engineering milestone in the document.

Then the engine expands through:

Deterministic character stat resolution
Race
Gear customization
Skills/passives
CP
Mundus/food/potions
Complex proc mechanics
Actual Min/Max optimization
Encounter-aware optimization
UI calculator

So we are nowhere near "the optimizer is finished." But we aren't staring at an empty engine either.

And this changes how I would describe the Optimization page

This is the key part.

The Optimization UI we are building now is ahead of the underlying optimization engine.

That's okay.

The page can already expose things like:

Coverage
Major Courage       ✓
Major Vulnerability ✓
Major Slayer        ✓
Minor Brittle       ⚠
...

because roster capability resolution and coverage analysis already exist.

Maximum Coverage Plan

Eventually:

CURRENT ROSTER
      ↓
ENCOUNTER REQUIREMENTS
      ↓
CAPABILITY GAPS
      ↓
CANDIDATE PLAYER / BUILD CHANGES
      ↓
SIMULATION
      ↓
EXPECTED IMPACT

The document specifically says the eventual system needs to determine who should provide what, which provider is best, redundancy, competing requirements, feasible assignments, and fundamental roster deficiencies before it gets to build optimization.

So your:

"Add X and it will improve Y by Z amount."

idea is absolutely consistent with the architecture.

It just belongs after the evaluation/assignment layer is trustworthy, not as fake math bolted onto the pretty card.

Where Phase 5 ends

I would now define our practical Phase 5 finish line as:

Phase 5 = Encounter Evaluation

We can call Phase 5 complete when BFF can take:

Encounter
+
actual requirements
+
actual roster
+
actual builds

and reliably produce:

✓ Covered requirements
⚠ Insufficient requirements
✕ Missing requirements
↔ Redundancy
⚔ Conflicts
?
Unknowns

with real database-backed characters and encounter data.

The document already defines those classifications explicitly: Covered, Redundant, Resilient, Insufficient, Missing, Conflict and Unknown.

That's the real Phase 5 finish line.

## Then Phase 6

Here's where the document has become confusing because there are multiple roadmap numbering systems layered on top of each other.

The encounter-aware roadmap effectively says the next stage is:

Provider Assignment / Roster Optimization

Given:

12 players
+
encounter requirements
+
capabilities
+
stacking rules
+
conditions
+
conflicts

the system determines:

who should provide each capability
best provider
redundant coverage
competing requirements
feasible assignments
fundamental roster deficiencies

That is the real bridge between the current Coverage page and the future Optimization page.

Then comes:

Build Optimization

That's where it stops asking:

"Can this roster cover the requirement?"

and starts asking:

"What should these characters actually change to cover it?"

And after that:

Explanation Engine

Which is the part I think is going to make BFF genuinely useful.

Not:

❌ Insufficient Major Force

but:

Major Force: INSUFFICIENT
Requirement: 2 valid providers
Available: 1
Provider: Character A
Coverage: 62%
Required: 80%

Why: Character B's source is conditional and its prerequisite isn't satisfied.
Recommendation: Modify one source to provide a second qualifying instance.

The document explicitly describes that as the intended explanation behavior.

So, brutally simplified
Where we are now
DATABASE                    ✓
     ↓
BUILD / EFFECTS             ✓
     ↓
CHARACTER CAPABILITIES      ✓
     ↓
ROSTER COVERAGE              ✓
     ↓
ENCOUNTER MECHANICS          ✓ imported
     ↓
ENCOUNTER REQUIREMENTS       ← WE ARE HERE
     ↓
ENCOUNTER EVALUATION
     ↓
PROVIDER ASSIGNMENT
     ↓
BUILD OPTIMIZATION
     ↓
ENCOUNTER-AWARE OPTIMIZATION
     ↓
EXPLANATIONS

And separately:

DB-backed StatEngine          ✓
Gear-set calculation          ✓
Build-level orchestration     ← immediate Min/Max work
Race                          ←
Traits/glyphs/enchants        ←
Skills/passives               ←
CP                            ←
Food/mundus/potions            ←
Complex procs                  ←
True numerical optimizer       ←

The two streams eventually meet.

One important thing I would change in our mental model

I would stop calling the current Optimization page "the optimizer."

It's currently the Optimization workspace/UI.

The actual optimization intelligence is being built underneath it in stages.

That's why we can safely keep designing the gorgeous page now, including the graphs, coverage cards, maximum-coverage recommendations, comparison panels, and eventually the "add X → gain Y" analysis.

The UI is basically the cockpit we're building before the aircraft has all its engines installed. Slightly reckless, but entirely reasonable if we keep the interfaces clean. 🛩️

And your latest 917 passing tests are a better current test signal than the document's older 890/107 checkpoints. The document itself is clearly stale in several places, especially around Min/Max status. Its architecture is still useful, but I would not use its old test counts or commit hashes as the current state of the project. The most important current truth is that the underlying architecture has advanced considerably beyond those older handoff sections.